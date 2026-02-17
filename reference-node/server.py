#!/usr/bin/env python3
"""ECHO Reference Node HTTP service (v1.2 launch API step).

Endpoints:
- POST /objects
- GET /objects/{type}/{object_id}
- GET /search
- GET /bundles/export
- POST /bundles/import
- GET /stats
- GET /registry/capabilities
- GET /registry/bootstrap
- GET /health
- GET /reputation/{agent_did}
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

HTTP_IMPORT_ERROR: Exception | None = None
try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Query
    from pydantic import BaseModel, Field
except Exception as exc:  # pragma: no cover - environment-dependent import path
    HTTP_IMPORT_ERROR = exc
    uvicorn = None

    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(*args, **kwargs):  # type: ignore[no-redef]
        return None

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: Any):
            super().__init__(f"{status_code}: {detail}")
            self.status_code = status_code
            self.detail = detail

    def Query(default=None, **kwargs):  # type: ignore[no-redef]
        return default

    class FastAPI:  # type: ignore[no-redef]
        pass

import reference_node as core


@dataclass
class NodeConfig:
    manifest_path: Path
    schemas_dir: Path
    storage_root: Path
    capabilities_path: Path
    require_signature: bool = False


class ObjectIn(BaseModel):
    type: str
    object_json: Dict[str, Any] = Field(default_factory=dict)
    skip_signature: bool = False


class BundleImportIn(BaseModel):
    bundle: Dict[str, Any] = Field(default_factory=dict)
    skip_signature: bool = False


class SearchOut(BaseModel):
    count: int
    ranked: bool
    explain: bool
    results: List[Dict[str, Any]]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_float(value: Any) -> float | None:
    if _is_number(value):
        return float(value)
    return None


def _normalize_unit_interval(value: float) -> float:
    if value <= 1.0:
        return max(0.0, min(value, 1.0))
    return max(0.0, min(value / 100.0, 1.0))


def _load_rr_objects(storage_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in core.iter_stored_paths(storage_root, "rr"):
        try:
            obj = core.load_json(path)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        rows.append(obj)
    return rows


def _issuer_reliability_map(rr_objects: List[Dict[str, Any]]) -> Dict[str, float]:
    counts: Dict[str, Dict[str, int]] = {}
    for rr in rr_objects:
        issuer = rr.get("issuer_agent_did")
        if not isinstance(issuer, str) or not issuer.strip():
            continue
        issuer = issuer.strip()
        c = counts.setdefault(issuer, {"success": 0, "total": 0})
        c["total"] += 1
        if rr.get("verdict") == "SUCCESS":
            c["success"] += 1

    reliability: Dict[str, float] = {}
    for issuer, c in counts.items():
        total = max(0, int(c["total"]))
        success = max(0, int(c["success"]))
        if total <= 0:
            reliability[issuer] = 0.5
            continue
        smoothed_ratio = (success + 1.0) / (total + 2.0)
        evidence = min(total / 10.0, 1.0)
        # Low evidence -> neutral 0.5, high evidence -> move toward historical quality.
        score = (0.5 * (1.0 - evidence)) + (smoothed_ratio * evidence)
        reliability[issuer] = max(0.0, min(score, 1.0))
    return reliability


def _collect_rr_stats(storage_root: Path) -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {}
    rr_objects = _load_rr_objects(storage_root)
    reliability = _issuer_reliability_map(rr_objects)

    for obj in rr_objects:
        eo_id = obj.get("target_eo_id")
        if not isinstance(eo_id, str) or not eo_id.strip():
            continue

        issuer = obj.get("issuer_agent_did")
        weight = 0.5
        if isinstance(issuer, str) and issuer.strip():
            weight = reliability.get(issuer.strip(), 0.5)

        entry = stats.setdefault(
            eo_id,
            {
                "success_weighted": 0.0,
                "total_weighted": 0.0,
                "success_raw": 0.0,
                "total_raw": 0.0,
            },
        )
        entry["total_weighted"] += weight
        entry["total_raw"] += 1.0
        if str(obj.get("verdict")) == "SUCCESS":
            entry["success_weighted"] += weight
            entry["success_raw"] += 1.0
    return stats


def _eo_rank_components(obj: Dict[str, Any], rr_stats: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    eo_id = str(obj.get("eo_id", ""))
    confidence = float(obj.get("confidence_score", 0.0)) if _is_number(obj.get("confidence_score")) else 0.0
    has_outcome_metrics = 1.0 if isinstance(obj.get("outcome_metrics"), dict) else 0.0

    r = rr_stats.get(
        eo_id,
        {
            "success_weighted": 0.0,
            "total_weighted": 0.0,
            "success_raw": 0.0,
            "total_raw": 0.0,
        },
    )
    success_count = float(r.get("success_weighted", 0.0))
    total_count = float(r.get("total_weighted", 0.0))
    success_rate = (success_count / total_count) if total_count > 0 else 0.0

    # Deterministic trust-weighted ranking v0.
    weighted_confidence = confidence * 10.0
    weighted_outcome = has_outcome_metrics * 2.0
    weighted_success_count = success_count * 1.5
    weighted_success_rate = success_rate * 2.0
    score = weighted_confidence + weighted_outcome + weighted_success_count + weighted_success_rate
    return {
        "score": score,
        "confidence_score": confidence,
        "has_outcome_metrics": has_outcome_metrics,
        "rr_success_count": success_count,
        "rr_total_count": total_count,
        "rr_success_rate": success_rate,
        "rr_success_raw": float(r.get("success_raw", 0.0)),
        "rr_total_raw": float(r.get("total_raw", 0.0)),
        "weighted_confidence": weighted_confidence,
        "weighted_outcome": weighted_outcome,
        "weighted_success_count": weighted_success_count,
        "weighted_success_rate": weighted_success_rate,
    }


def _rank_results(
    object_type: str, results: List[Dict[str, Any]], storage_root: Path, explain: bool = False
) -> List[Dict[str, Any]]:
    if object_type != "eo":
        return results

    rr_stats = _collect_rr_stats(storage_root)
    enriched: List[Dict[str, Any]] = []

    for item in results:
        obj = item.get("object")
        if not isinstance(obj, dict):
            continue
        components = _eo_rank_components(obj, rr_stats)
        row = dict(item)
        row["score"] = round(float(components.get("score", 0.0)), 6)
        if explain:
            row["score_explain"] = {
                k: round(float(v), 6) for k, v in components.items() if k != "score"
            }
        enriched.append(row)

    enriched.sort(
        key=lambda x: (
            -float(x.get("score", 0.0)),
            str(x.get("object", {}).get("eo_id", "")),
            str(x.get("path", "")),
        )
    )
    return enriched


def _compute_reputation(storage_root: Path, agent_did: str) -> Dict[str, Any]:
    rr_objects = _load_rr_objects(storage_root)
    issued: List[Dict[str, Any]] = []
    for rr in rr_objects:
        if rr.get("issuer_agent_did") == agent_did:
            issued.append(rr)

    total = len(issued)
    success = sum(1 for rr in issued if rr.get("verdict") == "SUCCESS")
    fail = sum(1 for rr in issued if rr.get("verdict") == "FAIL")
    other = max(0, total - success - fail)

    success_ratio = (success / total) if total > 0 else 0.0
    contradiction_ratio = (fail / total) if total > 0 else 0.0

    effectiveness_values: List[float] = []
    for rr in issued:
        metrics = rr.get("outcome_metrics")
        if not isinstance(metrics, dict):
            continue
        eff = _as_float(metrics.get("effectiveness_score"))
        if eff is None:
            continue
        effectiveness_values.append(_normalize_unit_interval(eff))
    avg_effectiveness = (sum(effectiveness_values) / len(effectiveness_values)) if effectiveness_values else 0.5

    evidence_factor = min(total / 20.0, 1.0)
    quality = (0.7 * success_ratio) + (0.3 * avg_effectiveness)
    score = quality * evidence_factor

    target_counts: Dict[str, Dict[str, int]] = {}
    for rr in issued:
        eo_id = rr.get("target_eo_id")
        if not isinstance(eo_id, str) or not eo_id.strip():
            continue
        t = target_counts.setdefault(eo_id, {"total": 0, "success": 0})
        t["total"] += 1
        if rr.get("verdict") == "SUCCESS":
            t["success"] += 1
    top_targets: List[Dict[str, Any]] = []
    for eo_id, c in sorted(target_counts.items(), key=lambda kv: (-kv[1]["total"], kv[0]))[:5]:
        t_total = c["total"]
        t_success = c["success"]
        top_targets.append(
            {
                "target_eo_id": eo_id,
                "receipts_total": t_total,
                "success_receipts": t_success,
                "success_rate": round((t_success / t_total) if t_total > 0 else 0.0, 6),
            }
        )

    return {
        "version": "echo.reputation.v1",
        "agent_did": agent_did,
        "score": round(score, 6),
        "receipts_total": total,
        "success_receipts": success,
        "status_breakdown": {
            "SUCCESS": success,
            "FAIL": fail,
            "OTHER": other,
        },
        "success_ratio": round(success_ratio, 6),
        "contradiction_ratio": round(contradiction_ratio, 6),
        "avg_effectiveness_score": round(avg_effectiveness, 6),
        "evidence_factor": round(evidence_factor, 6),
        "top_targets": top_targets,
    }


def _bootstrap_payload(config: NodeConfig) -> Dict[str, Any]:
    object_types = sorted(core.TYPE_TO_FAMILY.keys())
    return {
        "bootstrap_version": "echo.node.bootstrap.v1",
        "service": "echo-reference-node",
        "protocol_version": "ECHO/1.0",
        "manifest_path": str(config.manifest_path),
        "schemas_dir": str(config.schemas_dir),
        "object_types": object_types,
        "search_ops": sorted(core.SEARCH_OPS),
        "ranking": {
            "supports_rank": True,
            "supports_explain": True,
            "scope": "eo",
        },
        "endpoints": {
            "health": {"method": "GET", "path": "/health"},
            "store_object": {"method": "POST", "path": "/objects"},
            "get_object": {"method": "GET", "path": "/objects/{type}/{object_id}"},
            "search": {"method": "GET", "path": "/search"},
            "stats": {"method": "GET", "path": "/stats"},
            "capabilities": {"method": "GET", "path": "/registry/capabilities"},
            "bootstrap": {"method": "GET", "path": "/registry/bootstrap"},
            "bundle_export": {"method": "GET", "path": "/bundles/export"},
            "bundle_import": {"method": "POST", "path": "/bundles/import"},
            "reputation": {"method": "GET", "path": "/reputation/{agent_did}"},
        },
        "examples": {
            "store": {
                "type": "eo",
                "required_top_level": [
                    "eo_id",
                    "problem_embedding",
                    "constraints_embedding",
                    "solution_embedding",
                    "created_at",
                    "protocol",
                    "signature",
                ],
            },
            "search_ranked": "/search?type=eo&field=eo_id&op=contains&value=echo.eo&rank=true&explain=true",
            "stats_with_history": "/stats?history=10",
            "sdk_python_quickstart": "python3 sdk/python/quickstart.py --base-url http://127.0.0.1:8080",
        },
    }


def create_app(config: NodeConfig) -> FastAPI:
    if HTTP_IMPORT_ERROR is not None:
        raise RuntimeError(
            f"HTTP dependencies are missing. Install reference-node/requirements.txt ({HTTP_IMPORT_ERROR})"
        )

    # Validate manifest early so service fails fast on bad config.
    core.load_manifest(config.manifest_path)

    app = FastAPI(title="ECHO Reference Node", version="0.9")
    app.state.config = config

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "service": "echo-reference-node",
            "manifest": str(config.manifest_path),
            "schemas_dir": str(config.schemas_dir),
            "require_signature": config.require_signature,
        }

    @app.post("/objects")
    def post_objects(payload: ObjectIn) -> Dict[str, Any]:
        object_type = payload.type
        obj = payload.object_json

        if object_type not in core.TYPE_TO_FAMILY:
            raise HTTPException(status_code=400, detail=f"Unknown type: {object_type}")
        if not isinstance(obj, dict):
            raise HTTPException(status_code=400, detail="object_json must be a JSON object")
        if config.require_signature and payload.skip_signature:
            raise HTTPException(
                status_code=422,
                detail="skip_signature is disabled when server require_signature policy is enabled",
            )

        errors = core.validate_object(
            object_type=object_type,
            obj=obj,
            manifest_path=config.manifest_path,
            schemas_dir=config.schemas_dir,
            skip_signature=payload.skip_signature,
        )
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

        try:
            out = core.store_object(
                storage_root=config.storage_root,
                object_type=object_type,
                obj=obj,
            )
            obj_id = core.object_id_for_type(object_type, obj)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Store failed: {exc}") from exc

        return {
            "status": "stored",
            "type": object_type,
            "id": obj_id,
            "path": str(out),
        }

    @app.get("/objects/{type}/{object_id}")
    def get_object(type: str, object_id: str) -> Dict[str, Any]:
        if type not in core.TYPE_TO_FAMILY:
            raise HTTPException(status_code=400, detail=f"Unknown type: {type}")
        try:
            obj = core.get_object(config.storage_root, type, object_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Object not found: {type}:{object_id}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Read failed: {exc}") from exc

        return {
            "type": type,
            "id": object_id,
            "object": obj,
        }

    @app.get("/search", response_model=SearchOut)
    def get_search(
        type: str,
        field: str,
        op: str = Query("equals"),
        value: str = Query(..., min_length=1),
        rank: bool = Query(False),
        explain: bool = Query(False),
        limit: int = Query(50, ge=0, le=1000),
    ) -> SearchOut:
        if type not in core.TYPE_TO_FAMILY:
            raise HTTPException(status_code=400, detail=f"Unknown type: {type}")
        if op not in {"equals", "contains", "prefix"}:
            raise HTTPException(status_code=400, detail="Unsupported op. Use equals|contains|prefix")

        try:
            results = core.search_objects(
                storage_root=config.storage_root,
                object_type=type,
                field=field,
                op=op,
                value=value,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Search failed: {exc}") from exc

        ranked = False
        if rank:
            results = _rank_results(
                object_type=type,
                results=results,
                storage_root=config.storage_root,
                explain=explain,
            )
            ranked = True

        trimmed = results[:limit]
        return SearchOut(count=len(results), ranked=ranked, explain=bool(explain), results=trimmed)

    @app.get("/bundles/export")
    def get_bundle_export(type: str) -> Dict[str, Any]:
        if type not in core.TYPE_TO_FAMILY:
            raise HTTPException(status_code=400, detail=f"Unknown type: {type}")

        try:
            return core.export_bundle_payload(
                storage_root=config.storage_root,
                manifest_path=config.manifest_path,
                object_type=type,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Bundle export failed: {exc}") from exc

    @app.post("/bundles/import")
    def post_bundle_import(payload: BundleImportIn) -> Dict[str, Any]:
        if not isinstance(payload.bundle, dict):
            raise HTTPException(status_code=400, detail="bundle must be a JSON object")
        if config.require_signature and payload.skip_signature:
            raise HTTPException(
                status_code=422,
                detail="skip_signature is disabled when server require_signature policy is enabled",
            )

        try:
            count = core.import_bundle_payload(
                storage_root=config.storage_root,
                manifest_path=config.manifest_path,
                schemas_dir=config.schemas_dir,
                bundle=payload.bundle,
                skip_signature=payload.skip_signature,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Bundle import failed: {exc}") from exc

        return {
            "status": "imported",
            "stored_objects": count,
        }

    @app.get("/stats")
    def get_stats(history: int = Query(0, ge=0, le=100)) -> Dict[str, Any]:
        stats = core.compute_stats(
            config.storage_root,
            tools_out_dir=core.default_tools_out_dir(),
            history_limit=history,
        )
        stats["manifest"] = str(config.manifest_path)
        stats["schemas_dir"] = str(config.schemas_dir)
        return stats

    @app.get("/registry/capabilities")
    def get_registry_capabilities() -> Dict[str, Any]:
        try:
            payload = core.load_json(config.capabilities_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load capabilities: {exc}") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=500, detail="Capabilities file must be a JSON object")
        payload["_file"] = str(config.capabilities_path)
        payload["_require_signature"] = config.require_signature
        return payload

    @app.get("/registry/bootstrap")
    def get_registry_bootstrap() -> Dict[str, Any]:
        return _bootstrap_payload(config)

    @app.get("/reputation/{agent_did}")
    def get_reputation(agent_did: str) -> Dict[str, Any]:
        # Stub computation based on available receipts; defaults to score 0.
        return _compute_reputation(config.storage_root, agent_did)

    return app


def default_config() -> NodeConfig:
    return NodeConfig(
        manifest_path=Path(core.default_manifest_path()).expanduser().resolve(),
        schemas_dir=Path(core.default_schemas_dir()).expanduser().resolve(),
        storage_root=core.default_storage_root(),
        capabilities_path=Path(core.default_capabilities_path()).expanduser().resolve(),
        require_signature=False,
    )


def create_default_app() -> FastAPI:
    if HTTP_IMPORT_ERROR is not None:
        # Keep module importable for CLI/help paths in environments without HTTP deps.
        return None  # type: ignore[return-value]
    return create_app(default_config())


app = create_default_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ECHO reference-node HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--manifest", default=str(core.default_manifest_path()))
    parser.add_argument("--schemas-dir", default=str(core.default_schemas_dir()))
    parser.add_argument("--capabilities-file", default=str(core.default_capabilities_path()))
    parser.add_argument("--require-signature", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if HTTP_IMPORT_ERROR is not None:
        raise SystemExit(
            f"HTTP dependencies are missing. Install reference-node/requirements.txt ({HTTP_IMPORT_ERROR})"
        )
    config = NodeConfig(
        manifest_path=Path(args.manifest).expanduser().resolve(),
        schemas_dir=Path(args.schemas_dir).expanduser().resolve(),
        storage_root=core.default_storage_root(),
        capabilities_path=Path(args.capabilities_file).expanduser().resolve(),
        require_signature=bool(args.require_signature),
    )
    app = create_app(config)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
