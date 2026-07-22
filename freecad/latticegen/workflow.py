"""Document manipulation and workflow logic for LatticeGen."""

import FreeCAD as App
from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.utils import get_active_body
from freecad.latticegen.core import generate_lattice_shape

def inject_lattice_into_document(target_obj, target_face, config: LatticeConfig):
    """Handles all FreeCAD tree operations (PartDesign Body vs Part Root)."""
    active_body = get_active_body(target_obj)
    is_cut = config.operation_mode == "cut"

    # PartDesign Workflow
    if active_body:
        tool_shape = generate_lattice_shape(target_obj, config, target_face, return_tool=True)
        if tool_shape is None:
            return

        tool_obj = App.ActiveDocument.addObject("Part::Feature", f"{target_obj.Name}_LatticeTools")
        tool_obj.Shape = tool_shape
        tool_obj.Visibility = False

        operation_name = "LatticeCut" if is_cut else "LatticePanel"
        bool_feat = active_body.newObject("PartDesign::Boolean", f"{target_obj.Name}_{operation_name}")
        bool_feat.Type = 1 if is_cut else 2
        bool_feat.Group = [tool_obj]

        target_obj.Visibility = False
        if bool_feat.ViewObject and target_obj.ViewObject:
            bool_feat.ViewObject.ShapeColor = getattr(target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8))

        App.ActiveDocument.recompute()
        
    # Part Workbench Workflow (No active body)
    else:
        shape = generate_lattice_shape(target_obj, config, target_face, return_tool=False)
        if shape is None:
            return

        operation_name = "Lattice" if is_cut else "Panels"
        final_obj = App.ActiveDocument.addObject("Part::Feature", f"{target_obj.Name}_{operation_name}")
        final_obj.Shape = shape

        target_obj.Visibility = False
        if final_obj.ViewObject and target_obj.ViewObject:
            final_obj.ViewObject.ShapeColor = getattr(target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8))

        group_name = "Generated_Lattices"
        group = App.ActiveDocument.getObject(group_name) or App.ActiveDocument.addObject(
            "App::DocumentObjectGroup", group_name
        )
        group.Label = "Generated Lattices"
        group.addObject(final_obj)
