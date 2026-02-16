"""Public package API for the ECHO reference-node core library."""

from .index import empty_index, load_index, save_index
from .io_bundle import (
    export_bundle,
    export_bundle_payload,
    import_bundle,
    import_bundle_payload,
    infer_object_type,
)
from .metrics import (
    SIM_METRICS_CONTRACT_VERSION,
    SIM_METRIC_TARGETS,
    evaluate_sim_metrics_v1,
    extract_sim_metrics_v1,
)
from .io_utils import (
    default_capabilities_path,
    default_manifest_path,
    default_schemas_dir,
    default_storage_root,
    default_tools_out_dir,
    load_json,
    repo_root,
    safe_filename,
    write_json,
)
from .search import search_objects
from .stats import compute_stats
from .store import get_object, iter_stored_paths, object_id_for_type, storage_path_for_id, store_object
from .types import ID_FIELD_MAP, TYPE_DIR, TYPE_TO_FAMILY, SEARCH_OPS, type_to_family
from .validate import (
    load_manifest,
    load_schema_for_type,
    resolve_schema_path,
    schema_id_for_type,
    validate_object,
)

__all__ = [
    "ID_FIELD_MAP",
    "SEARCH_OPS",
    "TYPE_DIR",
    "TYPE_TO_FAMILY",
    "SIM_METRICS_CONTRACT_VERSION",
    "SIM_METRIC_TARGETS",
    "default_capabilities_path",
    "default_manifest_path",
    "default_schemas_dir",
    "default_storage_root",
    "default_tools_out_dir",
    "empty_index",
    "export_bundle",
    "export_bundle_payload",
    "import_bundle_payload",
    "import_bundle",
    "compute_stats",
    "get_object",
    "infer_object_type",
    "iter_stored_paths",
    "load_index",
    "load_json",
    "load_manifest",
    "load_schema_for_type",
    "object_id_for_type",
    "repo_root",
    "resolve_schema_path",
    "safe_filename",
    "save_index",
    "schema_id_for_type",
    "search_objects",
    "evaluate_sim_metrics_v1",
    "extract_sim_metrics_v1",
    "storage_path_for_id",
    "store_object",
    "type_to_family",
    "validate_object",
    "write_json",
]
