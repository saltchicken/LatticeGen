"""Document manipulation and workflow logic for LatticeGen."""

import FreeCAD as App

from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.feature import LatticeToolFeature, ViewProviderLatticeTool
from freecad.latticegen.utils import get_active_body


def inject_lattice_into_document(target_obj, target_face, config: LatticeConfig, target_face_name: str = ""):
    """Instantiates the parametric lattice feature into the document."""
    active_body = get_active_body(target_obj)
    
    op_suffix = "LatticeCut" if config.operation_mode == "cut" else "LatticePanel"
    feat_name = f"{target_obj.Name}_{op_suffix}"

    # 1. Create the unified Parametric Lattice Feature
    if active_body:
        feat_obj = App.ActiveDocument.addObject("PartDesign::FeaturePython", feat_name)
        active_body.addObject(feat_obj)
        active_body.Tip = feat_obj
    else:
        feat_obj = App.ActiveDocument.addObject("Part::FeaturePython", feat_name)

    LatticeToolFeature(feat_obj)
    if App.GuiUp:
        ViewProviderLatticeTool(feat_obj.ViewObject)

    # 2. Map the UI config directly to the new parametric node
    feat_obj.Target = target_obj
    feat_obj.TargetFace = target_face_name
    feat_obj.OperationMode = config.operation_mode
    feat_obj.Pattern = config.pattern
    feat_obj.Mapping = config.mapping
    feat_obj.Axis = config.axis
    feat_obj.TileRadius = config.tile_radius
    feat_obj.Gap = config.gap
    feat_obj.ExtrudeDepth = config.extrude_depth
    feat_obj.FilletRadius = config.fillet_radius
    feat_obj.BorderSize = config.border_size
    feat_obj.OffsetX = config.offset_x
    feat_obj.OffsetY = config.offset_y
    feat_obj.InclusionThreshold = config.inclusion_threshold

    # Hide the original target object to simulate PartDesign's "Tip" visual flow
    target_obj.Visibility = False
    
    # Inherit color from the target object
    if feat_obj.ViewObject and target_obj.ViewObject:
        feat_obj.ViewObject.ShapeColor = getattr(target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8))

    # 3. For Part Workbench, optionally place it in a group for cleanliness
    if not active_body:
        group_name = "Generated_Lattices"
        group = App.ActiveDocument.getObject(group_name) or App.ActiveDocument.addObject("App::DocumentObjectGroup", group_name)
        group.Label = "Generated Lattices"
        group.addObject(feat_obj)

    App.ActiveDocument.recompute()
