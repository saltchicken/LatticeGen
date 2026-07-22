"""Factory for instantiating mapping strategies."""

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

    STRATEGIES = {
        "Planar":
            PlanarStrategy,
        "Projected Planar":
            ProjectedPlanarStrategy,
        "Cylindrical":
            CylindricalStrategy,
        "Projected Cylindrical (Uniform)":
            ProjectedCylindricalUniformStrategy,
        "Projected Cylindrical (Stretched)":
            ProjectedCylindricalStretchedStrategy,
        "Spherical":
            SphericalStrategy,
        "Projected Spherical":
            ProjectedSphericalStrategy,
        "Radial":
            RadialStrategy,
        "Surface UV":
            SurfaceUVStrategy,
    }

    @classmethod
    def create(cls, mapping_type: str, target_shape, target_face=None):
        strategy_class = cls.STRATEGIES.get(mapping_type, PlanarStrategy)

        if mapping_type == "Surface UV" and not target_face:
            faces = target_shape.Faces
            if faces:
                target_face = max(faces, key=lambda f: f.Area)

        return strategy_class(target_shape, target_shape.BoundBox, target_face)
