import FreeCAD as App
import FreeCADGui as Gui

from .commands import LatticeGenCommand
from .resources import Resources

class LatticeGenWorkbench(Gui.Workbench):
    MenuText = "LatticeGen"
    ToolTip = "Lattice Generation Tools"
    Icon = Resources.icon("LatticeGen.svg") # You can make a specific -wb.svg later

    def Initialize(self):
        # Create a toolbar and add your command to it
        self.appendToolbar("Lattice Tools", [LatticeGenCommand.Name])
        self.appendMenu("LatticeGen", [LatticeGenCommand.Name])

    @classmethod
    def Install(cls):
        Gui.addWorkbench(cls)
