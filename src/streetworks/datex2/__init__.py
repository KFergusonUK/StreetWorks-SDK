"""DATEX II - the European standard for traffic and roadworks data exchange.

A streaming, namespace-tolerant parser for SituationPublication roadworks
(DATEX II v3 and v2), plus source adapters for National Access Point feeds:
the Netherlands' credential-free NDW open data (XML), National Highways'
Road and Lane Closures service for England (JSON - see
:mod:`streetworks.datex2.nationalhighways` for why it needs its own parsing
path), Fintraffic's Digitraffic open data for Finland (its own Simple-JSON
schema, not a DATEX-II serialisation - see
:mod:`streetworks.datex2.digitraffic` for the field-by-field mapping),
IRCA/Vegagerðin's DATEX II snapshotPull service for Iceland (credential-free
- see :mod:`streetworks.datex2.irca`), and Statens vegvesen's DATEX II
snapshotPull service for Norway (**pending live verification** - see
:mod:`streetworks.datex2.vegvesen`).
"""

from .digitraffic import BASE_URL as DIGITRAFFIC_BASE_URL
from .digitraffic import DigitrafficClient
from .digitraffic import parse_situations as parse_digitraffic_situations
from .digitraffic import provinces as digitraffic_provinces
from .irca import BASE_URL as IRCA_BASE_URL
from .irca import SITUATION_ENDPOINT as IRCA_SITUATION_ENDPOINT
from .irca import IcelandClient
from .models import Location, Period, Situation, SituationRecord, Validity
from .nationalhighways import BASE_URL as NH_BASE_URL
from .nationalhighways import ClosureType, NationalHighwaysClient
from .nationalhighways import parse_situations as parse_nationalhighways_situations
from .ndw import BASE_URL, PLANNED_WORKS_FEED, NDWClient
from .parser import iter_roadworks, iter_roadworks_full, iter_situations, iter_situations_full
from .vegvesen import BASE_URL as VEGVESEN_BASE_URL
from .vegvesen import NVDB_BASE_URL, VegvesenClient

__all__ = [
    "iter_situations",
    "iter_roadworks",
    "iter_situations_full",
    "iter_roadworks_full",
    "Situation",
    "SituationRecord",
    "Validity",
    "Period",
    "Location",
    "NDWClient",
    "BASE_URL",
    "PLANNED_WORKS_FEED",
    "NationalHighwaysClient",
    "ClosureType",
    "parse_nationalhighways_situations",
    "NH_BASE_URL",
    "DigitrafficClient",
    "parse_digitraffic_situations",
    "digitraffic_provinces",
    "DIGITRAFFIC_BASE_URL",
    "IcelandClient",
    "IRCA_BASE_URL",
    "IRCA_SITUATION_ENDPOINT",
    "VegvesenClient",
    "VEGVESEN_BASE_URL",
    "NVDB_BASE_URL",
]
