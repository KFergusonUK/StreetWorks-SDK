"""Tests for the DATEX II parser and NDW adapter.

The v3 fixture is derived from a real record in the Dutch national NDW
planned-works feed (lightly trimmed); the v2 fixture follows the published
D2LogicalModel structure for the same concepts.
"""

import gzip
import io
from datetime import datetime, timezone

import httpx
import respx

from streetworks.datex2 import NDWClient, iter_roadworks, iter_situations

V3_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<mc:messageContainer xmlns:sit="http://datex2.eu/schema/3/situation"
    xmlns:mc="http://datex2.eu/schema/3/messageContainer"
    xmlns:loc="http://datex2.eu/schema/3/locationReferencing"
    xmlns:com="http://datex2.eu/schema/3/common"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" modelBaseVersion="3">
  <mc:payload xsi:type="sit:SituationPublication" lang="nl">
    <com:publicationTime>2026-07-05T19:15:00Z</com:publicationTime>
    <sit:situation id="NDW03_554987">
      <sit:overallSeverity>low</sit:overallSeverity>
      <sit:situationVersionTime>2026-04-24T08:38:22Z</sit:situationVersionTime>
      <sit:situationRecord xsi:type="sit:MaintenanceWorks" id="NDW03_554987_MAN" version="4">
        <sit:situationRecordCreationTime>2026-03-20T14:31:37Z</sit:situationRecordCreationTime>
        <sit:situationRecordVersionTime>2026-04-24T08:38:22Z</sit:situationRecordVersionTime>
        <sit:probabilityOfOccurrence>probable</sit:probabilityOfOccurrence>
        <sit:source><com:sourceName><com:values>
          <com:value lang="nl">Provincie Limburg</com:value>
        </com:values></com:sourceName></sit:source>
        <sit:validity>
          <com:validityStatus>definedByValidityTimeSpec</com:validityStatus>
          <com:validityTimeSpecification>
            <com:overallStartTime>2026-07-13T07:00:00Z</com:overallStartTime>
            <com:overallEndTime>2026-07-15T14:00:00Z</com:overallEndTime>
            <com:validPeriod>
              <com:startOfPeriod>2026-07-13T07:00:00Z</com:startOfPeriod>
              <com:endOfPeriod>2026-07-13T14:00:00Z</com:endOfPeriod>
            </com:validPeriod>
          </com:validityTimeSpecification>
        </sit:validity>
        <sit:impact><sit:delays><sit:delayBand>upToTenMinutes</sit:delayBand></sit:delays></sit:impact>
        <sit:cause>
          <sit:causeDescription><com:values>
            <com:value lang="nl">Kabels / Leidingen</com:value>
          </com:values></sit:causeDescription>
          <sit:causeType>roadMaintenance</sit:causeType>
        </sit:cause>
        <sit:generalPublicComment><sit:comment><com:values>
          <com:value lang="nl">Verminderd aantal rijstroken beschikbaar</com:value>
        </com:values></sit:comment></sit:generalPublicComment>
        <sit:locationReference xsi:type="loc:PointLocation">
          <loc:supplementaryPositionalDescription>
            <loc:carriageway><loc:carriageway>mainCarriageway</loc:carriageway></loc:carriageway>
          </loc:supplementaryPositionalDescription>
          <loc:pointByCoordinates>
            <loc:pointCoordinates>
              <loc:latitude>50.857113</loc:latitude>
              <loc:longitude>5.8124113</loc:longitude>
            </loc:pointCoordinates>
          </loc:pointByCoordinates>
        </sit:locationReference>
        <sit:operatorActionStatus>approved</sit:operatorActionStatus>
        <sit:urgentRoadworks>false</sit:urgentRoadworks>
        <sit:roadMaintenanceType>maintenanceWork</sit:roadMaintenanceType>
      </sit:situationRecord>
      <sit:situationRecord xsi:type="sit:SpeedManagement" id="NDW03_554987_RSS" version="4">
        <sit:locationReference xsi:type="loc:LinearLocation">
          <loc:gmlLineString>
            <loc:posList>50.85 5.81 50.86 5.82 50.87 5.83</loc:posList>
          </loc:gmlLineString>
        </sit:locationReference>
      </sit:situationRecord>
    </sit:situation>
    <sit:situation id="NDW03_events_only">
      <sit:situationRecord xsi:type="sit:PublicEvent" id="EV_1" version="1"/>
    </sit:situation>
  </mc:payload>
