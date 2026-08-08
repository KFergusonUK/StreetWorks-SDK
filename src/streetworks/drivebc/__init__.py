"""DriveBC: British Columbia's Open511 road-events feed - this SDK's
first Canadian roadworks provider. See :mod:`streetworks.drivebc.client`
for the full investigation, including why this ships bespoke rather than
as a general Open511 parser.
"""

from .client import EVENTS_URL, DriveBCClient

__all__ = ["EVENTS_URL", "DriveBCClient"]
