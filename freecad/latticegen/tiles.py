"""Tile generation factory and classes for 2D patterns."""

import math
import Part

class HexagonTile:
    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        local_pts = [
            (
                radius * math.cos(math.radians(i * 60)),
                radius * math.sin(math.radians(i * 60)),
            )
            for i in range(6)
        ]
        test_pts_3d = [base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts]
        test_pts_3d.append(test_pts_3d[0])
        face = Part.Face(Part.makePolygon(test_pts_3d))
        return face, test_pts_3d

class SquareTile:
    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        local_pts = [
            (-radius, -radius),
            (radius, -radius),
            (radius, radius),
            (-radius, radius),
        ]
        test_pts_3d = [base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts]
        test_pts_3d.append(test_pts_3d[0])
        face = Part.Face(Part.makePolygon(test_pts_3d))
        return face, test_pts_3d

class CircleTile:
    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        circle_edge = Part.makeCircle(radius, base_pos, norm)
        face = Part.Face(Part.Wire(circle_edge))
        return face, [base_pos]  # Circles evaluate inclusion using just their center

class TileFactory:
    """Instantiates a 2D tile generator based on the pattern string."""
    @staticmethod
    def create(pattern: str):
        if pattern == "Hexagon":
            return HexagonTile
        elif pattern == "Square":
            return SquareTile
        elif "Circle" in pattern:
            return CircleTile
        return HexagonTile
