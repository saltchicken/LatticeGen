"""Core pattern generation math and B-Rep solid construction engine."""

import math
import Part

from freecad.latticegen.constants import BOOL_OVERSHOOT_LARGE, FILLET_ALIGN_TOL, TOL_RELAXED
from freecad.latticegen.strategies import MappingFactory


def calculate_pattern_shape(
    target_obj,
    target_face=None,
    pattern: str = "Hexagon",
    tile_radius: float = 5.0,
    gap: float = 0.5,
    mode: str = "cut",
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    inclusion_threshold: float = 0.0,
    border_size: float = 0.0,
    fillet_radius: float = 0.0,
    mapping: str = "Planar",
    extrude_depth: float = 5.0,
    return_tool: bool = False,
):
    """Calculates and returns the resulting FreeCAD Shape of a patterned lattice."""
    target_shape = target_obj.Shape
    step_radius = tile_radius + gap
    pattern_faces = []

    # 1. Initialize strategy & bounds
    strategy = MappingFactory.create(mapping, target_shape, target_face)
    u_min, u_max, v_min, v_max, offset_x, offset_y = strategy.setup_bounds(border_size, offset_x, offset_y)
    clipping_volume = strategy.get_clipping_shape(border_size)

    # 2. Determine grid step dimensions
    is_staggered = False
    if pattern == "Hexagon":
        dx = 1.5 * step_radius
        dy = math.sqrt(3) * step_radius
        is_staggered = True
    elif pattern in ["Square", "Circle (Grid)"]:
        dx = dy = 2.0 * step_radius
    elif pattern == "Circle (Staggered)":
        dx = math.sqrt(3) * step_radius
        dy = 2.0 * step_radius
        is_staggered = True

    target_cols, rows, c_start, c_end, dx, dy, odd_y_offset = strategy.setup_grid(
        dx, dy, u_min, u_max, v_min, v_max, is_staggered
    )

    # 3. Generate 2D tile faces mapped to target surface
    for c in range(c_start, c_end):
        for r in range(-1, rows):
            u = u_min + c * dx + offset_x
            v = v_min + r * dy + offset_y

            if c % 2 != 0:
                v += odd_y_offset

            if not strategy.is_valid_uv(u, v, u_min, u_max, v_min, v_max):
                continue

            pos, norm, tan_u, tan_v = strategy.get_mapping(u, v)
            base_pos = strategy.get_base_pos(pos, norm)

            if "Circle" in pattern:
                circle_edge = Part.makeCircle(tile_radius, base_pos, norm)
                tile_face = Part.Face(Part.Wire(circle_edge))

                if strategy.is_tile_valid([base_pos], inclusion_threshold):
                    pattern_faces.append((tile_face, norm))
            else:
                if pattern == "Hexagon":
                    local_pts = [
                        (
                            tile_radius * math.cos(math.radians(i * 60)),
                            tile_radius * math.sin(math.radians(i * 60)),
                        )
                        for i in range(6)
                    ]
                else:  # Square
                    local_pts = [
                        (-tile_radius, -tile_radius),
                        (tile_radius, -tile_radius),
                        (tile_radius, tile_radius),
                        (-tile_radius, tile_radius),
                    ]

                test_pts_3d = [base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts]
                test_pts_3d.append(test_pts_3d[0])
                tile_face = Part.Face(Part.makePolygon(test_pts_3d))

                if strategy.is_tile_valid(test_pts_3d, inclusion_threshold):
                    pattern_faces.append((tile_face, norm))

    if not pattern_faces:
        if return_tool or mode != "cut":
            return Part.makeCompound([])
        return target_shape.copy()

    # 4. Extrude 2D faces into 3D pillars, apply fillets and clipping
    z_height = target_shape.BoundBox.ZMax - target_shape.BoundBox.ZMin + BOOL_OVERSHOOT_LARGE
    pillar_solids = []

    for tile_face, norm in pattern_faces:
        extrude_vec = strategy.get_extrude_vector(norm, extrude_depth, z_height)
        pillar = tile_face.extrude(extrude_vec)

        if fillet_radius > 0.0 and "Circle" not in pattern:
            edges_to_fillet = []
            for e in pillar.Edges:
                if e.Curve.TypeId == "Part::GeomLine":
                    edge_vec = (e.Vertexes[1].Point - e.Vertexes[0].Point).normalize()
                    if abs(edge_vec.dot(norm)) > FILLET_ALIGN_TOL:
                        edges_to_fillet.append(e)

            if edges_to_fillet:
                try:
                    filleted = pillar.makeFillet(fillet_radius, edges_to_fillet)
                    if not filleted.isNull():
                        pillar = filleted
                except Exception:
                    pass

        if clipping_volume:
            try:
                clipped = pillar.common(clipping_volume)
                if not clipped.isNull() and clipped.Volume > TOL_RELAXED:
                    pillar = clipped
                else:
                    continue
            except Exception:
                pass

        pillar_solids.append(pillar)

    pillars = Part.makeCompound(pillar_solids)

    if return_tool:
        return pillars

    return target_shape.cut(pillars) if mode == "cut" else target_shape.common(pillars)
