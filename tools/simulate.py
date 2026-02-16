#!/usr/bin/env python3
import argparse
import copy
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# JSON helpers
# -----------------------------

def load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"\nJSON parse error in {path}\n"
            f"  line {e.lineno}, column {e.colno}\n"
            f"  {e.msg}\n"
            f"Tip: run `python3 -m json.tool {path}`.\n"
        )
    except FileNotFoundError:
        raise SystemExit(f"\nFile not found: {path}\n")


def spawn_count(expected: float) -> int:
    """Fractional spawn: floor(expected) + 1 with probability(frac)."""
    base = int(expected)
    frac = expected - base
    return base + (1 if random.random() < frac else 0)


# -----------------------------
# Params derived from manifest
# -----------------------------

@dataclass
class PromotionThresholds:
    min_unique_authorized_receipts: int
    min_success_rate: float
    max_contradiction_rate: float
    min_stability_observed: float


@dataclass
class SimParams:
    # Content generation / reuse
    honest_publish_rate: float = 0.05     # EO per honest agent per tick
    noisy_publish_rate: float = 0.03      # EO per noisy agent per tick
    p_useful_honest: float = 0.75
    p_useful_noisy: float = 0.35

    honest_reuse_attempts_per_tick: float = 0.80  # reuse attempts per honest agent per tick
    noisy_reuse_attempts_per_tick: float = 0.30   # reuse attempts per noisy agent per tick

    # Adversary EO poisoning "useful by accident" probability and stability
    p_useful_adv: float = 0.12
    adv_stability_min: float = 0.2
    adv_stability_max: float = 0.6

    # Honest/noisy stability ranges
    honest_stability_min: float = 0.6
    honest_stability_max: float = 0.9
    noisy_stability_min: float = 0.4
    noisy_stability_max: float = 0.8

    # Trace TTL in ticks
    trace_ttl_ticks: int = 6

    # Baseline spam survival proxy
    baseline_spam_survival_rate: float = 22.5

    # Promotion thresholds (for SIMULATOR tuning)
    # NOTE: these are NOT final protocol values; they are for simulation feedback loops.
    promo: PromotionThresholds = PromotionThresholds(
        min_unique_authorized_receipts=5,
        min_success_rate=0.70,
        max_contradiction_rate=0.15,
        min_stability_observed=0.65,
    )
# NOTE:
# Promotion thresholds below are for SIMULATION ONLY.
# Protocol-level thresholds live in manifest.json.

def read_params_from_manifest(manifest: Dict[str, Any]) -> SimParams:
    """
    Simulator params are intentionally stable.
    We DO NOT override simulator thresholds from manifest by default,
    because the simulator is used to test/tune scenarios independently.

    If you later want syncing, add an env flag: ECHO_SIM_SYNC_MANIFEST=1
    """
    p = SimParams()

    # Optional: allow override only if explicitly enabled
    if os.environ.get("ECHO_SIM_SYNC_MANIFEST", "").strip() == "1":
        try:
            th = manifest["validation"]["global_promotion"]["thresholds"]
            p.promo = PromotionThresholds(
                min_unique_authorized_receipts=int(th.get("min_unique_authorized_receipts", p.promo.min_unique_authorized_receipts)),
                min_success_rate=float(th.get("min_success_rate", p.promo.min_success_rate)),
                max_contradiction_rate=float(th.get("max_contradiction_rate", p.promo.max_contradiction_rate)),
                min_stability_observed=float(th.get("min_stability_observed", p.promo.min_stability_observed)),
            )
        except Exception:
            pass

    return p



# -----------------------------
# State parsing (your v0.7 format)
# -----------------------------