</mc:messageContainer>
"""

V2_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<d2LogicalModel xmlns="http://datex2.eu/schema/2/2_0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" modelBaseVersion="2">
  <payloadPublication xsi:type="SituationPublication" lang="en">
    <publicationTime>2026-07-05T10:00:00Z</publicationTime>
    <situation id="V2_1" version="1">
      <situationRecord xsi:type="MaintenanceWorks" id="V2_1_R1" version="1">
        <situationRecordCreationTime>2026-07-01T09:00:00Z</situationRecordCreationTime>
        <validity>
          <validityStatus>active</validityStatus>
          <validityTimeSpecification>
            <overallStartTime>2026-07-01T09:00:00Z</overallStartTime>
          </validityTimeSpecification>
        </validity>
        <groupOfLocations xsi:type="Point">
          <locationForDisplay>
            <latitude>52.1</latitude>
            <longitude>4.3</longitude>
          </locationForDisplay>
          <pointByCoordinates>
            <pointCoordinates>
              <latitude>52.1</latitude>
              <longitude>4.3</longitude>
            </pointCoordinates>
          </pointByCoordinates>
        </groupOfLocations>
        <roadMaintenanceType>resurfacingWork</roadMaintenanceType>
      </situationRecord>
    </situation>
  </payloadPublication>
</d2LogicalModel>
"""


def _v3_stream() -> io.BytesIO:
    return io.BytesIO(V3_FEED.encode())


def test_parses_v3_situation_from_real_shape():
    situations = list(iter_situations(_v3_stream()))
    assert len(situations) == 2
    s = situations[0]
    assert s.id == "NDW03_554987"
    assert s.overall_severity == "low"
    assert len(s.roadworks) == 1 and len(s.measures) == 1

    works = s.roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.source_name == "Provincie Limburg"
    assert works.cause_type == "roadMaintenance"
    assert works.cause_description == "Kabels / Leidingen"
    assert works.comments == ("Verminderd aantal rijstroken beschikbaar",)
    assert works.impact_delay_band == "upToTenMinutes"
    assert works.operator_action_status == "approved"
    assert works.urgent is False
    assert works.road_maintenance_type == "maintenanceWork"
    assert works.validity.overall_start == datetime(2026, 7, 13, 7, tzinfo=timezone.utc)
    assert len(works.validity.periods) == 1
    assert works.location.kind == "PointLocation"
    assert works.location.point == (50.857113, 5.8124113)
    assert works.location.carriageway == "mainCarriageway"


def test_parses_linear_geometry_poslist():
    situations = list(iter_situations(_v3_stream()))
    measure = situations[0].measures[0]
    assert measure.location.kind == "LinearLocation"
    assert measure.location.points == ((50.85, 5.81), (50.86, 5.82), (50.87, 5.83))


def test_iter_roadworks_filters_out_event_only_situations():
    situations = list(iter_roadworks(_v3_stream()))
    assert [s.id for s in situations] == ["NDW03_554987"]


def test_parses_v2_d2logicalmodel():
    situations = list(iter_situations(io.BytesIO(V2_FEED.encode())))
    assert len(situations) == 1
    works = situations[0].roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.road_maintenance_type == "resurfacingWork"
    assert works.validity.status == "active"
    assert works.location.point == (52.1, 4.3)


def test_gzip_detected_by_magic_bytes(tmp_path):
    path = tmp_path / "feed.data"  # deliberately not .gz
    path.write_bytes(gzip.compress(V3_FEED.encode()))
    assert len(list(iter_situations(path))) == 2


@respx.mock
def test_ndw_client_downloads_planned_works(tmp_path):
    respx.get(
        "https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz"
    ).mock(return_value=httpx.Response(200, content=gzip.compress(V3_FEED.encode())))
    with NDWClient() as ndw:
        path = ndw.download_planned_works(tmp_path / "feed.xml.gz")
    assert len(list(iter_roadworks(path))) == 1
