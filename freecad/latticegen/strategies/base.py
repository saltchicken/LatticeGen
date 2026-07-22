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

    name = "Base"
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.name != "Base":
            BaseMappingStrategy._registry[cls.name] = cls

    def __init__(self, target_shape, bbox, target_face=None, axis="Z"):
        self.target_shape = target_shape
        self.bbox = bbox
        self.target_face = target_face
        self.axis = axis

        # Global centers
        self.Cx = (bbox.XMax + bbox.XMin) / 2.0
        self.Cy = (bbox.YMax + bbox.YMin) / 2.0
        self.Cz = (bbox.ZMax + bbox.ZMin) / 2.0

        # Local coordinate mapping based on chosen axis
        # (a, b) represent the cross section plane, c represents the primary extrusion/cylinder axis
        if axis == "X":
            self.local_C_a, self.local_C_b, self.local_C_c = self.Cy, self.Cz, self.Cx
            self.a_min, self.a_max = bbox.YMin, bbox.YMax
            self.b_min, self.b_max = bbox.ZMin, bbox.ZMax
            self.c_min, self.c_max = bbox.XMin, bbox.XMax
        elif axis == "Y":
            self.local_C_a, self.local_C_b, self.local_C_c = self.Cz, self.Cx, self.Cy
            self.a_min, self.a_max = bbox.ZMin, bbox.ZMax
            self.b_min, self.b_max = bbox.XMin, bbox.XMax
            self.c_min, self.c_max = bbox.YMin, bbox.YMax
        else:
            self.local_C_a, self.local_C_b, self.local_C_c = self.Cx, self.Cy, self.Cz
            self.a_min, self.a_max = bbox.XMin, bbox.XMax
            self.b_min, self.b_max = bbox.YMin, bbox.YMax
            self.c_min, self.c_max = bbox.ZMin, bbox.ZMax

        self.max_dim = max(
            bbox.XMax - bbox.XMin,
            bbox.YMax - bbox.YMin,
            bbox.ZMax - bbox.ZMin,
        )
        self.R = max(self.a_max - self.a_min, self.b_max - self.b_min) / 2.0

    def to_global(self, a: float, b: float, c: float) -> App.Vector:
        """Translates local (a,b,c) parameters to a global App.Vector based on primary axis."""
        if self.axis == "X": return App.Vector(c, a, b)
        if self.axis == "Y": return App.Vector(b, c, a)
        return App.Vector(a, b, c)

    def get_c_val(self, pt: App.Vector) -> float:
        """Gets the coordinate value of a vector along the primary axis."""
        if self.axis == "X": return pt.x
        if self.axis == "Y": return pt.y
        return pt.z

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
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
    name = "Base"

    def __init__(self, target_shape, bbox, target_face=None, axis="Z"):
        super().__init__(target_shape, bbox, target_face, axis=axis)
        self.wrap_scale = 1.0

    def get_clipping_shape(self, border_size: float):
        safe_size = self.max_dim * 2.0 + BOUNDS_PADDING
        if border_size > 0.0:
            c_min = self.c_min + border_size
            c_max = self.c_max - border_size
            if c_max > c_min:
                if self.axis == "X":
                    safe_box = Part.makeBox(c_max - c_min, safe_size, safe_size)
                    safe_box.translate(App.Vector(c_min, self.Cy - safe_size / 2.0, self.Cz - safe_size / 2.0))
                elif self.axis == "Y":
                    safe_box = Part.makeBox(safe_size, c_max - c_min, safe_size)
                    safe_box.translate(App.Vector(self.Cx - safe_size / 2.0, c_min, self.Cz - safe_size / 2.0))
                else:
                    safe_box = Part.makeBox(safe_size, safe_size, c_max - c_min)
                    safe_box.translate(App.Vector(self.Cx - safe_size / 2.0, self.Cy - safe_size / 2.0, c_min))
                return safe_box
        return None

    def is_tile_valid(self, test_pts, inclusion_threshold: float) -> bool:
        if inclusion_threshold <= 0.0:
            return True

        pts_to_check = (test_pts[:-1] if
                        (len(test_pts) > 1 and test_pts[0].isEqual(
                            test_pts[-1], TOL_STRICT)) else test_pts)

        if not pts_to_check:
            return False

        def is_inside(pt):
            return self.c_min - TOL_RELAXED <= self.get_c_val(pt) <= self.c_max + TOL_RELAXED

        if inclusion_threshold >= PERCENT_MAX:
            return all(is_inside(pt) for pt in pts_to_check)

        inside_count = sum(1 for pt in pts_to_check if is_inside(pt))
        return (inside_count / len(pts_to_check)) >= (inclusion_threshold / PERCENT_SCALE)

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
