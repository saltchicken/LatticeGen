import FreeCAD as App
import Part
import math
import DraftGeomUtils

def calculate_projected_normal(target_shape, pos, ray_dir, hit_shape=True):
    if not hit_shape: return ray_dir
    test_pt = pos + ray_dir * 0.1
    dist, pts, info = target_shape.distToShape(Part.Vertex(test_pt))
    if pts and dist > 1e-5:
        norm = test_pt - pts[0][0]
        if norm.Length > 1e-5:
            norm.normalize()
            if norm.dot(ray_dir) > 0.5: return norm
    return ray_dir

class BaseMappingStrategy:
    def __init__(self, target_shape, bbox, target_face=None):
        self.target_shape = target_shape
        self.bbox = bbox
        self.target_face = target_face
        self.Cx = (bbox.XMax + bbox.XMin) / 2.0
        self.Cy = (bbox.YMax + bbox.YMin) / 2.0
        self.Cz = (bbox.ZMax + bbox.ZMin) / 2.0
        self.max_dim = max(bbox.XMax - bbox.XMin, bbox.YMax - bbox.YMin, bbox.ZMax - bbox.ZMin)
        self.R = max(bbox.XMax - bbox.XMin, bbox.YMax - bbox.YMin) / 2.0

    def setup_bounds(self, border_size, offset_x, offset_y): raise NotImplementedError
    def get_mapping(self, u, v): raise NotImplementedError

    def get_extrude_vector(self, norm, extrude_depth, z_height):
        return -norm * (extrude_depth + 2.0)

    def get_clipping_shape(self, border_size): return None
    def is_tile_valid(self, test_pts, inclusion_threshold): return True
    def get_base_pos(self, pos, norm): return pos + norm * 1.0
    def is_valid_uv(self, u, v, u_min, u_max, v_min, v_max): return True

    def setup_grid(self, dx, dy, u_min, u_max, v_min, v_max, is_staggered):
        odd_y_offset = dy / 2.0 if is_staggered else 0.0
        target_cols = max(2, int((u_max - u_min) / dx) + 2)
        rows = max(2, int((v_max - v_min) / dy) + 2)
        return target_cols, rows, -1, target_cols, dx, dy, odd_y_offset


# --- PLANAR STRATEGIES ---
class PlanarStrategy(BaseMappingStrategy):
    def setup_bounds(self, border_size, offset_x, offset_y):
        return self.bbox.XMin, self.bbox.XMax, self.bbox.YMin, self.bbox.YMax, offset_x, offset_y

    def get_mapping(self, u, v):
        return App.Vector(u, v, self.bbox.ZMin - 1.0), App.Vector(0, 0, 1), App.Vector(1, 0, 0), App.Vector(0, 1, 0)

    def get_base_pos(self, pos, norm): return pos
    def get_extrude_vector(self, norm, extrude_depth, z_height): return App.Vector(0, 0, z_height)

    def get_clipping_shape(self, border_size):
        base_face = None
        if self.target_shape.ShapeType in ["Face", "Wire"]: base_face = self.target_shape
        else:
            z_mid = (self.bbox.ZMax + self.bbox.ZMin) / 2.0
            plane = Part.makePlane((self.bbox.XMax - self.bbox.XMin) + 200, (self.bbox.YMax - self.bbox.YMin) + 200,
                                   App.Vector(self.bbox.XMin - 100, self.bbox.YMin - 100, z_mid), App.Vector(0,0,1))
            cross_section = self.target_shape.section(plane)
            if cross_section.Edges:
                wires = DraftGeomUtils.findWires(cross_section.Edges)
                closed_wires = [w for w in wires if w.isClosed()]
                if closed_wires:
                    closed_wires.sort(key=lambda w: w.Length, reverse=True)
                    base_face = Part.Face(closed_wires[0])
        
        if not base_face: return None
        try:
            offset_shape = base_face
            if border_size > 0.0:
                offset_shape = base_face.makeOffset2D(-border_size)
                if isinstance(offset_shape, list) and offset_shape: offset_shape = offset_shape[0]
                if offset_shape and offset_shape.ShapeType == "Wire": offset_shape = Part.Face(offset_shape)
            
            if offset_shape and not offset_shape.isNull():
                current_z = offset_shape.BoundBox.ZMin
                offset_shape.translate(App.Vector(0, 0, self.bbox.ZMin - 1.0 - current_z))
                return offset_shape.extrude(App.Vector(0, 0, self.bbox.ZMax + 2.0 - (self.bbox.ZMin - 1.0)))
        except Exception: pass
        return None

    def is_tile_valid(self, test_pts, inclusion_threshold):
        if inclusion_threshold <= 0.0: return True
        def is_inside(px, py):
            line = Part.makeLine(App.Vector(px, py, self.bbox.ZMin - 1.0), App.Vector(px, py, self.bbox.ZMax + 1.0))
            return line.distToShape(self.target_shape)[0] <= 1e-4

        pts_to_check = test_pts[:-1] if (len(test_pts) > 1 and test_pts[0].isEqual(test_pts[-1], 1e-5)) else test_pts
        if not pts_to_check: return False
        if inclusion_threshold >= 99.9: return all(is_inside(pt.x, pt.y) for pt in pts_to_check)
        
        inside_count = sum(1 for p in pts_to_check if is_inside(p.x, p.y))
        return (inside_count / len(pts_to_check)) >= (inclusion_threshold / 100.0)


