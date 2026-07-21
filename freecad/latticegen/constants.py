"""Configuration constants and numerical tolerances for LatticeGen."""

# Numerical Tolerances
TOL_STRICT = 1e-5  # Strict tolerance for exact equality / zero length
TOL_RELAXED = 1e-4  # Relaxed tolerance for intersection and bounding checks

# Raycasting & Geometry Offsets
RAY_OFFSET = 0.1  # Offset for ray test points to avoid self-intersection
MIN_DENOM = 0.1  # Minimum denominator to prevent division by zero in stretching
NORMAL_DOT_MIN = 0.5  # Minimum dot product to consider a normal valid

# Boolean & Bounds Padding
BOOL_OVERSHOOT = 1.0  # Extra length for clean boolean cuts
BOOL_OVERSHOOT_LARGE = 2.0  # Larger overshoot for boundary penetrating cuts
BOUNDS_PADDING = 100.0  # Buffer distance for boundary/plane extraction

# Thresholds & Scaling
PERCENT_MAX = 99.9  # Maximum percentage threshold before switching to "all" logic
PERCENT_SCALE = 100.0  # Scale factor for converting to/from percentages
FILLET_ALIGN_TOL = 0.999  # Minimum alignment for selecting pillar edges to fillet

# UI Settings
PREVIEW_DELAY_MS = 150  # Debounce timer for UI preview updates
PREVIEW_TRANSPARENCY = 50  # Transparency value for the preview tool object
