"""Data classes for LatticeGen configuration."""

from dataclasses import dataclass


@dataclass
class LatticeConfig:
    pattern: str = "Hexagon"
    mapping: str = "Planar"
    tile_radius: float = 8.0
    gap: float = 1.0
    extrude_depth: float = 5.0
    fillet_radius: float = 0.0
    border_size: float = 0.0
    inclusion_threshold: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    operation_mode: str = "cut"
    axis: str = "Z"
    
    # Custom specific parameters
    voronoi_seed: int = 12345
    voronoi_variance: float = 0.5
    voronoi_relaxation: int = 0
    voronoi_gap_variance: float = 0.0
    voronoi_base_grid: str = "Hexagon"
    voronoi_stretch_u: float = 1.0
    voronoi_stretch_v: float = 1.0
