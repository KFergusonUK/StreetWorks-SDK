"""Scottish Road Works Register (SRWR) Open Data provider.

Credential-free access to Scotland's national road works register via the
published Open Data CSV extracts (Open Government Licence v3). See
https://roadworks.scot/publications/scottish-road-works-register-open-data
"""

from .client import BASE_URL, AsyncSRWRClient, SRWRClient
from .codes import describe
from .reader import Activity, iter_activities, iter_records, latest_activities
from .records import Record

__all__ = [
    "SRWRClient",
    "AsyncSRWRClient",
    "BASE_URL",
    "Record",
    "Activity",
    "iter_records",
    "iter_activities",
    "latest_activities",
    "describe",
]
