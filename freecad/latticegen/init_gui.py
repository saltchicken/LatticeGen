import FreeCAD as App
import FreeCADGui as Gui

from .commands import LatticeGenCommand
from .resources import Resources

# 1. Register icons so FreeCAD can find them
Resources.gui_register_icons()

# 2. Register your command
LatticeGenCommand.Install()


# 3. Create a safe Workbench Manipulator
class PartDesignManipulator:

    def modifyToolBars(self):
        return [{"append": LatticeGenCommand.Name, "toolBar": "LatticeGen"}]

    def modifyMenuBar(self):
        return []

    def modifyContextMenu(self, recipient):
        return []


if App.GuiUp:
    # Safely inject the manipulator
    manipulator = PartDesignManipulator()
    Gui.addWorkbenchManipulator(manipulator)
