import hashlib
import math

import Part


class BaseTile:
    """Base class that automatically registers new patterns into its own encapsulated registry."""
    name = "Base"
    _registry = {} 
    
    # UI Metadata
    unsupported_parameters = []
    custom_parameters = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.name != "Base":
            BaseTile._registry[cls.name] = cls

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        """Default to a standard square grid spacing."""
        return 2.0 * step_radius, 2.0 * step_radius, False

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, config):
        raise NotImplementedError


class HexagonTile(BaseTile):
    name = "Hexagon"

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        dx = 1.5 * step_radius
        dy = math.sqrt(3) * step_radius
        return dx, dy, True

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, config):
        radius = config.tile_radius
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

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, config):
        radius = config.tile_radius
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

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, config):
        circle_edge = Part.makeCircle(config.tile_radius, base_pos, norm)
        face = Part.Face(Part.Wire(circle_edge))
        return face, [base_pos]


class CircleGridTile(BaseCircleTile):
    name = "Circle (Grid)"


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
    def create_face(base_pos, norm, tan_u, tan_v, config):
        radius = config.tile_radius
        inner_radius = radius / math.sqrt(3)
        local_pts = []
        for i in range(12):
            angle = math.radians(i * 30)
            r = radius if i % 2 == 0 else inner_radius
            local_pts.append((r * math.cos(angle), r * math.sin(angle)))

        test_pts_3d = [
            base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts
        ]
        test_pts_3d.append(test_pts_3d[0])
        face = Part.Face(Part.makePolygon(test_pts_3d))
        return face, test_pts_3d


class VoronoiTile(BaseTile):
    name = "Voronoi"
    
    # Request custom UI parameters
    custom_parameters = ["VoronoiSeed", "VoronoiVariance"]

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        dx = 1.5 * step_radius
        dy = math.sqrt(3) * step_radius
        return dx, dy, True

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, config):
        radius = config.tile_radius
        variance = config.voronoi_variance
        
        # Deterministic pseudo-random seed incorporating the custom UI seed
        seed_str = f"{round(base_pos.x, 2)}_{round(base_pos.y, 2)}_{round(base_pos.z, 2)}_{config.voronoi_seed}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        
        def rand():
            nonlocal seed
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            return seed / 0x7fffffff

        num_sides = 5 + int(rand() * 3)
        base_angle = rand() * math.pi * 2
        
        local_pts = []
        for i in range(num_sides):
            slice_angle = 2 * math.pi / num_sides
            angle = base_angle + i * slice_angle + slice_angle * 0.4 * (rand() - 0.5)
            
            # Apply user variance config to scaling
            scale_min = 1.0 - (variance * 0.5)
            r = radius * (scale_min + (variance * 0.5) * rand())
            
            lx = r * math.cos(angle)
            ly = r * math.sin(angle)
            local_pts.append((lx, ly))

        test_pts_3d = [
            base_pos + tan_u * lx + tan_v * ly for lx, ly in local_pts
        ]
        test_pts_3d.append(test_pts_3d[0])
        
        try:
            face = Part.Face(Part.makePolygon(test_pts_3d))
        except Part.OCCError:
            # Fallback to standard hexagon if extreme rounding/scale creates an invalid polygon
            return HexagonTile.create_face(base_pos, norm, tan_u, tan_v, config)
            
        return face, test_pts_3d


class TileFactory:
    """Instantiates a 2D tile generator based on the pattern string."""

    @staticmethod
    def create(pattern: str):
        return BaseTile._registry.get(pattern, HexagonTile)

    @staticmethod
    def get_available_patterns() -> list:
        return list(BaseTile._registry.keys())
