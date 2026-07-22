"""Tile generation factory and classes for 2D patterns."""

import math
import Part


class BaseTile:
    """Base class that automatically registers new patterns into its own encapsulated registry."""
    name = "Base"
    _registry = {}  # Class attribute replaces the global variable

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # We skip registering any class that doesn't define a unique name 
        # (like BaseTile or intermediate classes like BaseCircleTile)
        if cls.name != "Base":
            BaseTile._registry[cls.name] = cls

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        """Default to a standard square grid spacing."""
        return 2.0 * step_radius, 2.0 * step_radius, False

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        raise NotImplementedError


class HexagonTile(BaseTile):
    name = "Hexagon"

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        dx = 1.5 * step_radius
        dy = math.sqrt(3) * step_radius
        return dx, dy, True

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


class SquareTile(BaseTile):
    name = "Square"
    # Inherits default 2.0 x 2.0 grid from BaseTile

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


class BaseCircleTile(BaseTile):
    """Shared creation logic for both circle types."""
    # Inherits name="Base", so it won't be added to the registry dropdown
    
    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        circle_edge = Part.makeCircle(radius, base_pos, norm)
        face = Part.Face(Part.Wire(circle_edge))
        return face, [base_pos]


class CircleGridTile(BaseCircleTile):
    name = "Circle (Grid)"
    # Inherits default 2.0 x 2.0 grid


class CircleStaggeredTile(BaseCircleTile):
    name = "Circle (Staggered)"

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        dx = math.sqrt(3) * step_radius
        dy = 2.0 * step_radius
        return dx, dy, True


class KagomeTile(BaseTile):
    name = "Kagome (Hexagram)"

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        dx = 1.5 * step_radius
        dy = math.sqrt(3) * step_radius
        return dx, dy, True

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, radius):
        inner_radius = radius / math.sqrt(3)
        local_pts = []
        for i in range(12):
            angle = math.radians(i * 30)
            r = radius if i % 2 == 0 else inner_radius
            local_pts.append((r * math.cos(angle), r * math.sin(angle)))

        test_pts_3d = [base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts]
        test_pts_3d.append(test_pts_3d[0])
        face = Part.Face(Part.makePolygon(test_pts_3d))
        return face, test_pts_3d


class TileFactory:
    """Instantiates a 2D tile generator based on the pattern string."""

    @staticmethod
    def create(pattern: str):
        # Fetch from the encapsulated class attribute
        return BaseTile._registry.get(pattern, HexagonTile)

    @staticmethod
    def get_available_patterns() -> list:
        # Fetch keys from the encapsulated class attribute
        return list(BaseTile._registry.keys())
