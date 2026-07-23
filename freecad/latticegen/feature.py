"""Parametric FeaturePython definition for LatticeGen."""

import FreeCAD as App
import Part

from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.core import generate_lattice_shape
from freecad.latticegen.resources import Resources
from freecad.latticegen.strategies import MappingFactory
from freecad.latticegen.strategies.base import BaseMappingStrategy
from freecad.latticegen.tiles import BaseTile, TileFactory


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

        # Custom specialized parameters
        obj.addProperty("App::PropertyInteger", "VoronoiSeed", "Voronoi", "Seed for randomness").VoronoiSeed = 12345
        obj.addProperty("App::PropertyFloat", "VoronoiVariance", "Voronoi", "Variance for randomness").VoronoiVariance = 0.5
        obj.addProperty("App::PropertyInteger", "VoronoiRelaxation", "Voronoi", "Lloyd's relaxation steps").VoronoiRelaxation = 0
        obj.addProperty("App::PropertyFloat", "VoronoiGapVariance", "Voronoi", "Variance in strut thickness").VoronoiGapVariance = 0.0
        obj.addProperty("App::PropertyEnumeration", "VoronoiBaseGrid", "Voronoi", "Starting topology")
        obj.VoronoiBaseGrid = ["Hexagon", "Square"]
        obj.addProperty("App::PropertyFloat", "VoronoiStretchU", "Voronoi", "Stretch along U axis").VoronoiStretchU = 1.0
        obj.addProperty("App::PropertyFloat", "VoronoiStretchV", "Voronoi", "Stretch along V axis").VoronoiStretchV = 1.0

        # Initialize visibility state
        self.update_property_visibility(obj)

    def onChanged(self, obj, prop):
        """Called automatically by FreeCAD when a property changes."""
        if prop in ["Mapping", "Pattern"]:
            self.update_property_visibility(obj)

    def update_property_visibility(self, obj):
        """Dynamically hides/shows properties based on Tile and Strategy metadata."""
        current_pattern = getattr(obj, "Pattern", "")
        current_mapping = getattr(obj, "Mapping", "")

        tile_cls = BaseTile._registry.get(current_pattern, BaseTile)
        mapping_cls = BaseMappingStrategy._registry.get(current_mapping, BaseMappingStrategy)
        
        base_props = [
            "TileRadius", "Gap", "ExtrudeDepth", "FilletRadius", 
            "BorderSize", "OffsetX", "OffsetY", "InclusionThreshold"
        ]

        # Iterate through all properties
        for prop in obj.PropertiesList:
            if prop in ["Target", "TargetFace", "OperationMode", "Pattern", "Mapping", "Axis"]:
                continue

            if prop in base_props:
                is_hidden = (prop in mapping_cls.unsupported_parameters) or \
                            (prop in tile_cls.unsupported_parameters)
                obj.setEditorMode(prop, 2 if is_hidden else 0)
            else:
                # Treat as custom parameter. Show only if tile explicitly requests it.
                is_visible = prop in tile_cls.custom_parameters
                obj.setEditorMode(prop, 0 if is_visible else 2)

    def execute(self, obj):
        try:
            if not obj.Target or not hasattr(obj.Target, "Shape"):
                return

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
                operation_mode=obj.OperationMode,
                voronoi_seed=get_val("VoronoiSeed") if hasattr(obj, "VoronoiSeed") else 12345,
                voronoi_variance=get_val("VoronoiVariance") if hasattr(obj, "VoronoiVariance") else 0.5,
                voronoi_relaxation=get_val("VoronoiRelaxation") if hasattr(obj, "VoronoiRelaxation") else 0,
                voronoi_gap_variance=get_val("VoronoiGapVariance") if hasattr(obj, "VoronoiGapVariance") else 0.0,
                voronoi_base_grid=get_val("VoronoiBaseGrid") if hasattr(obj, "VoronoiBaseGrid") else "Hexagon",
                voronoi_stretch_u=get_val("VoronoiStretchU") if hasattr(obj, "VoronoiStretchU") else 1.0,
                voronoi_stretch_v=get_val("VoronoiStretchV") if hasattr(obj, "VoronoiStretchV") else 1.0
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
        return None

    def __setstate__(self, state):
        return None

    def getIcon(self):
        return Resources.icon("LatticeGen.svg")

    def claimChildren(self):
        return []

    def setEdit(self, vobj, mode=0):
        return False

    def doubleClicked(self, vobj):
        return False
