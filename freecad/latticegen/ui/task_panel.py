"""Task Panel UI binding for lattice pattern generation."""

import FreeCAD as App
from PySide6 import QtWidgets

from freecad.latticegen import workflow
from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.constants import PREVIEW_TRANSPARENCY
from freecad.latticegen.core import generate_lattice_shape
from freecad.latticegen.resources import Resources
from freecad.latticegen.strategies import MappingFactory
from freecad.latticegen.strategies.base import BaseMappingStrategy
from freecad.latticegen.tiles import BaseTile, TileFactory
from freecad.latticegen.ui.base_panel import BaseTaskPanel


class PatternTaskPanel(BaseTaskPanel):
    """Task panel for setting pattern parameters and generating geometry."""

    def __init__(self, target_obj, target_face=None, target_face_name=""):
        self.target_obj = target_obj
        self.target_face = target_face
        self.target_face_name = target_face_name

        ui_path = Resources._pkg.joinpath("ui/lattice_panel.ui")
        super().__init__(str(ui_path), has_preview=True)

    def setup_ui(self):
        self.form.pattern_combo.clear()
        self.form.pattern_combo.addItems(TileFactory.get_available_patterns())

        self.form.mapping_combo.clear()
        self.form.mapping_combo.addItems(MappingFactory.get_available_mappings())

        # Wire up visibility updates
        self.form.pattern_combo.currentIndexChanged.connect(self.update_ui_visibility)
        self.form.mapping_combo.currentIndexChanged.connect(self.update_ui_visibility)

        self.form.pattern_combo.currentIndexChanged.connect(self.queue_preview)
        self.form.mapping_combo.currentIndexChanged.connect(self.queue_preview)
        self.form.axis_combo.currentIndexChanged.connect(self.queue_preview)
        self.form.radius_spin.valueChanged.connect(self.queue_preview)
        self.form.gap_spin.valueChanged.connect(self.queue_preview)
        self.form.depth_spin.valueChanged.connect(self.queue_preview)
        self.form.fillet_spin.valueChanged.connect(self.queue_preview)
        self.form.border_spin.valueChanged.connect(self.queue_preview)
        self.form.threshold_spin.valueChanged.connect(self.queue_preview)
        self.form.offset_x_spin.valueChanged.connect(self.queue_preview)
        self.form.offset_y_spin.valueChanged.connect(self.queue_preview)
        self.form.operation_combo.currentIndexChanged.connect(self.queue_preview)
        
        # Connect specific parameters if they exist in the UI file
        if hasattr(self.form, "voronoi_seed_spin"):
            self.form.voronoi_seed_spin.valueChanged.connect(self.queue_preview)
        if hasattr(self.form, "voronoi_variance_spin"):
            self.form.voronoi_variance_spin.valueChanged.connect(self.queue_preview)
        if hasattr(self.form, "voronoi_relax_spin"):
            self.form.voronoi_relax_spin.valueChanged.connect(self.queue_preview)
        if hasattr(self.form, "voronoi_gapvar_spin"):
            self.form.voronoi_gapvar_spin.valueChanged.connect(self.queue_preview)
        if hasattr(self.form, "voronoi_grid_combo"):
            self.form.voronoi_grid_combo.currentIndexChanged.connect(self.queue_preview)
        if hasattr(self.form, "voronoi_stretch_u_spin"):
            self.form.voronoi_stretch_u_spin.valueChanged.connect(self.queue_preview)
        if hasattr(self.form, "voronoi_stretch_v_spin"):
            self.form.voronoi_stretch_v_spin.valueChanged.connect(self.queue_preview)

        if hasattr(self.form, "preview_toggle_check"):
            self.form.preview_toggle_check.stateChanged.connect(self.queue_preview)

        # --- Auto-update wiring ---
        if hasattr(self.form, "auto_update_check"):
            self.form.auto_update_check.stateChanged.connect(self._on_auto_update_changed)
            self.form.refresh_button.setEnabled(not self.form.auto_update_check.isChecked())

        if hasattr(self.form, "refresh_button"):
            self.form.refresh_button.clicked.connect(self.force_preview)
            
        # Map FreeCAD property names to Qt Widget objects
        self.prop_to_widget = {
            "TileRadius": getattr(self.form, "radius_spin", None),
            "Gap": getattr(self.form, "gap_spin", None),
            "ExtrudeDepth": getattr(self.form, "depth_spin", None),
            "FilletRadius": getattr(self.form, "fillet_spin", None),
            "BorderSize": getattr(self.form, "border_spin", None),
            "InclusionThreshold": getattr(self.form, "threshold_spin", None),
            "OffsetX": getattr(self.form, "offset_x_spin", None),
            "OffsetY": getattr(self.form, "offset_y_spin", None),
            "VoronoiSeed": getattr(self.form, "voronoi_seed_spin", None),
            "VoronoiVariance": getattr(self.form, "voronoi_variance_spin", None),
            "VoronoiRelaxation": getattr(self.form, "voronoi_relax_spin", None),
            "VoronoiGapVariance": getattr(self.form, "voronoi_gapvar_spin", None),
            "VoronoiBaseGrid": getattr(self.form, "voronoi_grid_combo", None),
            "VoronoiStretchU": getattr(self.form, "voronoi_stretch_u_spin", None),
            "VoronoiStretchV": getattr(self.form, "voronoi_stretch_v_spin", None),
        }
        
        # Initialize visibility state
        self.update_ui_visibility()

    def update_ui_visibility(self):
        """Rule engine to determine which fields are visible."""
        tile_cls = BaseTile._registry.get(self.form.pattern_combo.currentText(), BaseTile)
        mapping_cls = BaseMappingStrategy._registry.get(self.form.mapping_combo.currentText(), BaseMappingStrategy)
        
        base_props = [
            "TileRadius", "Gap", "ExtrudeDepth", "FilletRadius", 
            "BorderSize", "OffsetX", "OffsetY", "InclusionThreshold"
        ]

        for prop_name, widget in self.prop_to_widget.items():
            if not widget:
                continue
                
            if prop_name in base_props:
                is_hidden = (prop_name in mapping_cls.unsupported_parameters) or \
                            (prop_name in tile_cls.unsupported_parameters)
                self._set_field_visible(widget, not is_hidden)
            else:
                # Custom parameter
                is_visible = (prop_name in tile_cls.custom_parameters)
                self._set_field_visible(widget, is_visible)

    def _set_field_visible(self, widget, is_visible):
        """Hides the widget and its accompanying QLabel in a QFormLayout."""
        widget.setVisible(is_visible)
        
        # FreeCAD UI forms are typically nested. Look into layout index 1 based on UI XML
        form_layout = self.form.layout().itemAt(1).layout()
        if isinstance(form_layout, QtWidgets.QFormLayout):
            label = form_layout.labelForField(widget)
            if label:
                label.setVisible(is_visible)

    def _on_auto_update_changed(self, state):
        is_auto = self.form.auto_update_check.isChecked()
        self.form.refresh_button.setEnabled(not is_auto)
        if is_auto:
            self.force_preview()

    def queue_preview(self, *args):
        if hasattr(self.form, "auto_update_check") and not self.form.auto_update_check.isChecked():
            return
        super().queue_preview(*args)

    def force_preview(self, *args):
        super().queue_preview(*args)

    def get_config_from_ui(self) -> LatticeConfig:
        mode = "cut" if self.form.operation_combo.currentIndex() == 0 else "common"
        return LatticeConfig(
            pattern=self.form.pattern_combo.currentText(),
            mapping=self.form.mapping_combo.currentText(),
            axis=self.form.axis_combo.currentText(),
            tile_radius=self.form.radius_spin.value(),
            gap=self.form.gap_spin.value(),
            extrude_depth=self.form.depth_spin.value(),
            fillet_radius=self.form.fillet_spin.value(),
            border_size=self.form.border_spin.value(),
            inclusion_threshold=self.form.threshold_spin.value(),
            offset_x=self.form.offset_x_spin.value(),
            offset_y=self.form.offset_y_spin.value(),
            operation_mode=mode,
            voronoi_seed=self.form.voronoi_seed_spin.value() if hasattr(self.form, "voronoi_seed_spin") else 12345,
            voronoi_variance=self.form.voronoi_variance_spin.value() if hasattr(self.form, "voronoi_variance_spin") else 0.5,
            voronoi_relaxation=self.form.voronoi_relax_spin.value() if hasattr(self.form, "voronoi_relax_spin") else 0,
            voronoi_gap_variance=self.form.voronoi_gapvar_spin.value() if hasattr(self.form, "voronoi_gapvar_spin") else 0.0,
            voronoi_base_grid=self.form.voronoi_grid_combo.currentText() if hasattr(self.form, "voronoi_grid_combo") else "Hexagon",
            voronoi_stretch_u=self.form.voronoi_stretch_u_spin.value() if hasattr(self.form, "voronoi_stretch_u_spin") else 1.0,
            voronoi_stretch_v=self.form.voronoi_stretch_v_spin.value() if hasattr(self.form, "voronoi_stretch_v_spin") else 1.0
        )

    def get_shape(self, config: LatticeConfig, return_tool: bool = True):
        return generate_lattice_shape(
            target_obj=self.target_obj,
            config=config,
            target_face=self.target_face,
            return_tool=return_tool,
        )

    def calculate_preview(self):
        config = self.get_config_from_ui()
        show_final = (hasattr(self.form, "preview_toggle_check") and
                      self.form.preview_toggle_check.isChecked())

        if show_final:
            self.target_obj.Visibility = False
            if self.has_preview and hasattr(
                    self, "preview_obj") and self.preview_obj.ViewObject:
                self.preview_obj.ViewObject.ShapeColor = getattr(
                    self.target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8))
                self.preview_obj.ViewObject.Transparency = getattr(
                    self.target_obj.ViewObject, "Transparency", 0)
            return self.get_shape(config, return_tool=False)
        else:
            self.target_obj.Visibility = True
            if self.has_preview and hasattr(
                    self, "preview_obj") and self.preview_obj.ViewObject:
                self.preview_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
                self.preview_obj.ViewObject.Transparency = PREVIEW_TRANSPARENCY
            return self.get_shape(config, return_tool=True)

    def generate_final(self):
        config = self.get_config_from_ui()
        workflow.inject_lattice_into_document(self.target_obj, self.target_face,
                                              config, self.target_face_name)

    def reject(self):
        super().reject()
