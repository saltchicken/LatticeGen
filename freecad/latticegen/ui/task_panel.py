"""Task Panel UI binding for lattice pattern generation."""

import os
import FreeCAD as App
import FreeCADGui as Gui

from freecad.latticegen.constants import PREVIEW_TRANSPARENCY
from freecad.latticegen.core import calculate_pattern_shape
from freecad.latticegen.ui.base_panel import BaseTaskPanel
from freecad.latticegen.utils import get_active_body

from freecad.latticegen.resources import Resources


class PatternTaskPanel(BaseTaskPanel):
    """Task panel for setting pattern parameters and generating geometry."""

    def __init__(self, target_obj, target_face=None):
        self.target_obj = target_obj
        self.target_face = target_face

        ui_path = Resources._pkg.joinpath("ui/lattice_panel.ui")
        
        super().__init__(str(ui_path), has_preview=True)

    def setup_ui(self):
        self.form.pattern_combo.currentIndexChanged.connect(self.queue_preview)
        self.form.mapping_combo.currentIndexChanged.connect(self.queue_preview)
        self.form.radius_spin.valueChanged.connect(self.queue_preview)
        self.form.gap_spin.valueChanged.connect(self.queue_preview)
        self.form.depth_spin.valueChanged.connect(self.queue_preview)
        self.form.fillet_spin.valueChanged.connect(self.queue_preview)
        self.form.border_spin.valueChanged.connect(self.queue_preview)
        self.form.threshold_spin.valueChanged.connect(self.queue_preview)
        self.form.offset_x_spin.valueChanged.connect(self.queue_preview)
        self.form.offset_y_spin.valueChanged.connect(self.queue_preview)
        self.form.operation_combo.currentIndexChanged.connect(self.queue_preview)

        if hasattr(self.form, "preview_toggle_check"):
            self.form.preview_toggle_check.stateChanged.connect(self.queue_preview)

    def get_shape(self, return_tool: bool = True):
        mode = "cut" if self.form.operation_combo.currentIndex() == 0 else "common"

        return calculate_pattern_shape(
            target_obj=self.target_obj,
            target_face=self.target_face,
            pattern=self.form.pattern_combo.currentText(),
            tile_radius=self.form.radius_spin.value(),
            gap=self.form.gap_spin.value(),
            mode=mode,
            offset_x=self.form.offset_x_spin.value(),
            offset_y=self.form.offset_y_spin.value(),
            inclusion_threshold=self.form.threshold_spin.value(),
            border_size=self.form.border_spin.value(),
            fillet_radius=self.form.fillet_spin.value(),
            mapping=self.form.mapping_combo.currentText(),
            extrude_depth=self.form.depth_spin.value(),
            return_tool=return_tool,
        )

    def calculate_preview(self):
        show_final = (
            hasattr(self.form, "preview_toggle_check") and self.form.preview_toggle_check.isChecked()
        )

        if show_final:
            self.target_obj.Visibility = False
            if self.has_preview and hasattr(self, "preview_obj") and self.preview_obj.ViewObject:
                self.preview_obj.ViewObject.ShapeColor = getattr(
                    self.target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8)
                )
                self.preview_obj.ViewObject.Transparency = getattr(
                    self.target_obj.ViewObject, "Transparency", 0
                )
            return self.get_shape(return_tool=False)
        else:
            self.target_obj.Visibility = True
            if self.has_preview and hasattr(self, "preview_obj") and self.preview_obj.ViewObject:
                self.preview_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
                self.preview_obj.ViewObject.Transparency = PREVIEW_TRANSPARENCY
            return self.get_shape(return_tool=True)

    def generate_final(self):
        active_body = get_active_body(self.target_obj)
        is_cut = self.form.operation_combo.currentIndex() == 0

        if active_body:
            tool_shape = self.get_shape(return_tool=True)
            if tool_shape is None:
                return

            tool_obj = App.ActiveDocument.addObject(
                "Part::Feature", f"{self.target_obj.Name}_LatticeTools"
            )
            tool_obj.Shape = tool_shape
            tool_obj.Visibility = False

            operation_name = "LatticeCut" if is_cut else "LatticePanel"
            bool_feat = active_body.newObject(
                "PartDesign::Boolean", f"{self.target_obj.Name}_{operation_name}"
            )
            bool_feat.Type = 1 if is_cut else 2
            bool_feat.Group = [tool_obj]

            self.target_obj.Visibility = False
            if bool_feat.ViewObject and self.target_obj.ViewObject:
                bool_feat.ViewObject.ShapeColor = getattr(
                    self.target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8)
                )

            App.ActiveDocument.recompute()
        else:
            shape = self.get_shape(return_tool=False)
            if shape is None:
                return

            operation_name = "Lattice" if is_cut else "Panels"
            final_obj = App.ActiveDocument.addObject(
                "Part::Feature", f"{self.target_obj.Name}_{operation_name}"
            )
            final_obj.Shape = shape

            self.target_obj.Visibility = False
            if final_obj.ViewObject and self.target_obj.ViewObject:
                final_obj.ViewObject.ShapeColor = getattr(
                    self.target_obj.ViewObject, "ShapeColor", (0.8, 0.8, 0.8)
                )

            group_name = "Generated_Lattices"
            group = App.ActiveDocument.getObject(group_name) or App.ActiveDocument.addObject(
                "App::DocumentObjectGroup", group_name
            )
            group.Label = "Generated Lattices"
            group.addObject(final_obj)

    def reject(self):
        self.target_obj.Visibility = True
        super().reject()