class ProjectedPlanarStrategy(PlanarStrategy):
    def get_mapping(self, u, v):
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

        norm = calculate_projected_normal(self.target_shape, pos, App.Vector(0,0,1), hit_shape)
        tan_u = App.Vector(0,1,0).cross(norm)
        if tan_u.Length < 1e-4: tan_u = App.Vector(1, 0, 0)
        tan_u.normalize()
        tan_v = norm.cross(tan_u).normalize()
        return pos, norm, tan_u, tan_v
        
    def get_extrude_vector(self, norm, extrude_depth, z_height):
        return -norm * (extrude_depth + 2.0)


# --- WRAP STRATEGIES ---
class WrapStrategy(BaseMappingStrategy):
    def get_clipping_shape(self, border_size):
        safe_size = self.max_dim * 2.0 + 100.0
        if border_size > 0.0:
            z_min = self.bbox.ZMin + border_size
            z_max = self.bbox.ZMax - border_size
            if z_max > z_min:
                safe_box = Part.makeBox(safe_size, safe_size, z_max - z_min)
                safe_box.translate(App.Vector(self.Cx - safe_size/2.0, self.Cy - safe_size/2.0, z_min))
                return safe_box
        return None

    def is_tile_valid(self, test_pts, inclusion_threshold):
        if inclusion_threshold <= 0.0: return True
        z_min_orig, z_max_orig = self.bbox.ZMin, self.bbox.ZMax
        pts_to_check = test_pts[:-1] if (len(test_pts) > 1 and test_pts[0].isEqual(test_pts[-1], 1e-5)) else test_pts
        if not pts_to_check: return False
        if inclusion_threshold >= 99.9:
            return all(z_min_orig - 1e-4 <= pt.z <= z_max_orig + 1e-4 for pt in pts_to_check)
        inside_count = sum(1 for p in pts_to_check if (z_min_orig - 1e-4 <= p.z <= z_max_orig + 1e-4))
        return (inside_count / len(pts_to_check)) >= (inclusion_threshold / 100.0)

    def setup_grid(self, dx, dy, u_min, u_max, v_min, v_max, is_staggered):
        circumference = 2 * math.pi * self.R
        target_cols = max(2, round(circumference / dx))
        if is_staggered and target_cols % 2 != 0: target_cols += 1
        dx = circumference / target_cols
        odd_y_offset = dy / 2.0 if is_staggered else 0.0
        rows = max(2, int((v_max - v_min) / dy) + 2)
        return target_cols, rows, 0, target_cols, dx, dy, odd_y_offset


