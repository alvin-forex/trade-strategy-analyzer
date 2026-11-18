"""Engine version and calc-method registry.

Every artefact produced by this package carries ENGINE_VERSION so that a
report can be traced back to the exact code that produced it (requirement
v0.2 §4 provenance fields).
"""

ENGINE_VERSION = "0.3.0-a3"

# calc_method identifiers recorded in provenance metadata. These describe the
# *calculation*, and therefore must NOT change when only the interface (CLI,
# MCP, batch runner) changes — 0.3.0-a3 uses exactly the same formulas as
# 0.2.0-a2, so the identifiers stay put.
CALC_METHOD_WAVES = "zigzag-merge/v1"
CALC_METHOD_BUCKET_COUNT = "count-v1"
CALC_METHOD_BUCKET_NEAREST_RANK = "nearest-rank"
CALC_METHOD_BUCKET_PERCENTILE_INC = "percentile-inc"

BAR_MODE_EXCLUSIVE = "exclusive"
BAR_MODE_INCLUSIVE = "inclusive"

TIME_BASIS_SERVER = "server"
TIME_BASIS_UTC = "utc"
