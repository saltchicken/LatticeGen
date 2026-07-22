"""Base class for FreeCAD UI Task Panels."""

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore
from PySide6 import QtWidgets

from freecad.latticegen.constants import PREVIEW_DELAY_MS


class BaseTaskPanel:
    """Reusable TaskPanel wrapper handling UIC auto-loading and preview debounce."""

    def __init__(self, ui_file_path: str, has_preview: bool = True):
        self.form = Gui.PySideUic.loadUi(ui_file_path)
        self.has_preview = has_preview

        if self.has_preview:
            self.preview_timer = QtCore.QTimer()
            self.preview_timer.setSingleShot(True)
            self.preview_timer.setInterval(PREVIEW_DELAY_MS)
            self.preview_timer.timeout.connect(self._trigger_preview)

            App.ActiveDocument.openTransaction("Preview Transaction")
            self.preview_obj = App.ActiveDocument.addObject(
                "Part::Feature", "PreviewObject")

        self.setup_ui()

        if self.has_preview:
            self.queue_preview()

    def setup_ui(self):
        pass

    def queue_preview(self, *args):
        if self.has_preview:
            self.preview_timer.start()

    def _trigger_preview(self):
        try:
            shape = self.calculate_preview()
            if shape and not shape.isNull():
                self.preview_obj.Shape = shape
                App.ActiveDocument.recompute()
        except Exception as e:
            App.Console.PrintWarning(f"Preview calculation error: {e}\n")

    def calculate_preview(self):
        return None

    def generate_final(self):
        pass

    def getStandardButtons(self):
        return (QtWidgets.QDialogButtonBox.Ok |
                QtWidgets.QDialogButtonBox.Cancel).value

    def accept(self):
        if self.has_preview:
            App.ActiveDocument.abortTransaction()

        App.ActiveDocument.openTransaction("Apply Tool")
        try:
            self.generate_final()
            App.ActiveDocument.commitTransaction()
        except Exception as e:
            App.ActiveDocument.abortTransaction()
            App.Console.PrintError(f"Generation failed: {e}\n")

        Gui.Control.closeDialog()

    def reject(self):
        if self.has_preview:
            App.ActiveDocument.abortTransaction()
        Gui.Control.closeDialog()
