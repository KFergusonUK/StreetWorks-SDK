"""Street Manager environments, API versions and URL construction.

Confirmed against the DfT API specification (V6 baseline, July 2026):

* Sandbox host:    ``https://api.sandbox.manage-roadworks.service.gov.uk``
* Production host: ``https://api.manage-roadworks.service.gov.uk``
* URL pattern:     ``{host}/{version}/{api}/...`` e.g. ``/v6/work/works/{wrn}``
* Versions are path-based: ``v6`` (stable baseline), ``v7`` (active
  development), and ``latest`` (tracks the newest code, used by the UI).
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    SANDBOX = "https://api.sandbox.manage-roadworks.service.gov.uk"
    PRODUCTION = "https://api.manage-roadworks.service.gov.uk"

    @property
    def host(self) -> str:
        return self.value


class ApiVersion(str, Enum):
    V6 = "v6"  # stable baseline - additive changes only
    V7 = "v7"  # under active development
    LATEST = "latest"


class Api(str, Enum):
    """The nine Street Manager API services (V6/V7)."""

    WORK = "work"
    REPORTING = "reporting"
    LOOKUP = "lookup"
    GEOJSON = "geojson"
    PARTY = "party"
    EXPORT = "export"
    EVENT = "event"
    SAMPLING = "sampling"
    WORKLIST = "worklist"


def base_url(
    environment: Environment | str,
    version: ApiVersion | str,
    api: Api | str,
) -> str:
    """Build the base URL for one API service, e.g. ``.../v6/work``."""
    if isinstance(environment, Environment):
        host = environment.host
    else:
        host = str(environment).rstrip("/")
    version_str = version.value if isinstance(version, ApiVersion) else str(version).strip("/")
    api_str = api.value if isinstance(api, Api) else str(api).strip("/")
    return f"{host}/{version_str}/{api_str}"
