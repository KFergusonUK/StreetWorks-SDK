"""Copenhagen: "Gravetilladelser" (excavation permits) - this SDK's first
Nordic roadworks coverage. See :mod:`streetworks.copenhagen.client` for
the full investigation, including why the source brief's guessed dataset
name and ArcGIS/OGC Features backend don't match the real WFS source.
"""

from .client import GRAVETILLADELSER_URL, CopenhagenClient

__all__ = ["GRAVETILLADELSER_URL", "CopenhagenClient"]
