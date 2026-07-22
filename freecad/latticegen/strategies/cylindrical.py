"""Cylindrical mapping strategy variants."""

import math

import FreeCAD as App
import Part

from freecad.latticegen.constants import MIN_DENOM
from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.constants import TOL_STRICT
from freecad.latticegen.strategies.base import WrapStrategy
from freecad.latticegen.utils import calculate_projected_normal


class CylindricalStrategy(WrapStrategy):
    """Simple cylindrical projection wrapped around the selected axis."""
    name = "Cylindrical"

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
        return 0.0, 2 * math.pi * self.R, self.c_min, self.c_max, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        theta = u / self.R
        pos = self.to_global(self.local_C_a + self.R * math.cos(theta),
                             self.local_C_b + self.R * math.sin(theta), v)
        norm = self.to_global(math.cos(theta), math.sin(theta), 0)

        tan_u = self.to_global(-math.sin(theta), math.cos(theta), 0) * self.wrap_scale
        tan_v = self.to_global(0, 0, 1) * self.wrap_scale
        return pos, norm, tan_u, tan_v


class ProjectedCylindricalStretchedStrategy(WrapStrategy):
    """Raycast cylindrical projection with dynamic stretching."""
    name = "Projected Cylindrical (Stretched)"

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
        return 0.0, 2 * math.pi * self.R, self.c_min, self.c_max, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        theta = u / self.R
        p_center = self.to_global(self.local_C_a, self.local_C_b, v)
        ray_dir = self.to_global(math.cos(theta), math.sin(theta), 0)
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes,
                      key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else:
            pos = self.to_global(self.local_C_a + self.R * math.cos(theta),
                                 self.local_C_b + self.R * math.sin(theta), v)

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir, hit_shape)

        tan_u = self.to_global(0, 0, 1).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = self.to_global(-math.sin(theta), math.cos(theta), 0)
        tan_u.normalize()

        tan_v = norm.cross(tan_u).normalize()

        r_hit = (pos - p_center).Length
        scale_u = self.wrap_scale * (
            r_hit / self.R) if self.R > TOL_STRICT else self.wrap_scale
            
        # Ensure we evaluate the tangent along the correct primary axis
        scale_v = self.wrap_scale / max(abs(tan_v.dot(self.to_global(0, 0, 1))), MIN_DENOM)

        return pos, norm, tan_u * scale_u, tan_v * scale_v


class ProjectedCylindricalUniformStrategy(WrapStrategy):
    """Raycast cylindrical projection with uniform cell scaling."""
    name = "Projected Cylindrical (Uniform)"

    # FIX: Accept axis and pass it to super()
    def __init__(self, target_shape, bbox, target_face=None, axis="Z"):
        super().__init__(target_shape, bbox, target_face, axis=axis)
        self.true_R = self.R

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
        return 0.0, 2 * math.pi * self.R, self.c_min, self.c_max, offset_x, offset_y

    def setup_grid(self, dx: float, dy: float, u_min: float, u_max: float,
                   v_min: float, v_max: float, is_staggered: bool):
        p_center = self.to_global(self.local_C_a, self.local_C_b, (v_max + v_min) / 2.0)
        ray = Part.makeLine(p_center, p_center + self.to_global(self.max_dim * 2, 0, 0))
        intersections = self.target_shape.common(ray)

        if intersections.Vertexes:
            self.true_R = (intersections.Vertexes[0].Point - p_center).Length
        else:
            self.true_R = self.R

        true_circumference = 2 * math.pi * self.true_R
        target_cols = max(2, round(true_circumference / dx))

        if is_staggered and target_cols % 2 != 0:
            target_cols += 1

        self.wrap_scale = (true_circumference / target_cols) / dx

        dx_uv = (2 * math.pi * self.R) / target_cols
        dy_uv = dy * self.wrap_scale

        odd_y_offset = dy_uv / 2.0 if is_staggered else 0.0
        rows = max(2, int((v_max - v_min) / dy_uv) + 2)

        return target_cols, rows, 0, target_cols, dx_uv, dy_uv, odd_y_offset

    def get_mapping(self, u: float, v: float):
        theta = u / self.R
        p_center = self.to_global(self.local_C_a, self.local_C_b, v)
        ray_dir = self.to_global(math.cos(theta), math.sin(theta), 0)
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes,
                      key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else:
            pos = self.to_global(self.local_C_a + self.R * math.cos(theta),
                                 self.local_C_b + self.R * math.sin(theta), v)

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir, hit_shape)

        tan_u = self.to_global(0, 0, 1).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = self.to_global(-math.sin(theta), math.cos(theta), 0)

        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()

        return pos, norm, tan_u * self.wrap_scale, tan_v * self.wrap_scale
