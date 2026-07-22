"""Parametric FeaturePython definition for LatticeGen."""

import FreeCAD as App
import Part

from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.core import generate_lattice_shape
from freecad.latticegen.resources import Resources
from freecad.latticegen.strategies import MappingFactory
from freecad.latticegen.tiles import TileFactory


class LatticeToolFeature:
    """Parametric FeaturePython object that generates the final Lattice Boolean shape."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "LatticeToolFeature"
        self.setup_properties(obj)

    def setup_properties(self, obj):
        # Target Links
        obj.addProperty("App::PropertyLink", "Target", "Lattice", "Target solid object")
        obj.addProperty("App::PropertyString", "TargetFace", "Lattice", "Specific face subname (optional)")

        # Enumerations
        obj.addProperty("App::PropertyEnumeration", "OperationMode", "Lattice", "Boolean Operation")
        obj.OperationMode = ["cut", "common"]

        obj.addProperty("App::PropertyEnumeration", "Pattern", "Lattice", "Tile Pattern")
        obj.Pattern = TileFactory.get_available_patterns()

        obj.addProperty("App::PropertyEnumeration", "Mapping", "Lattice", "Mapping Strategy")
        obj.Mapping = MappingFactory.get_available_mappings()

        obj.addProperty("App::PropertyEnumeration", "Axis", "Lattice", "Projection Axis")
        obj.Axis = ["Z", "X", "Y"]

        # Dimensions
        obj.addProperty("App::PropertyLength", "TileRadius", "Parameters", "Radius of tiles").TileRadius = 8.0
        obj.addProperty("App::PropertyLength", "Gap", "Parameters", "Gap between tiles").Gap = 1.0
        obj.addProperty("App::PropertyLength", "ExtrudeDepth", "Parameters", "Extrusion depth").ExtrudeDepth = 5.0
        obj.addProperty("App::PropertyLength", "FilletRadius", "Parameters", "Corner fillet").FilletRadius = 0.0
        obj.addProperty("App::PropertyLength", "BorderSize", "Parameters", "Margin from borders").BorderSize = 0.0

        # Offsets & Thresholds
        obj.addProperty("App::PropertyDistance", "OffsetX", "Parameters", "X Offset").OffsetX = 0.0
        obj.addProperty("App::PropertyDistance", "OffsetY", "Parameters", "Y Offset").OffsetY = 0.0
        obj.addProperty("App::PropertyFloat", "InclusionThreshold", "Parameters", "Min visibility %").InclusionThreshold = 0.0

    def execute(self, obj):
        try:
            if not obj.Target or not hasattr(obj.Target, "Shape"):
                return

            # Helper to safely extract float values whether FreeCAD
            # returns a Unit Quantity or a raw float
            def get_val(prop_name):
                val = getattr(obj, prop_name)
                return val.Value if hasattr(val, 'Value') else val

            config = LatticeConfig(
                pattern=obj.Pattern,
                mapping=obj.Mapping,
                axis=obj.Axis,
                tile_radius=get_val("TileRadius"),
                gap=get_val("Gap"),
                extrude_depth=get_val("ExtrudeDepth"),
                fillet_radius=get_val("FilletRadius"),
                border_size=get_val("BorderSize"),
                inclusion_threshold=get_val("InclusionThreshold"),
                offset_x=get_val("OffsetX"),
                offset_y=get_val("OffsetY"),
                operation_mode=obj.OperationMode
            )

            target_face = None
            if obj.TargetFace:
                target_face = obj.Target.Shape.getElement(obj.TargetFace)

            final_shape = generate_lattice_shape(
                target_obj=obj.Target,
                config=config,
                target_face=target_face,
                return_tool=False
            )

            if final_shape and not final_shape.isNull():
                obj.Shape = final_shape
            else:
                App.Console.PrintWarning(f"{obj.Name}: Generated boolean shape is empty.\n")

        except Exception as e:
            # If anything breaks, print the exact error and line number to the FreeCAD console
            import traceback
            App.Console.PrintError(f"LatticeTool failed to execute: {e}\n{traceback.format_exc()}\n")


class ViewProviderLatticeTool:
    """ViewProvider for the LatticeToolFeature to handle UI and icons."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def __getstate__(self):
        """Called during save. Return None to prevent serializing C++ objects."""
        return None

    def __setstate__(self, state):
        """Called during document restore."""
        return None

    def getIcon(self):
        return Resources.icon("LatticeGen.svg")

    def claimChildren(self):
        return []

    def setEdit(self, vobj, mode=0):
        # Return False to tell FreeCAD we don't have a custom Task Panel to open.
        # Users will edit the parametric values via the Data property tab instead.
        return False

    def doubleClicked(self, vobj):
        # Intercept the double-click so FreeCAD doesn't look for getEditDialog()
        return False
