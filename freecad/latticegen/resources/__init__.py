import importlib
import importlib.resources
from typing import ClassVar

import FreeCAD as App

class Resources:
    """Addon LatticeGen resource manager"""

    _pkg = importlib.resources.files(__name__)
    _gui_icons_added: ClassVar[bool] = False

    @classmethod
    def icon(cls, path: str) -> str:
        """Resolve relative icon path to actual path in the module system"""
        base = cls._pkg / "icons"
        return str(base.joinpath(path))

    @classmethod
    def __truediv__(cls, path: str) -> str:
        """Resolve relative resource path to actual path in the module system"""
        return str(cls._pkg.joinpath(path))

    @classmethod
    def gui_register_icons(cls) -> bool:
        if not App.GuiUp:
            raise RuntimeError(f"{__name__}: Icon path cannot be added without Gui.")

        if cls._gui_icons_added:
            return False

        icons = str(cls._pkg / "icons")
        App.Console.PrintLog(f"Installing {__name__}: icons={icons}\n")
        App.Gui.addIconPath(icons)
        cls._gui_icons_added = True
        return True
