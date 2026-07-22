"""Planar mapping strategy variants."""

import DraftGeomUtils
import FreeCAD as App
import Part

from freecad.latticegen.constants import BOOL_OVERSHOOT
from freecad.latticegen.constants import BOOL_OVERSHOOT_LARGE
from freecad.latticegen.constants import BOUNDS_PADDING
from freecad.latticegen.constants import PERCENT_MAX
from freecad.latticegen.constants import PERCENT_SCALE
from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.constants import TOL_STRICT
from freecad.latticegen.strategies.base import BaseMappingStrategy
from freecad.latticegen.utils import calculate_projected_normal


class PlanarStrategy(BaseMappingStrategy):
    """Direct planar projection on the selected Axis plane."""
    name = "Planar"

    def setup_bounds(self, border_size: float, offset_x: float, offset_y: float):
        return self.a_min, self.a_max, self.b_min, self.b_max, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        pos = self.to_global(u, v, self.c_min - BOOL_OVERSHOOT)
        norm = self.to_global(0, 0, 1)
        tan_u = self.to_global(1, 0, 0)
        tan_v = self.to_global(0, 1, 0)
        return pos, norm, tan_u, tan_v

    def get_base_pos(self, pos: App.Vector, norm: App.Vector) -> App.Vector:
        return pos

    def get_extrude_vector(self, norm: App.Vector, extrude_depth: float, z_height: float) -> App.Vector:
        span = self.c_max - self.c_min + BOOL_OVERSHOOT_LARGE
        return self.to_global(0, 0, span)

    def get_clipping_shape(self, border_size: float):
        base_face = None

        if self.target_shape.ShapeType in ["Face", "Wire"]:
            base_face = self.target_shape
        else:
            c_mid = (self.c_max + self.c_min) / 2.0
            plane_dx = (self.a_max - self.a_min) + (BOUNDS_PADDING * 2)
            plane_dy = (self.b_max - self.b_min) + (BOUNDS_PADDING * 2)
            plane_pos = self.to_global(self.a_min - BOUNDS_PADDING, self.b_min - BOUNDS_PADDING, c_mid)
            plane_norm = self.to_global(0, 0, 1)

            plane = Part.makePlane(plane_dx, plane_dy, plane_pos, plane_norm)
            cross_section = self.target_shape.section(plane)

            if cross_section.Edges:
                wires = DraftGeomUtils.findWires(cross_section.Edges)
                closed_wires = [w for w in wires if w.isClosed()]
                if closed_wires:
                    closed_wires.sort(key=lambda w: w.Length, reverse=True)
                    base_face = Part.Face(closed_wires[0])

        if not base_face:
            return None

        try:
            offset_shape = base_face
            if border_size > 0.0:
                offset_shape = base_face.makeOffset2D(-border_size)
                if isinstance(offset_shape, list) and offset_shape:
                    offset_shape = offset_shape[0]
                if offset_shape and offset_shape.ShapeType == "Wire":
                    offset_shape = Part.Face(offset_shape)

            if offset_shape and not offset_shape.isNull():
                current_c = self.get_c_val(offset_shape.CenterOfMass)
                c_offset = (self.c_min - BOOL_OVERSHOOT) - current_c
                offset_shape.translate(self.to_global(0, 0, c_offset))

                extrude_c = self.c_max + BOOL_OVERSHOOT_LARGE - (self.c_min - BOOL_OVERSHOOT)
                return offset_shape.extrude(self.to_global(0, 0, extrude_c))
        except Exception:
            pass

        return None

    def is_tile_valid(self, test_pts, inclusion_threshold: float) -> bool:
        if inclusion_threshold <= 0.0:
            return True

        def is_inside(px, py):
            # px and py are in local coordinates when testing tiles
            # We map back to local to test the bounding box effectively
            line_start = self.to_global(px, py, self.c_min - BOOL_OVERSHOOT)
            line_end = self.to_global(px, py, self.c_max + BOOL_OVERSHOOT)
            line = Part.makeLine(line_start, line_end)
            return line.distToShape(self.target_shape)[0] <= TOL_RELAXED

        pts_to_check = (test_pts[:-1] if
                        (len(test_pts) > 1 and test_pts[0].isEqual(
                            test_pts[-1], TOL_STRICT)) else test_pts)

        if not pts_to_check:
            return False

        if inclusion_threshold >= PERCENT_MAX:
            # We must map the test_pts back to local coords since they are global
            return all(is_inside(pt.x if self.axis!="X" else pt.y, pt.y if self.axis!="Y" else pt.z) for pt in pts_to_check)

        inside_count = sum(1 for pt in pts_to_check if is_inside(pt.x if self.axis!="X" else pt.y, pt.y if self.axis!="Y" else pt.z))
        return (inside_count / len(pts_to_check)) >= (inclusion_threshold / PERCENT_SCALE)


class ProjectedPlanarStrategy(PlanarStrategy):
    """Raycast projection onto target surface along the selected axis."""
    name = "Projected Planar"

    def get_mapping(self, u: float, v: float):
        p_top = self.to_global(u, v, self.c_max + self.max_dim)
        p_bot = self.to_global(u, v, self.c_min - self.max_dim)
        ray = Part.makeLine(p_top, p_bot)
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes, key=lambda vtx: self.get_c_val(vtx.Point)).Point
            hit_shape = True
        else:
            pos = self.to_global(u, v, self.c_max)

        norm = calculate_projected_normal(self.target_shape, pos, self.to_global(0, 0, 1), hit_shape)

        tan_u = self.to_global(0, 1, 0).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = self.to_global(1, 0, 0)

        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()

        return pos, norm, tan_u, tan_v

    def get_extrude_vector(self, norm: App.Vector, extrude_depth: float, z_height: float) -> App.Vector:
        return -norm * (extrude_depth + BOOL_OVERSHOOT_LARGE)