class CylindricalStrategy(WrapStrategy):
    def setup_bounds(self, border_size, offset_x, offset_y):
        return 0.0, 2 * math.pi * self.R, self.bbox.ZMin, self.bbox.ZMax, offset_x, offset_y

    def get_mapping(self, u, v):
        theta = u / self.R
        pos = App.Vector(self.Cx + self.R * math.cos(theta), self.Cy + self.R * math.sin(theta), v)
        norm = App.Vector(math.cos(theta), math.sin(theta), 0)
        return pos, norm, App.Vector(-math.sin(theta), math.cos(theta), 0), App.Vector(0, 0, 1)

class ProjectedCylindricalStrategy(WrapStrategy):
    def setup_bounds(self, border_size, offset_x, offset_y):
        return 0.0, 2 * math.pi * self.R, self.bbox.ZMin, self.bbox.ZMax, offset_x, offset_y

    def get_mapping(self, u, v):
        theta = u / self.R
        p_center = App.Vector(self.Cx, self.Cy, v)
        ray_dir = App.Vector(math.cos(theta), math.sin(theta), 0)
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes, key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else:
            pos = App.Vector(self.Cx + self.R * math.cos(theta), self.Cy + self.R * math.sin(theta), v)

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir, hit_shape)
        tan_u = App.Vector(0,0,1).cross(norm)
        if tan_u.Length < 1e-4: tan_u = App.Vector(-math.sin(theta), math.cos(theta), 0)
        tan_u.normalize()
        return pos, norm, tan_u, norm.cross(tan_u).normalize()

class SphericalStrategy(WrapStrategy):
    def setup_bounds(self, border_size, offset_x, offset_y):
        self.R = self.max_dim / 2.0
        return 0.0, 2 * math.pi * self.R, 0.0, math.pi * self.R, offset_x, offset_y

    def get_mapping(self, u, v):
        theta, phi = u / self.R, v / self.R
        pos = App.Vector(self.Cx + self.R*math.cos(theta)*math.sin(phi), self.Cy + self.R*math.sin(theta)*math.sin(phi), self.Cz + self.R*math.cos(phi))
        norm = App.Vector(math.cos(theta)*math.sin(phi), math.sin(theta)*math.sin(phi), math.cos(phi)).normalize()
        tan_u = App.Vector(-math.sin(theta), math.cos(theta), 0)
        if tan_u.Length < 1e-4: tan_u = App.Vector(1, 0, 0)
        tan_u.normalize()
        return pos, norm, tan_u, norm.cross(tan_u).normalize()

    def is_valid_uv(self, u, v, u_min, u_max, v_min, v_max): return v_min <= v <= v_max

class ProjectedSphericalStrategy(SphericalStrategy):
    def get_mapping(self, u, v):
        theta, phi = u / self.R, v / self.R
        p_center = App.Vector(self.Cx, self.Cy, self.Cz)
        ray_dir = App.Vector(math.cos(theta)*math.sin(phi), math.sin(theta)*math.sin(phi), math.cos(phi)).normalize()
        ray = Part.makeLine(p_center, p_center + ray_dir * (self.max_dim * 2.0))
        intersections = self.target_shape.common(ray)

        hit_shape = False
        if intersections.Vertexes:
            pos = max(intersections.Vertexes, key=lambda vtx: (vtx.Point - p_center).Length).Point
            hit_shape = True
        else: pos = p_center + ray_dir * self.R

        norm = calculate_projected_normal(self.target_shape, pos, ray_dir, hit_shape)
        tan_u = App.Vector(0,0,1).cross(norm)
        if tan_u.Length < 1e-4: tan_u = App.Vector(1, 0, 0)
        tan_u.normalize()
        return pos, norm, tan_u, norm.cross(tan_u).normalize()


