"""Task Panel UI binding for lattice pattern generation."""

import FreeCAD as App

from freecad.latticegen import workflow
from freecad.latticegen.config import LatticeConfig
from freecad.latticegen.constants import PREVIEW_TRANSPARENCY
from freecad.latticegen.core import generate_lattice_shape
from freecad.latticegen.resources import Resources
from freecad.latticegen.strategies import MappingFactory
from freecad.latticegen.tiles import TileFactory
from freecad.latticegen.ui.base_panel import BaseTaskPanel


class PatternTaskPanel(BaseTaskPanel):
    """Task panel for setting pattern parameters and generating geometry."""

    def __init__(self, target_obj, target_face=None):
        self.target_obj = target_obj
        self.target_face = target_face

        ui_path = Resources._pkg.joinpath("ui/lattice_panel.ui")
        super().__init__(str(ui_path), has_preview=True)

    def setup_ui(self):
        self.form.pattern_combo.clear()
        self.form.pattern_combo.addItems(TileFactory.get_available_patterns())
        
        self.form.mapping_combo.clear()
        self.form.mapping_combo.addItems(MappingFactory.get_available_mappings())

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
        self.form.operation_combo.currentIndexChanged.connect(
            self.queue_preview)

        if hasattr(self.form, "preview_toggle_check"):
            self.form.preview_toggle_check.stateChanged.connect(
                self.queue_preview)

    def get_config_from_ui(self) -> LatticeConfig:
        """Hydrates a configuration object from current UI widget states."""
        mode = "cut" if self.form.operation_combo.currentIndex(
        ) == 0 else "common"
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
        """Passes the hydrated config and target info to the workflow logic module."""
        config = self.get_config_from_ui()
        workflow.inject_lattice_into_document(self.target_obj, self.target_face,
                                              config)

    def reject(self):
        super().reject()
