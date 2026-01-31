#!/usr/bin/env python3
import sys
"""
ECHO Minimal Simulator (v0.7.1)

This is a conceptual simulator for protocol tuning.
It does NOT implement embeddings or real search.
Instead, it models outcomes using probabilities and protocol parameters.

Inputs:
- examples/simulation/state.template.json
- manifest.json

Outputs:
- stdout report
- optionally writes a JSON report to tools/out/sim_report.json
"""

import json
import math
import os
import random
from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class Params:
    ttl_trace: int
    ttl_request: int
    ttl_referral: int
    ttl_seedupdate: int
    prom_min_receipts: int
    prom_min_success: float
    prom_max_contra: float
    prom_min_stability: float
    decay_half_life: int
    newcomer_trace_per_hour: int
    standard_trace_per_hour: int
    newcomer_request_per_hour: int
    standard_request_per_hour: int
    newcomer_eo_per_hour: int
    standard_eo_per_hour: int


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_params(manifest: Dict[str, Any]) -> Params:
    ttl = manifest["anti_abuse"]["ttl_defaults_seconds"]
    prom = manifest["validation"]["global_promotion"]["thresholds"]
    decay = manifest["validation"]["mra"]["authority_decay"]["half_life_seconds"]
    rl = manifest["anti_abuse"]["rate_limits"]

    return Params(
        ttl_trace=int(ttl["TraceObject"]),
        ttl_request=int(ttl["RequestObject"]),
        ttl_referral=int(ttl["ReferralObject"]),
        ttl_seedupdate=int(ttl["SeedUpdateObject"]),
        prom_min_receipts=int(prom["min_unique_authorized_receipts"]),
        prom_min_success=float(prom["min_success_rate"]),
        prom_max_contra=float(prom["max_contradiction_rate"]),
        prom_min_stability=float(prom["min_stability_observed"]),
        decay_half_life=int(decay),
        newcomer_trace_per_hour=int(rl["newcomer"]["trace_per_hour"]),
        standard_trace_per_hour=int(rl["standard"]["trace_per_hour"]),
        newcomer_request_per_hour=int(rl["newcomer"]["request_per_hour"]),
        standard_request_per_hour=int(rl["standard"]["request_per_hour"]),
        newcomer_eo_per_hour=int(rl["newcomer"]["eo_per_hour"]),
        standard_eo_per_hour=int(rl["standard"]["eo_per_hour"]),
    )


