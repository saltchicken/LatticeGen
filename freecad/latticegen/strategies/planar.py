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
    """Direct planar projection on the XY plane."""
    
    name = "Planar"

    def setup_bounds(self, border_size: float, offset_x: float,
                     offset_y: float):
        return self.bbox.XMin, self.bbox.XMax, self.bbox.YMin, self.bbox.YMax, offset_x, offset_y

    def get_mapping(self, u: float, v: float):
        pos = App.Vector(u, v, self.bbox.ZMin - BOOL_OVERSHOOT)
        norm = App.Vector(0, 0, 1)
        tan_u = App.Vector(1, 0, 0)
        tan_v = App.Vector(0, 1, 0)
        return pos, norm, tan_u, tan_v

    def get_base_pos(self, pos: App.Vector, norm: App.Vector) -> App.Vector:
        return pos

    def get_extrude_vector(self, norm: App.Vector, extrude_depth: float,
                           z_height: float) -> App.Vector:
        return App.Vector(0, 0, z_height)

    def get_clipping_shape(self, border_size: float):
        base_face = None

        if self.target_shape.ShapeType in ["Face", "Wire"]:
            base_face = self.target_shape
        else:
            z_mid = (self.bbox.ZMax + self.bbox.ZMin) / 2.0
            plane_dx = (self.bbox.XMax - self.bbox.XMin) + (BOUNDS_PADDING * 2)
            plane_dy = (self.bbox.YMax - self.bbox.YMin) + (BOUNDS_PADDING * 2)
            plane_pos = App.Vector(self.bbox.XMin - BOUNDS_PADDING,
                                   self.bbox.YMin - BOUNDS_PADDING, z_mid)
            plane_norm = App.Vector(0, 0, 1)

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
                current_z = offset_shape.BoundBox.ZMin
                z_offset = self.bbox.ZMin - BOOL_OVERSHOOT - current_z
                offset_shape.translate(App.Vector(0, 0, z_offset))

                extrude_z = self.bbox.ZMax + BOOL_OVERSHOOT_LARGE - (
                    self.bbox.ZMin - BOOL_OVERSHOOT)
                return offset_shape.extrude(App.Vector(0, 0, extrude_z))
        except Exception:
            pass

        return None

    def is_tile_valid(self, test_pts, inclusion_threshold: float) -> bool:
        if inclusion_threshold <= 0.0:
            return True

        def is_inside(px, py):
            line_start = App.Vector(px, py, self.bbox.ZMin - BOOL_OVERSHOOT)
            line_end = App.Vector(px, py, self.bbox.ZMax + BOOL_OVERSHOOT)
            line = Part.makeLine(line_start, line_end)
            return line.distToShape(self.target_shape)[0] <= TOL_RELAXED

        pts_to_check = (test_pts[:-1] if
                        (len(test_pts) > 1 and test_pts[0].isEqual(
                            test_pts[-1], TOL_STRICT)) else test_pts)

        if not pts_to_check:
            return False

        if inclusion_threshold >= PERCENT_MAX:
            return all(is_inside(pt.x, pt.y) for pt in pts_to_check)

        inside_count = sum(1 for p in pts_to_check if is_inside(p.x, p.y))
        return (inside_count / len(pts_to_check)) >= (inclusion_threshold /
                                                      PERCENT_SCALE)


class ProjectedPlanarStrategy(PlanarStrategy):
    """Raycast projection onto target surface along Z axis."""
    
    name = "Projected Planar"

    def get_mapping(self, u: float, v: float):
        p_top = App.Vector(u, v, self.bbox.ZMax + self.max_dim)
        p_bot = App.Vector(u, v, self.bbox.ZMin - self.max_dim)
        ray = Part.makeLine(p_top, p_bot)
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes, key=lambda vtx: vtx.Point.z).Point
            hit_shape = True
        else:
            pos = App.Vector(u, v, self.bbox.ZMax)

        norm = calculate_projected_normal(self.target_shape, pos,
                                          App.Vector(0, 0, 1), hit_shape)

        tan_u = App.Vector(0, 1, 0).cross(norm)
        if tan_u.Length < TOL_RELAXED:
            tan_u = App.Vector(1, 0, 0)

        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()

        return pos, norm, tan_u, tan_v

    def get_extrude_vector(self, norm: App.Vector, extrude_depth: float,
                           z_height: float) -> App.Vector:
        return -norm * (extrude_depth + BOOL_OVERSHOOT_LARGE)