def parse_agents(state: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """
    Returns (agents_total, n_honest, n_noisy, n_adv).
    Prefers state["agents"] = {honest, noisy, adversarial}.
    """
    agents = state.get("agents", {})
    if isinstance(agents, dict) and any(k in agents for k in ("honest", "noisy", "adversarial")):
        n_honest = int(agents.get("honest", 0))
        n_noisy = int(agents.get("noisy", 0))
        n_adv = int(agents.get("adversarial", 0))
        total = n_honest + n_noisy + n_adv
        if total > 0:
            return total, n_honest, n_noisy, n_adv

    # fallback
    total = int(state.get("agents_total", 20))
    n_adv = max(1, int(round(0.1 * total)))
    n_noisy = max(0, int(round(0.2 * total)))
    n_honest = max(0, total - n_adv - n_noisy)
    return total, n_honest, n_noisy, n_adv


def parse_attack_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supports:
      attack_profile.trace_flood_multiplier
      attack_profile.request_spam_multiplier (ignored)
      attack_profile.eo_poisoning_rate
      attack_profile.receipt_farming_enabled
      attack_profile.receipt_replay_enabled (ignored)
    """
    ap = state.get("attack_profile", {})
    if not isinstance(ap, dict):
        ap = {}

    trace_mult = float(ap.get("trace_flood_multiplier", 1))
    eo_poisoning_rate = float(ap.get("eo_poisoning_rate", 0))
    receipt_farming_enabled = bool(ap.get("receipt_farming_enabled", False))

    # Map multiplier -> per adv agent per tick traces
    # baseline is 5 traces per adv per tick, only if multiplier > 1
    trace_flood_rate = 5.0 * trace_mult if trace_mult > 1 else 0.0

    # If enabled, farm 5 forged receipts per adv per tick
    receipt_farming_rate = 5.0 if receipt_farming_enabled else 0.0

    return {
        "trace_flood_rate": trace_flood_rate,
        "eo_poisoning_rate": eo_poisoning_rate,
        "receipt_farming_rate": receipt_farming_rate
    }


def build_simulated_eo_payload(
    eo_id: str,
    quality: bool,
    stability: float,
    tick: int,
) -> Dict[str, Any]:
    """Build a schema-valid EO payload for reference-node CLI ingestion."""
    return {
        "eo_id": eo_id,
        "problem_embedding": "SIM_PROBLEM_EMBEDDING",
        "constraints_embedding": "SIM_CONSTRAINTS_EMBEDDING",
        "solution_embedding": "SIM_SOLUTION_EMBEDDING",
        "outcome_metrics": {
            "effectiveness_score": 0.85 if quality else 0.25,
            "stability_score": round(stability, 4),
            "iterations": 1,
        },
        "confidence_score": 0.8 if quality else 0.35,
        "share_level": "FEDERATED",
        "created_at": tick,
        "protocol": "ECHO/1.0",
        "signature": f"sim-signature-{eo_id}",
    }


def store_eo_via_reference_node(
    repo_root: str,
    eo_payload: Dict[str, Any],
    skip_signature: bool,
) -> Tuple[bool, str]:
    """Send one EO to reference-node CLI and return (accepted, raw_output)."""
    node_path = os.path.join(repo_root, "reference-node", "echo_node.py")
    manifest_path = os.path.join(repo_root, "manifest.json")
    schemas_dir = os.path.join(repo_root, "schemas")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as tmp:
            json.dump(eo_payload, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = tmp.name

        cmd = [
            sys.executable,
            node_path,
            "--manifest",
            manifest_path,
            "--schemas-dir",
            schemas_dir,
            "store",
            "--type",
            "eo",
            "--file",
            tmp_path,
        ]
        if skip_signature:
            cmd.append("--skip-signature")

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0, output
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def search_eo_via_reference_node(repo_root: str, eo_id: str) -> Tuple[bool, int, str]:
    """Probe reference-node search for a single EO id."""
    node_path = os.path.join(repo_root, "reference-node", "echo_node.py")
    manifest_path = os.path.join(repo_root, "manifest.json")
    schemas_dir = os.path.join(repo_root, "schemas")
    cmd = [
        sys.executable,
        node_path,
        "--manifest",
        manifest_path,
        "--schemas-dir",
        schemas_dir,
        "search",
        "--type",
        "eo",
        "--field",
        "eo_id",
        "--equals",
        eo_id,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = (proc.stdout + proc.stderr).strip()

    count = 0
    for line in proc.stdout.splitlines():
        if line.startswith("count:"):
            try:
                count = int(line.split(":", 1)[1].strip())
            except Exception:
                count = 0
            break

    return proc.returncode == 0, count, output


# -----------------------------
# Simulation core
# -----------------------------

def simulate(
    state: Dict[str, Any],
    params: SimParams,
    seed: int = 42,
    use_reference_node: bool = False,
    repo_root: Optional[str] = None,
    reference_node_skip_signature: bool = False,
) -> Dict[str, Any]:
    random.seed(seed)

    duration_ticks = int(state.get("duration_ticks", 168))

    agents_total, n_honest, n_noisy, n_adv = parse_agents(state)
    attack = parse_attack_profile(state)

    trace_flood_rate = float(attack["trace_flood_rate"])
    eo_poisoning_rate = float(attack["eo_poisoning_rate"])
    receipt_farming_rate = float(attack["receipt_farming_rate"])

    # EO object: quality, receipts(list of dicts), stability, promoted
    eos: List[Dict[str, Any]] = []
    traces_live: List[int] = []

    promoted_good = 0
    promoted_bad = 0
    first_find_tick = None

    th = params.promo
    eo_seq = 0
    run_tag = f"{seed}.{int(time.time())}"

    node_stats: Dict[str, Any] = {
        "enabled": bool(use_reference_node),
        "store_calls": 0,
        "store_ok": 0,
        "store_fail": 0,
        "first_error": None,
        "search_probe_id": None,
        "search_probe_found": None,
    }
    stored_ids: List[str] = []

    for tick in range(duration_ticks):
        def add_eo(quality: bool, stability: float):
            nonlocal eo_seq
            eo_seq += 1
            eo_id = f"echo.eo.sim.{run_tag}.{eo_seq}"

            accepted = True
            if use_reference_node:
                if not repo_root:
                    accepted = False
                    node_stats["store_calls"] += 1
                    node_stats["store_fail"] += 1
                    if node_stats["first_error"] is None:
                        node_stats["first_error"] = "missing repo_root for reference-node mode"
                else:
                    payload = build_simulated_eo_payload(eo_id, quality, stability, tick)
                    node_stats["store_calls"] += 1
                    ok, out = store_eo_via_reference_node(
                        repo_root=repo_root,
                        eo_payload=payload,
                        skip_signature=reference_node_skip_signature,
                    )
                    if ok:
                        node_stats["store_ok"] += 1
                        stored_ids.append(eo_id)
                    else:
                        accepted = False
                        node_stats["store_fail"] += 1
                        if node_stats["first_error"] is None:
                            node_stats["first_error"] = out[:500] if out else "reference-node store failed"

            if accepted:
                eos.append({
                    "eo_id": eo_id,
                    "quality": quality,
                    "receipts": [],
                    "stability": stability,
                    "promoted": False
                })

        # ---- Publish EOs ----
        honest_expected = params.honest_publish_rate * n_honest
        for _ in range(spawn_count(honest_expected)):
            add_eo(
                quality=(random.random() < params.p_useful_honest),
                stability=random.uniform(params.honest_stability_min, params.honest_stability_max),
            )

        noisy_expected = params.noisy_publish_rate * n_noisy
        for _ in range(spawn_count(noisy_expected)):
            add_eo(
                quality=(random.random() < params.p_useful_noisy),
                stability=random.uniform(params.noisy_stability_min, params.noisy_stability_max),
            )

        # adversarial poisoning EOs
        adv_attempts = int(max(0.0, eo_poisoning_rate) * n_adv)
        for _ in range(adv_attempts):
            add_eo(
                quality=(random.random() < params.p_useful_adv),
                stability=random.uniform(params.adv_stability_min, params.adv_stability_max),
            )

        # ---- Trace flood (TTL) ----
        new_traces = int(max(0.0, trace_flood_rate) * n_adv)
        for _ in range(new_traces):
            traces_live.append(params.trace_ttl_ticks)

        traces_live = [ttl - 1 for ttl in traces_live if (ttl - 1) > 0]

        # ---- Reuse attempts -> receipts ----
        if eos:
            honest_attempts = int(round(params.honest_reuse_attempts_per_tick * n_honest))
            for _ in range(max(0, honest_attempts)):
                if random.random() < 0.8:
                    cands = [eo for eo in eos if eo["quality"]]
                    target = random.choice(cands) if cands else random.choice(eos)
                else:
                    target = random.choice(eos)

                target["receipts"].append({
                    "verdict": "SUCCESS" if target["quality"] else "FAIL",
                    "source": "honest"
                })

            noisy_attempts = int(round(params.noisy_reuse_attempts_per_tick * n_noisy))
            for _ in range(max(0, noisy_attempts)):
                target = random.choice(eos)
                if random.random() < 0.55:
                    verdict = "SUCCESS" if target["quality"] else "FAIL"
                else:
                    verdict = "FAIL" if target["quality"] else "SUCCESS"

                target["receipts"].append({
                    "verdict": verdict,
                    "source": "noisy"
                })

        # ---- Receipt farming: forge SUCCESS on bad EO if possible ----
        if eos and receipt_farming_rate > 0:
            forged = int(receipt_farming_rate * n_adv)
            for _ in range(max(0, forged)):
                bads = [eo for eo in eos if not eo["quality"]]
                target = random.choice(bads) if bads else random.choice(eos)
                target["receipts"].append({
                    "verdict": "SUCCESS",
                    "source": "farm"
                })

        # ---- Promotion check (AUTHORIZED receipts only) ----
        for eo in eos:
            if eo["promoted"]:
                continue

            authorized = [r for r in eo["receipts"] if r.get("source") != "farm"]
            if len(authorized) < th.min_unique_authorized_receipts:
                continue

            success = sum(1 for r in authorized if r.get("verdict") == "SUCCESS")
            fail = sum(1 for r in authorized if r.get("verdict") == "FAIL")

            success_rate = success / max(1, len(authorized))
            contradiction_rate = fail / max(1, len(authorized))

            if (success_rate >= th.min_success_rate and
                contradiction_rate <= th.max_contradiction_rate and
                eo["stability"] >= th.min_stability_observed):
                eo["promoted"] = True
                if eo["quality"]:
                    promoted_good += 1
                else:
                    promoted_bad += 1

        # ---- D2: first tick where useful EO got at least one authorized SUCCESS ----
        if first_find_tick is None:
            for eo in eos:
                if not eo["quality"]:
                    continue
                authorized = [r for r in eo["receipts"] if r.get("source") != "farm"]
                if any(r.get("verdict") == "SUCCESS" for r in authorized):
                    first_find_tick = tick
                    break

    # ---- Aggregate metrics ----
    eos_total = len(eos)
    eos_useful = sum(1 for eo in eos if eo["quality"])
    eos_bad = eos_total - eos_useful

    def score(eo: Dict[str, Any]) -> float:
        authorized = [r for r in eo["receipts"] if r.get("source") != "farm"]
        s = sum(1 for r in authorized if r.get("verdict") == "SUCCESS") - sum(1 for r in authorized if r.get("verdict") == "FAIL")
        return float(s) + (0.5 * eo["stability"])

    if eos_total == 0:
        d1 = 0.0
        d2 = 200
    else:
        ranked = sorted(eos, key=score, reverse=True)
        top5 = ranked[:5]
        d1 = 0.0 if not top5 else (100.0 * sum(1 for eo in top5 if eo["quality"]) / len(top5))
        d2 = int(first_find_tick) if first_find_tick is not None else 200

    promoted_total = promoted_good + promoted_bad
    t1 = 0.0 if promoted_total == 0 else (100.0 * promoted_bad / promoted_total)
    t2 = 0.0 if eos_useful == 0 else (100.0 * (eos_useful - promoted_good) / eos_useful)

    a1 = params.baseline_spam_survival_rate + (5.0 if trace_flood_rate > 0 else 0.0)

    metrics_v1 = {
        "time_to_find_ticks": int(d2),
        "useful_hit_rate_top5_pct": round(d1, 2),
        "false_promotion_rate_pct": round(t1, 2),
        "missed_promotion_rate_pct": round(t2, 2),
        "spam_survival_rate_pct": round(a1, 2),
    }
    legacy_metrics = {
        "D1_useful_top5": metrics_v1["useful_hit_rate_top5_pct"],
        "D2_time_to_find_ticks": metrics_v1["time_to_find_ticks"],
        "T1_false_promotion_rate": metrics_v1["false_promotion_rate_pct"],
        "T2_missed_promotion_rate": metrics_v1["missed_promotion_rate_pct"],
        "A1_spam_survival_rate": metrics_v1["spam_survival_rate_pct"],
        "P1_avg_trace_lifetime_ticks": int(params.trace_ttl_ticks),
        "C1_bootstrap_success": True,
    }

    report = {
        "agents_total": agents_total,
        "objects": {
            "eos_total": eos_total,
            "eos_useful": eos_useful,
            "eos_bad": eos_bad
        },
        "metrics": {**metrics_v1, **legacy_metrics},
        "metrics_contract_version": "echo.sim.metrics.v1",
    }

    if use_reference_node:
        if repo_root and stored_ids:
            probe_id = stored_ids[0]
            ok, count, out = search_eo_via_reference_node(repo_root=repo_root, eo_id=probe_id)
            node_stats["search_probe_id"] = probe_id
            node_stats["search_probe_found"] = bool(ok and count > 0)
            if (not ok or count <= 0) and node_stats["first_error"] is None:
                node_stats["first_error"] = out[:500] if out else "reference-node search probe failed"
        report["reference_node"] = node_stats

    return report


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ECHO minimal simulator")
    parser.add_argument(
        "state",
        nargs="?",
        default=os.path.join("examples", "simulation", "state.template.json"),
        help="Path to simulation state JSON (repo-relative or absolute)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--use-reference-node",
        action="store_true",
        help="Store generated EOs through reference-node CLI",
    )
    parser.add_argument(
        "--reference-node-skip-signature",
        action="store_true",
        help="When using reference-node mode, pass --skip-signature to store calls",
    )
    return parser.parse_args()


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    args = parse_args()

    if os.path.isabs(args.state):
        state_path = args.state
    else:
        state_path = os.path.join(repo_root, args.state)

    manifest_path = os.path.join(repo_root, "manifest.json")

    print("Using state file:", state_path)

    state = load_json(state_path)
    manifest = load_json(manifest_path)
    params = read_params_from_manifest(manifest)

    report = simulate(
        state,
        params,
        seed=args.seed,
        use_reference_node=args.use_reference_node,
        repo_root=repo_root,
        reference_node_skip_signature=args.reference_node_skip_signature,
    )

    print("\nECHO Minimal Simulator Report\n")
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
    metrics_to_print = [
        "time_to_find_ticks",
        "useful_hit_rate_top5_pct",
        "false_promotion_rate_pct",
        "missed_promotion_rate_pct",
        "spam_survival_rate_pct",
    ]
    for k in metrics_to_print:
        v = report.get("metrics", {}).get(k)
        print(f"  - {k}: {v}")

    if "reference_node" in report:
        rn = report["reference_node"]
        print("\nReference-node:")
        print(f"  - enabled: {rn.get('enabled')}")
        print(f"  - store_calls: {rn.get('store_calls')}")
        print(f"  - store_ok: {rn.get('store_ok')}")
        print(f"  - store_fail: {rn.get('store_fail')}")
        print(f"  - search_probe_id: {rn.get('search_probe_id')}")
        print(f"  - search_probe_found: {rn.get('search_probe_found')}")
        if rn.get("first_error"):
            print(f"  - first_error: {rn.get('first_error')}")

    out_dir = os.path.join(repo_root, "tools", "out")
    os.makedirs(out_dir, exist_ok=True)

    state_name = os.path.basename(state_path).replace(".json", "")
    out_path = os.path.join(out_dir, f"sim_report_{state_name}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    latest_path = os.path.join(out_dir, "sim_report_latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(copy.deepcopy(report), f, ensure_ascii=False, indent=2)

    print("\nWrote:", out_path)
    print("Wrote:", latest_path)


if __name__ == "__main__":
    main()
