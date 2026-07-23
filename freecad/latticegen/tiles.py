import hashlib
import math

import Part

try:
    from scipy.spatial import Voronoi
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


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
    custom_parameters = [
        "VoronoiSeed", "VoronoiVariance", "VoronoiRelaxation", 
        "VoronoiGapVariance", "VoronoiBaseGrid", "VoronoiStretchU", "VoronoiStretchV"
    ]

    @classmethod
    def get_grid_dimensions(cls, step_radius: float):
        dx = 1.5 * step_radius
        dy = math.sqrt(3) * step_radius
        return dx, dy, True

    @staticmethod
    def create_face(base_pos, norm, tan_u, tan_v, config):
        if not HAS_SCIPY:
            return VoronoiTile._create_face_fallback(base_pos, norm, tan_u, tan_v, config)
            
        step_radius = config.tile_radius + config.gap
        variance = config.voronoi_variance
        
        # Grid Topology Setup
        if config.voronoi_base_grid == "Square":
            dx, dy, is_staggered = 2.0 * step_radius, 2.0 * step_radius, False
        else:
            dx, dy, is_staggered = 1.5 * step_radius, math.sqrt(3) * step_radius, True
            
        # Stretch setup (protect against division by zero)
        su = config.voronoi_stretch_u if config.voronoi_stretch_u > 0.01 else 1.0
        sv = config.voronoi_stretch_v if config.voronoi_stretch_v > 0.01 else 1.0
        
        def get_offset(lx, ly):
            gx = base_pos.x + tan_u.x * lx + tan_v.x * ly
            gy = base_pos.y + tan_u.y * lx + tan_v.y * ly
            gz = base_pos.z + tan_u.z * lx + tan_v.z * ly
            
            rx = round(gx, 1) + 0.0
            ry = round(gy, 1) + 0.0
            rz = round(gz, 1) + 0.0
            
            seed_str = f"{rx}_{ry}_{rz}_{config.voronoi_seed}"
            h = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
            
            def rand():
                nonlocal h
                h = (h * 1103515245 + 12345) & 0x7fffffff
                return (h / 0x7fffffff) * 2.0 - 1.0
                
            max_offset = variance * step_radius * 0.45
            
            # Divide by stretch factors here so that the initial seed points 
            # are mathematically morphed prior to Voronoi diagram generation.
            return (lx + rand() * max_offset) / su, (ly + rand() * max_offset) / sv

        points_2d = []
        center_idx = -1
        
        # Build a 5x5 local grid
        for i in range(-2, 3):
            for j in range(-2, 3):
                lx = i * dx
                ly = j * dy
                if is_staggered and i % 2 != 0:
                    ly += dy / 2.0
                    
                px, py = get_offset(lx, ly)
                points_2d.append([px, py])
                
                if i == 0 and j == 0:
                    center_idx = len(points_2d) - 1

        try:
            # 1. Relaxation (Lloyd's Algorithm)
            for _ in range(config.voronoi_relaxation):
                vor = Voronoi(points_2d)
                new_points = []
                for i, p in enumerate(points_2d):
                    region_idx = vor.point_region[i]
                    region = vor.regions[region_idx]
                    if -1 in region or not region:
                        new_points.append(p)
                    else:
                        poly = [vor.vertices[v] for v in region]
                        # Vertex average provides a stable centroid proxy for convex regions
                        cx = sum(v[0] for v in poly) / len(poly)
                        cy = sum(v[1] for v in poly) / len(poly)
                        new_points.append([cx, cy])
                points_2d = new_points
                
            # 2. Final Diagram computation
            vor = Voronoi(points_2d)
            region_idx = vor.point_region[center_idx]
            region = vor.regions[region_idx]
            
            if -1 in region or not region:
                raise ValueError("Unbounded Voronoi region generated")
                
            # Multiply by stretch factors to transform geometry back to target surface scale
            local_pts = [(vor.vertices[v_idx][0] * su, vor.vertices[v_idx][1] * sv) for v_idx in region]
            
            # 3. Gap Variance logic based on global position hash
            gap_var = config.voronoi_gap_variance
            if gap_var > 0.0:
                rx = round(base_pos.x, 1) + 0.0
                ry = round(base_pos.y, 1) + 0.0
                rz = round(base_pos.z, 1) + 0.0
                cv_hash_str = f"gap_{rx}_{ry}_{rz}_{config.voronoi_seed}"
                cv_hash = int(hashlib.md5(cv_hash_str.encode()).hexdigest()[:8], 16)
                gap_rnd = cv_hash / 0xffffffff
                
                # Bounded so cell scale never collapses entirely
                gap_scale = 1.0 - (gap_var * 0.7 * gap_rnd)
            else:
                gap_scale = 1.0
            
            # 4. Final Cell Scaling
            cx = sum(p[0] for p in local_pts) / len(local_pts)
            cy = sum(p[1] for p in local_pts) / len(local_pts)
            
            scale = (config.tile_radius / step_radius) * gap_scale if step_radius > 0 else 1.0
            
            scaled_pts = []
            for px, py in local_pts:
                sx = cx + (px - cx) * scale
                sy = cy + (py - cy) * scale
                scaled_pts.append((sx, sy))

            test_pts_3d = [
                base_pos + tan_u * lx + tan_v * ly for lx, ly in scaled_pts
            ]
            test_pts_3d.append(test_pts_3d[0])
            
            face = Part.Face(Part.makePolygon(test_pts_3d))
            return face, test_pts_3d
            
        except Exception:
            return VoronoiTile._create_face_fallback(base_pos, norm, tan_u, tan_v, config)

    @staticmethod
    def _create_face_fallback(base_pos, norm, tan_u, tan_v, config):
        """Legacy standalone Voronoi approximation logic if scipy isn't available."""
        radius = config.tile_radius
        variance = config.voronoi_variance
        
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
