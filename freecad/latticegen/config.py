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
