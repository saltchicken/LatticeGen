"""Utility functions for PartDesign body lookup and vector calculations."""

import FreeCAD as App
import FreeCADGui as Gui
import Part

from freecad.latticegen.constants import NORMAL_DOT_MIN
from freecad.latticegen.constants import RAY_OFFSET
from freecad.latticegen.constants import TOL_RELAXED
from freecad.latticegen.constants import TOL_STRICT


def get_active_body(base_obj=None):
    """Finds the active PartDesign Body, falling back to the base object's parent."""
    active_body = None

    if Gui.ActiveDocument:
        active_body = Gui.ActiveDocument.ActiveView.getActiveObject("pdbody")

    if not active_body and base_obj:
        for parent in base_obj.InList:
            if parent.isDerivedFrom("PartDesign::Body"):
                active_body = parent
                break

    if not active_body:
        App.Console.PrintWarning(
            "Warning: No Active Body found. Placing objects in root.\n")

    return active_body


def calculate_projected_normal(target_shape,
                               pos: App.Vector,
                               ray_dir: App.Vector,
                               hit_shape: bool = True) -> App.Vector:
    """Calculates surface normal at a given point using ray projection."""
    if not hit_shape:
        return ray_dir

    best_norm = None
    max_dot = -1.0

    # Attempt to extract the true face normal. This fixes issues where pos is 
    # exactly on a sharp boundary edge (like the end caps of a cylinder), avoiding
    # distance-field snapping artifacts.
    if hasattr(target_shape, "Faces"):
        for face in target_shape.Faces:
            try:
                dist, _, _ = face.distToShape(Part.Vertex(pos))
                if dist <= TOL_RELAXED:
                    uv = face.Surface.parameter(pos)
                    norm = face.normalAt(uv[0], uv[1])
                    if norm.Length > TOL_STRICT:
                        norm.normalize()
                        # If on an edge, prefer the face pointing towards the ray (e.g., side over cap)
                        d = norm.dot(ray_dir)
                        if d > max_dot:
                            max_dot = d
                            best_norm = norm
            except Exception:
                continue

    if best_norm is not None and max_dot > NORMAL_DOT_MIN:
        return best_norm

    # Fallback to distance field gradient if face math fails
    test_pt = pos + ray_dir * RAY_OFFSET
    dist, pts, _ = target_shape.distToShape(Part.Vertex(test_pt))

    if pts and dist > TOL_STRICT:
        norm = test_pt - pts[0][0]
        if norm.Length > TOL_STRICT:
            norm.normalize()
            if norm.dot(ray_dir) > NORMAL_DOT_MIN:
                return norm

    return ray_dir
