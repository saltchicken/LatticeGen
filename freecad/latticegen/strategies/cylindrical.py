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
    """Simple cylindrical projection wrapped around Z axis."""

    def setup_bounds(self, border_size: float, offset_x: float,
                     offset_y: float):
        return 0.0, 2 * math.pi * self.R, self.bbox.ZMin, self.bbox.ZMax, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        theta = u / self.R
        pos = App.Vector(self.Cx + self.R * math.cos(theta),
                         self.Cy + self.R * math.sin(theta), v)
        norm = App.Vector(math.cos(theta), math.sin(theta), 0)

        tan_u = App.Vector(-math.sin(theta), math.cos(theta),
                           0) * self.wrap_scale
        tan_v = App.Vector(0, 0, 1) * self.wrap_scale
        return pos, norm, tan_u, tan_v


class ProjectedCylindricalStretchedStrategy(WrapStrategy):
    """Raycast cylindrical projection with dynamic stretching."""

    def setup_bounds(self, border_size: float, offset_x: float,
                     offset_y: float):
        return 0.0, 2 * math.pi * self.R, self.bbox.ZMin, self.bbox.ZMax, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        theta = u / self.R
        p_center = App.Vector(self.Cx, self.Cy, v)
        ray_dir = App.Vector(math.cos(theta), math.sin(theta), 0)
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes,
                      key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else:
            pos = App.Vector(self.Cx + self.R * math.cos(theta),
                             self.Cy + self.R * math.sin(theta), v)

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir,
                                          hit_shape)

        tan_u = App.Vector(0, 0, 1).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = App.Vector(-math.sin(theta), math.cos(theta), 0)
        tan_u.normalize()

        tan_v = norm.cross(tan_u).normalize()

        r_hit = (pos - p_center).Length
        scale_u = self.wrap_scale * (
            r_hit / self.R) if self.R > TOL_STRICT else self.wrap_scale
        scale_v = self.wrap_scale / max(abs(tan_v.z), MIN_DENOM)

        return pos, norm, tan_u * scale_u, tan_v * scale_v


class ProjectedCylindricalUniformStrategy(WrapStrategy):
    """Raycast cylindrical projection with uniform cell scaling."""

    def __init__(self, target_shape, bbox, target_face=None):
        super().__init__(target_shape, bbox, target_face)
        self.true_R = self.R

    def setup_bounds(self, border_size: float, offset_x: float,
                     offset_y: float):
        return 0.0, 2 * math.pi * self.R, self.bbox.ZMin, self.bbox.ZMax, offset_x, offset_y

    def setup_grid(self, dx: float, dy: float, u_min: float, u_max: float,
                   v_min: float, v_max: float, is_staggered: bool):
        p_center = App.Vector(self.Cx, self.Cy, (v_max + v_min) / 2.0)
        ray = Part.makeLine(p_center,
                            p_center + App.Vector(self.max_dim * 2, 0, 0))
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
        p_center = App.Vector(self.Cx, self.Cy, v)
        ray_dir = App.Vector(math.cos(theta), math.sin(theta), 0)
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes,
                      key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else:
            pos = App.Vector(self.Cx + self.R * math.cos(theta),
                             self.Cy + self.R * math.sin(theta), v)

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir,
                                          hit_shape)

        tan_u = App.Vector(0, 0, 1).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = App.Vector(-math.sin(theta), math.cos(theta), 0)

        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()

        return pos, norm, tan_u * self.wrap_scale, tan_v * self.wrap_scale
