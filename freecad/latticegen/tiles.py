"""Tile generation factory and classes for 2D patterns."""

import math

import Part


class HexagonTile:

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        local_pts = [(
            radius * math.cos(math.radians(i * 60)),
            radius * math.sin(math.radians(i * 60)),
        ) for i in range(6)]
        test_pts_3d = [
            base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts
        ]
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
        test_pts_3d = [
            base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts
        ]
        test_pts_3d.append(test_pts_3d[0])
        face = Part.Face(Part.makePolygon(test_pts_3d))
        return face, test_pts_3d


class CircleTile:

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        circle_edge = Part.makeCircle(radius, base_pos, norm)
        face = Part.Face(Part.Wire(circle_edge))
        return face, [base_pos
                     ]  # Circles evaluate inclusion using just their center

class KagomeTile:
    """
    Generates a 12-pointed Hexagram (Star of David) tile. 
    When cut on a staggered grid, it leaves behind a Kagome lattice web.
    """
    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        # A standard hexagram has an inner radius that is 1/sqrt(3) of the outer radius
        inner_radius = radius / math.sqrt(3)
        local_pts = []
        
        for i in range(12):
            angle = math.radians(i * 30)
            # Alternate between outer and inner radius
            r = radius if i % 2 == 0 else inner_radius
            
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            local_pts.append((x, y))

        test_pts_3d = [
            base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts
        ]
        test_pts_3d.append(test_pts_3d[0])  # Close the polygon
        
        face = Part.Face(Part.makePolygon(test_pts_3d))
        return face, test_pts_3d

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
        elif pattern == "Kagome (Hexagram)":
            return KagomeTile
        return HexagonTile
