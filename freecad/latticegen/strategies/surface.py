"""Parametric surface UV mapping strategy."""

import FreeCAD as App

from freecad.latticegen.constants import PERCENT_SCALE
from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.strategies.base import BaseMappingStrategy


class SurfaceUVStrategy(BaseMappingStrategy):
    """Direct mapping using face UV parametric domain."""

    def setup_bounds(self, border_size: float, offset_x: float,
                     offset_y: float):
        if not self.target_face:
            return 0, 0, 0, 0, offset_x, offset_y

        u_min, u_max, v_min, v_max = self.target_face.ParameterRange

        if border_size > 0.0:
            mid_u, mid_v = (u_min + u_max) / 2.0, (v_min + v_max) / 2.0
            len_u = (self.target_face.valueAt(u_max, mid_v) -
                     self.target_face.valueAt(u_min, mid_v)).Length
            len_v = (self.target_face.valueAt(mid_u, v_max) -
                     self.target_face.valueAt(mid_u, v_min)).Length

            scale_u = (u_max - u_min) / len_u if len_u > TOL_RELAXED else 0
            scale_v = (v_max - v_min) / len_v if len_v > TOL_RELAXED else 0

            u_min += border_size * scale_u
            u_max -= border_size * scale_u
            v_min += border_size * scale_v
            v_max -= border_size * scale_v

        ur, vr = (u_max - u_min), (v_max - v_min)
        offset_x = (offset_x / PERCENT_SCALE) * ur if ur > 0 else offset_x
        offset_y = (offset_y / PERCENT_SCALE) * vr if vr > 0 else offset_y

        return u_min, u_max, v_min, v_max, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        pos = self.target_face.valueAt(u, v)
        norm = self.target_face.normalAt(u, v).normalize()

        tan_u = App.Vector(0, 0, 1).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = App.Vector(1, 0, 0)

        tan_u.normalize()
        return pos, norm, tan_u, norm.cross(tan_u).normalize()

    def is_valid_uv(self, u: float, v: float, u_min: float, u_max: float,
                    v_min: float, v_max: float) -> bool:
        return (u_min <= u <= u_max) and (v_min <= v <= v_max)

    def setup_grid(self, dx: float, dy: float, u_min: float, u_max: float,
                   v_min: float, v_max: float, is_staggered: bool):
        dx = (dx / self.max_dim) * (u_max - u_min)
        dy = (dy / self.max_dim) * (v_max - v_min)
        odd_y_offset = dy / 2.0 if is_staggered else 0.0
        target_cols = max(2, int((u_max - u_min) / dx) + 2)
        rows = max(2, int((v_max - v_min) / dy) + 2)
        return target_cols, rows, -1, target_cols, dx, dy, odd_y_offset
