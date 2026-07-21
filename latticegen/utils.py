"""Utility functions for PartDesign body lookup and vector calculations."""

import FreeCAD as App
import FreeCADGui as Gui
import Part

from latticegen.constants import NORMAL_DOT_MIN, RAY_OFFSET, TOL_STRICT


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
        App.Console.PrintWarning("Warning: No Active Body found. Placing objects in root.\n")

    return active_body


def calculate_projected_normal(target_shape, pos: App.Vector, ray_dir: App.Vector, hit_shape: bool = True) -> App.Vector:
    """Calculates surface normal at a given point using ray projection."""
    if not hit_shape:
        return ray_dir

    test_pt = pos + ray_dir * RAY_OFFSET
    dist, pts, _ = target_shape.distToShape(Part.Vertex(test_pt))

    if pts and dist > TOL_STRICT:
        norm = test_pt - pts[0][0]
        if norm.Length > TOL_STRICT:
            norm.normalize()
            if norm.dot(ray_dir) > NORMAL_DOT_MIN:
                return norm

    return ray_dir
