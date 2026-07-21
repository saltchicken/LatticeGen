# freecad/freecad.latticegen/init_gui.py
from .resources import Resources
from .commands import LatticeGenCommand
from .lattice_workbench import LatticeGenWorkbench

# 1. Register icons so FreeCAD can find them
Resources.gui_register_icons()

# 2. Register your commands
LatticeGenCommand.Install()

# 3. Register your workbench
LatticeGenWorkbench.Install()
