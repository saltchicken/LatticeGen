"""Core pattern generation math and B-Rep solid construction engine."""

import math

import FreeCAD as App
import Part

from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.constants import BOOL_OVERSHOOT_LARGE
from freecad.latticegen.constants import FILLET_ALIGN_TOL
from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.strategies import MappingFactory
from freecad.latticegen.tiles import TileFactory


def _generate_2d_tiles(target_shape, strategy, config: LatticeConfig):
    step_radius = config.tile_radius + config.gap
    u_min, u_max, v_min, v_max, offset_x, offset_y = strategy.setup_bounds(
        config.border_size, config.offset_x, config.offset_y)

    tile_generator = TileFactory.create(config.pattern)
    dx, dy, is_staggered = tile_generator.get_grid_dimensions(step_radius)

    target_cols, rows, c_start, c_end, dx, dy, odd_y_offset = strategy.setup_grid(
        dx, dy, u_min, u_max, v_min, v_max, is_staggered)

    pattern_faces = []

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

            # Pass the full config so tiles can access custom parameters
            tile_face, test_pts = tile_generator.create_face(
                base_pos, norm, tan_u, tan_v, config)

            if strategy.is_tile_valid(test_pts, config.inclusion_threshold):
                pattern_faces.append((tile_face, norm))

    return pattern_faces


def _build_3d_pillars(pattern_faces, strategy, target_shape,
                      config: LatticeConfig):
    z_height = target_shape.BoundBox.ZMax - target_shape.BoundBox.ZMin + BOOL_OVERSHOOT_LARGE
    clipping_volume = strategy.get_clipping_shape(config.border_size)
    pillar_solids = []

    for tile_face, norm in pattern_faces:
        extrude_vec = strategy.get_extrude_vector(norm, config.extrude_depth,
                                                  z_height)
        pillar = tile_face.extrude(extrude_vec)

        if config.fillet_radius > 0.0 and "Circle" not in config.pattern:
            edges_to_fillet = []
            for e in pillar.Edges:
                if e.Curve.TypeId == "Part::GeomLine":
                    edge_vec = (e.Vertexes[1].Point -
                                e.Vertexes[0].Point).normalize()
                    if abs(edge_vec.dot(norm)) > FILLET_ALIGN_TOL:
                        edges_to_fillet.append(e)

            if edges_to_fillet:
                try:
                    filleted = pillar.makeFillet(config.fillet_radius,
                                                 edges_to_fillet)
                    if not filleted.isNull():
                        pillar = filleted
                except Part.OCCError as e:
                    App.Console.PrintWarning(f"Fillet failed on a pillar: {e}\n")

        if clipping_volume:
            try:
                clipped = pillar.common(clipping_volume)
                if not clipped.isNull() and clipped.Volume > TOL_RELAXED:
                    pillar = clipped
                else:
                    continue
            except Part.OCCError as e:
                App.Console.PrintWarning(f"Clipping failed on a pillar: {e}\n")

        pillar_solids.append(pillar)

    return Part.makeCompound(pillar_solids)


def _apply_boolean(target_shape, tool_compound, operation_mode):
    if operation_mode == "cut":
        return target_shape.cut(tool_compound)
    return target_shape.common(tool_compound)


def generate_lattice_shape(target_obj,
                           config: LatticeConfig,
                           target_face=None,
                           return_tool=False):
    """Calculates and returns the resulting FreeCAD Shape of a patterned lattice."""
    target_shape = target_obj.Shape
    strategy = MappingFactory.create(config.mapping, target_shape, target_face, config.axis)

    # 1. Generate the 2D base profiles mapped to the surface
    pattern_faces = _generate_2d_tiles(target_shape, strategy, config)

    if not pattern_faces:
        if return_tool or config.operation_mode != "cut":
            return Part.makeCompound([])
        return target_shape.copy()

    # 2. Extrude, fillet, and clip to create the 3D tool
    tool_compound = _build_3d_pillars(pattern_faces, strategy, target_shape,
                                      config)

    if return_tool:
        return tool_compound

    # 3. Apply the final boolean
    return _apply_boolean(target_shape, tool_compound, config.operation_mode)
