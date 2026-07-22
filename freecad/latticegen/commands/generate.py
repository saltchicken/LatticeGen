import FreeCAD as App
import FreeCADGui as Gui

from freecad.latticegen.resources import Resources
from freecad.latticegen.ui.task_panel import PatternTaskPanel


class LatticeGenCommand:
    Name = "LatticeGen_Generate"

    def GetResources(self):
        return {
            "Pixmap": Resources.icon("LatticeGen.svg"),
            "MenuText": "Generate Lattice",
            "ToolTip": "Generate lattice of shapes over a range"
        }

    def Activated(self):
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()

        selection = Gui.Selection.getSelectionEx()
        if not selection or not hasattr(selection[0].Object, "Shape"):
            App.Console.PrintError(
                "Error: Select a valid solid object first.\n")
            return

        target_obj = selection[0].Object
        target_face = None

        if selection[0].HasSubObjects and "Face" in selection[
                0].SubElementNames[0]:
            target_face = target_obj.Shape.getElement(
                selection[0].SubElementNames[0])

        panel = PatternTaskPanel(target_obj, target_face)
        Gui.Control.showDialog(panel)

    def IsActive(self):
        # Optional: Only activate if a document is open
        return App.ActiveDocument is not None

    @classmethod
    def Install(cls):
        if App.GuiUp:
            Gui.addCommand(cls.Name, cls())
