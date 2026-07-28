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
- see :mod:`streetworks.datex2.irca`), Bison Futé/the DIRs' DATEX II v2 feed
for France (credential-free - see :mod:`streetworks.datex2.bisonfute`), the
DGT's DATEX II v3 SituationPublication for Spain, excl. Catalonia & the
Basque Country (credential-free - see :mod:`streetworks.datex2.dgt`),
Verkeerscentrum Vlaanderen's DATEX II v3 feed for Belgium/Flanders only,
not all-Belgium (credential-free - see :mod:`streetworks.datex2.belgium`
for the coverage question and a real non-WGS84 CRS finding), Ponts et
Chaussées' DATEX II v2.3 feed for Luxembourg (credential-free - see
:mod:`streetworks.datex2.luxembourg`), the Road Infrastructure Agency's
DATEX II v2.3 "Short-term Road Construction" feed for Bulgaria
(credential-free - see :mod:`streetworks.datex2.bulgaria` for the wrong
NAP-listed host, the date-stamped catalogue-then-file fetch, and a real
mislabelled-encoding finding), the Basque Government's DATEX II **v1.0**
feed for the Basque Country (credential-free, licence explicitly absent -
see :mod:`streetworks.datex2.euskadi` for the oldest schema version in
this SDK and a real, additive parser fix it needed), and three
**Credentials wanted** scaffolds - built to a confirmed API/schema shape
but not yet verified against real authenticated data, pending a tester
with credentials: Statens vegvesen for Norway (see
:mod:`streetworks.datex2.vegvesen`), Trafikverket for Sweden (its own
bespoke XML-request/JSON-response API, not DATEX - see
:mod:`streetworks.datex2.trafikverket`), and Vejdirektoratet for Denmark
(genuine DATEX II 3.2 - see :mod:`streetworks.datex2.vejdirektoratet`).
"""

from .belgium import BASE_URL as BELGIUM_BASE_URL
from .belgium import CRS as BELGIUM_CRS
from .belgium import DATEX_PATH as BELGIUM_DATEX_PATH
from .belgium import BelgiumClient
from .bisonfute import BASE_URL as BISONFUTE_BASE_URL
from .bisonfute import CONTENT_PATH as BISONFUTE_CONTENT_PATH
from .bisonfute import BisonFuteClient
from .bisonfute import dir_regions as bisonfute_dir_regions
from .bulgaria import BASE_URL as BULGARIA_BASE_URL
from .bulgaria import CATALOGUE_PATH as BULGARIA_CATALOGUE_PATH
from .bulgaria import BulgariaClient
from .dgt import BASE_URL as DGT_BASE_URL
from .dgt import SITUATION_PUBLICATION_PATH as DGT_SITUATION_PUBLICATION_PATH
from .dgt import DGTClient
from .dgt import provinces as dgt_provinces
from .digitraffic import BASE_URL as DIGITRAFFIC_BASE_URL
from .digitraffic import DigitrafficClient
from .digitraffic import parse_situations as parse_digitraffic_situations
from .digitraffic import provinces as digitraffic_provinces
from .euskadi import BASE_URL as EUSKADI_BASE_URL
from .euskadi import SITUATION_PATH as EUSKADI_SITUATION_PATH
from .euskadi import EuskadiClient
from .euskadi import provinces as euskadi_provinces
from .irca import BASE_URL as IRCA_BASE_URL
from .irca import SITUATION_ENDPOINT as IRCA_SITUATION_ENDPOINT
from .irca import IcelandClient
from .luxembourg import BASE_URL as LUXEMBOURG_BASE_URL
from .luxembourg import DATEX_PATH as LUXEMBOURG_DATEX_PATH
from .luxembourg import LuxembourgClient
from .models import Location, Period, Situation, SituationRecord, Validity
from .nationalhighways import BASE_URL as NH_BASE_URL
from .nationalhighways import ClosureType, NationalHighwaysClient
from .nationalhighways import parse_situations as parse_nationalhighways_situations
from .ndw import BASE_URL, PLANNED_WORKS_FEED, NDWClient
from .parser import iter_roadworks, iter_roadworks_full, iter_situations, iter_situations_full
from .trafikverket import BASE_URL as TRAFIKVERKET_BASE_URL
from .trafikverket import DATA_PATH as TRAFIKVERKET_DATA_PATH
from .trafikverket import TrafikverketClient
from .trafikverket import parse_situations as parse_trafikverket_situations
from .vegvesen import BASE_URL as VEGVESEN_BASE_URL
from .vegvesen import NVDB_BASE_URL, VegvesenClient
from .vejdirektoratet import VejdirektoratetClient

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
    "BisonFuteClient",
    "BISONFUTE_BASE_URL",
    "BISONFUTE_CONTENT_PATH",
    "bisonfute_dir_regions",
    "DGTClient",
    "DGT_BASE_URL",
    "DGT_SITUATION_PUBLICATION_PATH",
    "dgt_provinces",
    "EuskadiClient",
    "EUSKADI_BASE_URL",
    "EUSKADI_SITUATION_PATH",
    "euskadi_provinces",
    "VegvesenClient",
    "VEGVESEN_BASE_URL",
    "NVDB_BASE_URL",
    "BelgiumClient",
    "BELGIUM_BASE_URL",
    "BELGIUM_DATEX_PATH",
    "BELGIUM_CRS",
    "LuxembourgClient",
    "LUXEMBOURG_BASE_URL",
    "LUXEMBOURG_DATEX_PATH",
    "BulgariaClient",
    "BULGARIA_BASE_URL",
    "BULGARIA_CATALOGUE_PATH",
    "TrafikverketClient",
    "TRAFIKVERKET_BASE_URL",
    "TRAFIKVERKET_DATA_PATH",
    "parse_trafikverket_situations",
    "VejdirektoratetClient",
]
