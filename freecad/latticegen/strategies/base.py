"""Base mapping strategy definitions."""

import math

import FreeCAD as App
import Part

from freecad.latticegen.constants import BOOL_OVERSHOOT
from freecad.latticegen.constants import BOOL_OVERSHOOT_LARGE
from freecad.latticegen.constants import BOUNDS_PADDING
from freecad.latticegen.constants import PERCENT_MAX
from freecad.latticegen.constants import PERCENT_SCALE
from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.constants import TOL_STRICT


class BaseMappingStrategy:
    """Abstract base class for target surface UV mapping strategies."""

    def __init__(self, target_shape, bbox, target_face=None):
        self.target_shape = target_shape
        self.bbox = bbox
        self.target_face = target_face
        self.Cx = (bbox.XMax + bbox.XMin) / 2.0
        self.Cy = (bbox.YMax + bbox.YMin) / 2.0
        self.Cz = (bbox.ZMax + bbox.ZMin) / 2.0
        self.max_dim = max(
            bbox.XMax - bbox.XMin,
            bbox.YMax - bbox.YMin,
            bbox.ZMax - bbox.ZMin,
        )
        self.R = max(bbox.XMax - bbox.XMin, bbox.YMax - bbox.YMin) / 2.0

    def setup_bounds(self, border_size: float, offset_x: float,
                     offset_y: float):
        raise NotImplementedError

    def get_mapping(self, u: float, v: float):
        raise NotImplementedError

    def get_extrude_vector(self, norm: App.Vector, extrude_depth: float,
                           z_height: float) -> App.Vector:
        return -norm * (extrude_depth + BOOL_OVERSHOOT_LARGE)

    def get_clipping_shape(self, border_size: float):
        return None

    def is_tile_valid(self, test_pts, inclusion_threshold: float) -> bool:
        return True

    def get_base_pos(self, pos: App.Vector, norm: App.Vector) -> App.Vector:
        return pos + norm * BOOL_OVERSHOOT

    def is_valid_uv(self, u: float, v: float, u_min: float, u_max: float,
                    v_min: float, v_max: float) -> bool:
        return True

    def setup_grid(self, dx: float, dy: float, u_min: float, u_max: float,
                   v_min: float, v_max: float, is_staggered: bool):
        odd_y_offset = dy / 2.0 if is_staggered else 0.0
        target_cols = max(2, int((u_max - u_min) / dx) + 2)
        rows = max(2, int((v_max - v_min) / dy) + 2)
        return target_cols, rows, -1, target_cols, dx, dy, odd_y_offset


class WrapStrategy(BaseMappingStrategy):
    """Base strategy for cylindrical and spherical wrap mappings."""

    def __init__(self, target_shape, bbox, target_face=None):
        super().__init__(target_shape, bbox, target_face)
        self.wrap_scale = 1.0

    def get_clipping_shape(self, border_size: float):
        safe_size = self.max_dim * 2.0 + BOUNDS_PADDING
        if border_size > 0.0:
            z_min = self.bbox.ZMin + border_size
            z_max = self.bbox.ZMax - border_size
            if z_max > z_min:
                safe_box = Part.makeBox(safe_size, safe_size, z_max - z_min)
                box_pos = App.Vector(self.Cx - safe_size / 2.0,
                                     self.Cy - safe_size / 2.0, z_min)
                safe_box.translate(box_pos)
                return safe_box
        return None

    def is_tile_valid(self, test_pts, inclusion_threshold: float) -> bool:
        if inclusion_threshold <= 0.0:
            return True

        z_min_orig, z_max_orig = self.bbox.ZMin, self.bbox.ZMax
        pts_to_check = (test_pts[:-1] if
                        (len(test_pts) > 1 and test_pts[0].isEqual(
                            test_pts[-1], TOL_STRICT)) else test_pts)

        if not pts_to_check:
            return False

        if inclusion_threshold >= PERCENT_MAX:
            return all(
                z_min_orig - TOL_RELAXED <= pt.z <= z_max_orig + TOL_RELAXED
                for pt in pts_to_check)

        inside_count = sum(
            1 for p in pts_to_check
            if z_min_orig - TOL_RELAXED <= p.z <= z_max_orig + TOL_RELAXED)
        return (inside_count / len(pts_to_check)) >= (inclusion_threshold /
                                                      PERCENT_SCALE)

    def setup_grid(self, dx: float, dy: float, u_min: float, u_max: float,
                   v_min: float, v_max: float, is_staggered: bool):
        circumference = 2 * math.pi * self.R
        target_cols = max(2, round(circumference / dx))

        if is_staggered and target_cols % 2 != 0:
            target_cols += 1

        self.wrap_scale = (circumference / target_cols) / dx
        dx = circumference / target_cols
        dy = dy * self.wrap_scale

        odd_y_offset = dy / 2.0 if is_staggered else 0.0
        rows = max(2, int((v_max - v_min) / dy) + 2)

        return target_cols, rows, 0, target_cols, dx, dy, odd_y_offset