def exp_decay(weight: float, age_seconds: int, half_life_seconds: int) -> float:
    if half_life_seconds <= 0:
        return weight
    # weight * 0.5^(age/half-life)
    return weight * (0.5 ** (age_seconds / half_life_seconds))


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def simulate_experiment(state: Dict[str, Any], params: Params, seed: int = 42) -> Dict[str, Any]:
    random.seed(seed)

    tick_seconds = int(state["tick_seconds"])
    duration_ticks = int(state["duration_ticks"])
    agents = state["agents"]
    attack = state["attack_profile"]

    n_honest = int(agents["honest"])
    n_noisy = int(agents["noisy"])
    n_adv = int(agents["adversarial"])
    n_total = n_honest + n_noisy + n_adv

    # --- Model assumptions (tunable constants) ---
    # Probability an EO is "useful" by publisher type
    p_useful_honest = 0.75
    p_useful_noisy = 0.45
    p_useful_adv = 0.15  # poisoning tends to be useless

    # Baseline reuse probability if EO is useful
    base_reuse_p = 0.20  # per tick across network (conceptual)

    # Receipt verdict probabilities conditioned on EO quality
    # If useful: mostly success
    useful_success = 0.80
    useful_partial = 0.15
    useful_fail = 0.05
    # If not useful: mostly fail
    bad_success = 0.10
    bad_partial = 0.20
    bad_fail = 0.70

    # Contradiction proxy: probability of FAIL in "similar contexts"
    # We approximate by fail rate among receipts.

    # Attack multipliers (spam volume)
    trace_mult = float(attack.get("trace_flood_multiplier", 1))
    request_mult = float(attack.get("request_spam_multiplier", 1))
    eo_poison_rate = float(attack.get("eo_poisoning_rate", 0))
    farm = bool(attack.get("receipt_farming_enabled", False))
    replay = bool(attack.get("receipt_replay_enabled", False))

    # --- State variables ---
    # We simulate a pool of EOs and their receipt stats.
    eos = []  # list of dict: {quality: bool, receipts: [], created_tick: int, stability: float}
    traces_active = 0
    requests_active = 0

    # Helper: publish EOs per tick subject to rate limits.
    def eo_publishes_per_tick(role: str) -> int:
        # Convert per hour to per tick (tick may be 1h)
        if role == "honest":
            return max(0, int(params.standard_eo_per_hour * (tick_seconds / 3600)))
        if role == "noisy":
            return max(0, int(params.standard_eo_per_hour * (tick_seconds / 3600)))
        if role == "adv":
            # adversary tries to publish more, but constrained by standard limits
            return max(0, int(params.standard_eo_per_hour * (tick_seconds / 3600)))
        return 0

    # Helper: spawn spam traces/requests (bounded by rate limits + TTL)
    def trace_gen_per_tick(role: str) -> int:
        base = params.standard_trace_per_hour if role != "honest_new" else params.newcomer_trace_per_hour
        return max(0, int(base * (tick_seconds / 3600)))

    def request_gen_per_tick(role: str) -> int:
        base = params.standard_request_per_hour if role != "honest_new" else params.newcomer_request_per_hour
        return max(0, int(base * (tick_seconds / 3600)))

    # TTL in ticks
    ttl_trace_ticks = max(1, params.ttl_trace // tick_seconds)
    ttl_request_ticks = max(1, params.ttl_request // tick_seconds)

    # Track counts of ephemeral objects to approximate discoverability degradation.
    # Very rough: more spam lowers D1.
    trace_ttl_queue = [0] * ttl_trace_ticks
    request_ttl_queue = [0] * ttl_request_ticks

    false_promotions = 0
    promotions_total = 0

    # Main loop
    for tick in range(duration_ticks):
        # --- Generate traces/requests (including adversarial spam) ---
        # Honest produce some traces/requests naturally (low)
        honest_traces = int(0.3 * n_honest)
        honest_requests = int(0.1 * n_honest)

        # Adversarial spam attempts scaled by multipliers
        adv_traces = int(trace_mult * trace_gen_per_tick("adv") * max(1, n_adv))
        adv_requests = int(request_mult * request_gen_per_tick("adv") * max(1, n_adv))

        # Enforce rough rate limit caps (per tick, per agent)
        # We approximate by capping to standard per-tick * #agents
        trace_cap = trace_gen_per_tick("adv") * max(1, n_adv)
        req_cap = request_gen_per_tick("adv") * max(1, n_adv)

        adv_traces = min(adv_traces, trace_cap)
        adv_requests = min(adv_requests, req_cap)

        traces_new = honest_traces + adv_traces
        requests_new = honest_requests + adv_requests

        # TTL queues
        expired_traces = trace_ttl_queue.pop(0)
        expired_requests = request_ttl_queue.pop(0)
        traces_active = max(0, traces_active - expired_traces) + traces_new
        requests_active = max(0, requests_active - expired_requests) + requests_new
        trace_ttl_queue.append(traces_new)
        request_ttl_queue.append(requests_new)

        # --- Publish EOs ---
        # Honest publishes a small number overall per tick; noisy less useful; adversarial poison
        # We keep EO volume low to make it interpretable.
        eo_new = 0

        # Honest EOs
        for _ in range(max(0, int(0.05 * n_honest))):
            eos.append({"quality": random.random() < p_useful_honest, "receipts": [], "created_tick": tick, "stability": random.uniform(0.6, 0.9)})
            eo_new += 1

        # Noisy EOs
        for _ in range(max(0, int(0.03 * n_noisy))):
            eos.append({"quality": random.random() < p_useful_noisy, "receipts": [], "created_tick": tick, "stability": random.uniform(0.4, 0.8)})
            eo_new += 1

        # Adversarial EOs (poisoning rate controls how many they try)
        adv_attempts = int(eo_poison_rate * max(1, n_adv))
        for _ in range(adv_attempts):
            eos.append({"quality": random.random() < p_useful_adv, "receipts": [], "created_tick": tick, "stability": random.uniform(0.2, 0.6)})
            eo_new += 1

        # --- Reuse + receipts ---
        # Compute how spam affects discoverability: more traces/requests reduce effective reuse probability.
        spam_pressure = (traces_active + requests_active) / max(1, n_total * 10)
        reuse_p = clamp01(base_reuse_p * (1.0 / (1.0 + spam_pressure)))

        for eo in eos:
            # probability to be reused this tick
            if random.random() < reuse_p:
                if eo["quality"]:
                    verdict_roll = random.random()
                    if verdict_roll < useful_success:
                        verdict = "SUCCESS"
                    elif verdict_roll < useful_success + useful_partial:
                        verdict = "PARTIAL"
                    else:
                        verdict = "FAIL"
                else:
                    verdict_roll = random.random()
                    if verdict_roll < bad_success:
                        verdict = "SUCCESS"
                    elif verdict_roll < bad_success + bad_partial:
                        verdict = "PARTIAL"
                    else:
                        verdict = "FAIL"
                eo["receipts"].append({"tick": tick, "verdict": verdict})

        # Receipt farming: colluders add SUCCESS receipts to random EOs they own (approx)
        if farm and n_adv > 0 and eos:
            for _ in range(min(3, len(eos))):
                target = random.choice(eos)
                target["receipts"].append({"tick": tick, "verdict": "SUCCESS", "farmed": True})

        # Receipt replay: old receipts re-added (inflation attempt)
        if replay and eos:
            target = random.choice(eos)
            if target["receipts"]:
                old = random.choice(target["receipts"])
                # replay at current tick
                target["receipts"].append({"tick": tick, "verdict": old["verdict"], "replayed": True})

        # --- Promotion check (very simplified) ---
        # Determine if any EO meets promotion thresholds based on receipts so far.
        for eo in eos:
            receipts = eo["receipts"]
            if len(receipts) < params.prom_min_receipts:
                continue

            # Compute decayed success/fail rates
            success_w = 0.0
            fail_w = 0.0
            total_w = 0.0

            for r in receipts:
                age_seconds = (tick - r["tick"]) * tick_seconds
                w = exp_decay(1.0, age_seconds, params.decay_half_life)
                total_w += w
                if r["verdict"] == "SUCCESS":
                    success_w += w
                if r["verdict"] == "FAIL":
                    fail_w += w

            if total_w <= 0:
                continue

            success_rate = success_w / total_w
            contra_rate = fail_w / total_w  # proxy
            stability = eo["stability"]

            promoted = (
                success_rate >= params.prom_min_success and
                contra_rate <= params.prom_max_contra and
                stability >= params.prom_min_stability
            )

            # Count promotions; estimate false promotions if EO quality is bad
            if promoted:
                promotions_total += 1
                if not eo["quality"]:
                    false_promotions += 1

    # --- Aggregate metrics ---
    # D1 proxy: probability useful EO appears in top-5; we approximate by ratio of useful EOs with good success rate.
    useful_eos = [eo for eo in eos if eo["quality"]]
    bad_eos = [eo for eo in eos if not eo["quality"]]

    def eo_score(eo) -> float:
        receipts = eo["receipts"]
        if not receipts:
            return 0.0
        success = sum(1 for r in receipts if r["verdict"] == "SUCCESS")
        total = len(receipts)
        return (success / total) * (1.0 + math.log1p(total))

    scored = sorted(eos, key=eo_score, reverse=True)
    top5 = scored[:5]
    D1_useful_top5 = 0.0
    if top5:
        D1_useful_top5 = sum(1 for eo in top5 if eo["quality"]) / len(top5)

    # D2 proxy: time-to-find; we approximate inversely by D1 and reuse probability.
    D2_time_to_find_ticks = int(max(1, round(10 / max(0.05, D1_useful_top5))))

    T1_false_promotion_rate = 0.0
    if promotions_total > 0:
        T1_false_promotion_rate = false_promotions / promotions_total

    # T2 missed promotions proxy: useful EO with many receipts but not promoted
    missed = 0
    eligible = 0
    for eo in useful_eos:
        if len(eo["receipts"]) >= params.prom_min_receipts:
            eligible += 1
            # check if would be promoted in last tick (approx)
            receipts = eo["receipts"]
            success = sum(1 for r in receipts if r["verdict"] == "SUCCESS")
            fail = sum(1 for r in receipts if r["verdict"] == "FAIL")
            total = len(receipts)
            success_rate = success / total
            contra_rate = fail / total
            if not (success_rate >= params.prom_min_success and contra_rate <= params.prom_max_contra and eo["stability"] >= params.prom_min_stability):
                missed += 1
    T2_missed_promotion_rate = (missed / eligible) if eligible else 0.0

    A1_spam_survival_rate = clamp01((traces_active + requests_active) / max(1.0, duration_ticks * n_total))

    P1_avg_trace_lifetime_ticks = ttl_trace_ticks  # by design under TTL queue

    # C1 bootstrap success: if referral exists and mirrors exist conceptually -> yes
    C1_bootstrap_success = True

    return {
        "agents_total": n_total,
        "objects": {
            "eos_total": len(eos),
            "eos_useful": len(useful_eos),
            "eos_bad": len(bad_eos)
        },
        "metrics": {
            "D1_useful_top5": round(D1_useful_top5 * 100, 1),
            "D2_time_to_find_ticks": D2_time_to_find_ticks,
            "T1_false_promotion_rate": round(T1_false_promotion_rate * 100, 2),
            "T2_missed_promotion_rate": round(T2_missed_promotion_rate * 100, 2),
            "A1_spam_survival_rate": round(A1_spam_survival_rate * 100, 2),
            "P1_avg_trace_lifetime_ticks": P1_avg_trace_lifetime_ticks,
            "C1_bootstrap_success": C1_bootstrap_success
        }
    }


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # --- NEW: read state file from CLI args ---
    if len(sys.argv) > 1:
        state_arg = sys.argv[1]
        state_path = os.path.join(repo_root, state_arg)
    else:
        state_path = os.path.join(
            repo_root, "examples", "simulation", "state.template.json"
        )

    manifest_path = os.path.join(repo_root, "manifest.json")

    print("Using state file:", state_path)

    state = load_json(state_path)
    manifest = load_json(manifest_path)
    params = read_params(manifest)

    report = simulate_experiment(state, params, seed=42)

    print("\nECHO Minimal Simulator Report (v0.7.1)\n")
    print("Agents total:", report["agents_total"])
    print(
        "EOs total:",
        report["objects"]["eos_total"],
        "| useful:",
        report["objects"]["eos_useful"],
        "| bad:",
        report["objects"]["eos_bad"],
    )
    print("\nMetrics:")
    for k, v in report["metrics"].items():
        print(f"  - {k}: {v}")

    out_dir = os.path.join(repo_root, "tools", "out")
    os.makedirs(out_dir, exist_ok=True)

    state_name = os.path.basename(state_path).replace(".json", "")
    out_path = os.path.join(out_dir, f"sim_report_{state_name}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\nWrote:", out_path)
    print("\nRun another scenario by passing a different state file.\n")



if __name__ == "__main__":
    main()
