"""Spherical and Radial mapping strategy variants."""

import math

import FreeCAD as App
import Part

from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.constants import TOL_STRICT
from freecad.latticegen.strategies.base import WrapStrategy
from freecad.latticegen.utils import calculate_projected_normal


class SphericalStrategy(WrapStrategy):
    """Spherical polar coordinate projection."""
    name = "Spherical"

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
        self.R = self.max_dim / 2.0
        return 0.0, 2 * math.pi * self.R, 0.0, math.pi * self.R, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        theta, phi = u / self.R, v / self.R

        x_val = self.local_C_a + self.R * math.cos(theta) * math.sin(phi)
        y_val = self.local_C_b + self.R * math.sin(theta) * math.sin(phi)
        z_val = self.local_C_c + self.R * math.cos(phi)
        pos = self.to_global(x_val, y_val, z_val)

        norm = self.to_global(
            math.cos(theta) * math.sin(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(phi),
        ).normalize()

        tan_u = self.to_global(-math.sin(theta), math.cos(theta), 0)
        if tan_u.Length < TOL_RELAXED:
            tan_u = self.to_global(1, 0, 0)

        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()

        return pos, norm, tan_u * (self.wrap_scale * math.sin(phi)), tan_v * self.wrap_scale

    def is_valid_uv(self, u: float, v: float, u_min: float, u_max: float,
                    v_min: float, v_max: float) -> bool:
        return v_min <= v <= v_max


class ProjectedSphericalStrategy(SphericalStrategy):
    """Raycast spherical projection with latitude pinching."""
    name = "Projected Spherical"

    def get_mapping(self, u: float, v: float):
        theta, phi = u / self.R, v / self.R
        p_center = self.to_global(self.local_C_a, self.local_C_b, self.local_C_c)

        ray_dir = self.to_global(
            math.cos(theta) * math.sin(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(phi),
        ).normalize()
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes,
                      key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else:
            pos = p_center + ray_dir * self.R

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir, hit_shape)

        tan_u = self.to_global(0, 0, 1).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = self.to_global(1, 0, 0)

        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()

        r_hit = (pos - p_center).Length
        base_scale = r_hit / self.R if self.R > TOL_STRICT else 1.0

        scale_u = self.wrap_scale * base_scale * math.sin(phi)
        scale_v = self.wrap_scale * base_scale

        return pos, norm, tan_u * scale_u, tan_v * scale_v


class RadialStrategy(WrapStrategy):
    """Radial disk projection on top planar faces."""
    name = "Radial"

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
        return 0.0, 2 * math.pi * self.R, 0.0, self.R, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        theta = u / self.R
        pos = self.to_global(self.local_C_a + v * math.cos(theta),
                             self.local_C_b + v * math.sin(theta), self.c_max)
        norm = self.to_global(0, 0, 1)
        tan_u = self.to_global(-math.sin(theta), math.cos(theta), 0)
        tan_v = self.to_global(math.cos(theta), math.sin(theta), 0)
        return pos, norm, tan_u, tan_v

    def get_base_pos(self, pos: App.Vector, norm: App.Vector) -> App.Vector:
        return pos

    def get_extrude_vector(self, norm: App.Vector, extrude_depth: float,
                           z_height: float) -> App.Vector:
        return self.to_global(0, 0, z_height)

    def is_valid_uv(self, u: float, v: float, u_min: float, u_max: float,
                    v_min: float, v_max: float) -> bool:
        return v <= v_max
