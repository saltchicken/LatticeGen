"""Factory for instantiating mapping strategies."""

from freecad.latticegen.strategies.base import BaseMappingStrategy
from freecad.latticegen.strategies.cylindrical import CylindricalStrategy
from freecad.latticegen.strategies.cylindrical import ProjectedCylindricalStretchedStrategy
from freecad.latticegen.strategies.cylindrical import ProjectedCylindricalUniformStrategy
from freecad.latticegen.strategies.planar import PlanarStrategy
from freecad.latticegen.strategies.planar import ProjectedPlanarStrategy
from freecad.latticegen.strategies.spherical import ProjectedSphericalStrategy
from freecad.latticegen.strategies.spherical import RadialStrategy
from freecad.latticegen.strategies.spherical import SphericalStrategy
from freecad.latticegen.strategies.surface import SurfaceUVStrategy


class MappingFactory:
    """Instantiates strategy handlers based on string selection."""

    @classmethod
    def create(cls, mapping_type: str, target_shape, target_face=None, axis="Z"):
        strategy_class = BaseMappingStrategy._registry.get(mapping_type, PlanarStrategy)

        if mapping_type == "Surface UV" and not target_face:
            faces = target_shape.Faces
            if faces:
                target_face = max(faces, key=lambda f: f.Area)

        return strategy_class(target_shape, target_shape.BoundBox, target_face, axis=axis)
        
    @staticmethod
    def get_available_mappings() -> list:
        return list(BaseMappingStrategy._registry.keys())