class RadialStrategy(WrapStrategy):
    def setup_bounds(self, border_size, offset_x, offset_y):
        return 0.0, 2 * math.pi * self.R, 0.0, self.R, offset_x, offset_y

    def get_mapping(self, u, v):
        theta = u / self.R
        pos = App.Vector(self.Cx + v * math.cos(theta), self.Cy + v * math.sin(theta), self.bbox.ZMax)
        return pos, App.Vector(0, 0, 1), App.Vector(-math.sin(theta), math.cos(theta), 0), App.Vector(math.cos(theta), math.sin(theta), 0)

    def get_base_pos(self, pos, norm): return pos
    def get_extrude_vector(self, norm, extrude_depth, z_height): return App.Vector(0, 0, z_height)
    def is_valid_uv(self, u, v, u_min, u_max, v_min, v_max): return v <= v_max


class SurfaceUVStrategy(BaseMappingStrategy):
    def setup_bounds(self, border_size, offset_x, offset_y):
        if not self.target_face: return 0, 0, 0, 0, offset_x, offset_y
        u_min, u_max, v_min, v_max = self.target_face.ParameterRange

        if border_size > 0.0:
            mid_u, mid_v = (u_min + u_max) / 2.0, (v_min + v_max) / 2.0
            len_u = (self.target_face.valueAt(u_max, mid_v) - self.target_face.valueAt(u_min, mid_v)).Length
            len_v = (self.target_face.valueAt(mid_u, v_max) - self.target_face.valueAt(mid_u, v_min)).Length
            scale_u = (u_max - u_min) / len_u if len_u > 1e-4 else 0
            scale_v = (v_max - v_min) / len_v if len_v > 1e-4 else 0
            u_min += border_size * scale_u; u_max -= border_size * scale_u
            v_min += border_size * scale_v; v_max -= border_size * scale_v

        ur, vr = (u_max - u_min), (v_max - v_min)
        offset_x = (offset_x / 100.0) * ur if ur > 0 else offset_x
        offset_y = (offset_y / 100.0) * vr if vr > 0 else offset_y
        return u_min, u_max, v_min, v_max, offset_x, offset_y

    def get_mapping(self, u, v):
        pos = self.target_face.valueAt(u, v)
        norm = self.target_face.normalAt(u, v).normalize()
        tan_u = App.Vector(0,0,1).cross(norm)
        if tan_u.Length < 1e-4: tan_u = App.Vector(1, 0, 0)
        tan_u.normalize()
        return pos, norm, tan_u, norm.cross(tan_u).normalize()

    def is_valid_uv(self, u, v, u_min, u_max, v_min, v_max):
        return (u_min <= u <= u_max) and (v_min <= v <= v_max)

    def setup_grid(self, dx, dy, u_min, u_max, v_min, v_max, is_staggered):
        dx = (dx / self.max_dim) * (u_max - u_min)
        dy = (dy / self.max_dim) * (v_max - v_min)
        odd_y_offset = dy / 2.0 if is_staggered else 0.0
        target_cols = max(2, int((u_max - u_min) / dx) + 2)
        rows = max(2, int((v_max - v_min) / dy) + 2)
        return target_cols, rows, -1, target_cols, dx, dy, odd_y_offset


class MappingFactory:
    @staticmethod
    def create(mapping_type, target_shape, target_face=None):
        strategies = {
            "Planar": PlanarStrategy, "Projected Planar": ProjectedPlanarStrategy,
            "Cylindrical": CylindricalStrategy, "Projected Cylindrical": ProjectedCylindricalStrategy,
            "Spherical": SphericalStrategy, "Projected Spherical": ProjectedSphericalStrategy,
            "Radial": RadialStrategy, "Surface UV": SurfaceUVStrategy
        }
        strategy_class = strategies.get(mapping_type, PlanarStrategy)
        if mapping_type == "Surface UV" and not target_face:
            faces = target_shape.Faces
            if faces: target_face = max(faces, key=lambda f: f.Area)
            
        return strategy_class(target_shape, target_shape.BoundBox, target_face)
