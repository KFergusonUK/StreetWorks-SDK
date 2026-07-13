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


# Real feeds (confirmed on Iceland's IRCA feed - see streetworks.datex2.irca)
# list an empty placeholder value before the real text. The parser must
# skip it, not silently return the empty entry.
EMPTY_PLACEHOLDER_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<mc:messageContainer xmlns:sit="http://datex2.eu/schema/3/situation"
    xmlns:mc="http://datex2.eu/schema/3/messageContainer"
    xmlns:loc="http://datex2.eu/schema/3/locationReferencing"
    xmlns:com="http://datex2.eu/schema/3/common"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" modelBaseVersion="3">
  <mc:payload xsi:type="sit:SituationPublication" lang="is">
    <sit:situation id="EMPTY_PLACEHOLDER">
      <sit:situationRecord xsi:type="sit:MaintenanceWorks" id="EMPTY_PLACEHOLDER_1" version="0">
        <sit:generalPublicComment><sit:comment><com:values>
          <com:value lang="en"></com:value>
          <com:value lang="is">Raunverulegur texti</com:value>
        </com:values></sit:comment></sit:generalPublicComment>
      </sit:situationRecord>
    </sit:situation>
  </mc:payload>
</mc:messageContainer>
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

    # .raw stays unset for the streaming XML parser - a deliberate trade-off
    # (each Element is cleared after yielding to bound memory on huge feeds),
    # not an oversight - unlike the JSON-sourced adapters (National
    # Highways, Digitraffic), which populate it since the payload is
    # already fully in memory regardless.
    assert works.raw is None
    assert s.raw is None


def test_parses_linear_geometry_poslist():
    situations = list(iter_situations(_v3_stream()))
    measure = situations[0].measures[0]
    assert measure.location.kind == "LinearLocation"
    assert measure.location.points == ((50.85, 5.81), (50.86, 5.82), (50.87, 5.83))


# Real shape confirmed on France/Bison Fute (DATEX II v2): a TPEG linear
# location's from/to endpoints, each with their own pointCoordinates, plus
# an alertCLinear carrying both a raw numeric code (specificLocation) and a
# human-readable name (alertCLocationName) side by side.
TPEG_LINEAR_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<d2LogicalModel xmlns:ns2="http://datex2.eu/schema/2/2_0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" modelBaseVersion="2">
  <ns2:payloadPublication xsi:type="ns2:SituationPublication" lang="fr">
    <ns2:situation id="FR_1">
      <ns2:situationRecord xsi:type="ns2:MaintenanceWorks" id="FR_1_1" version="1">
        <ns2:groupOfLocations xsi:type="ns2:Linear">
          <ns2:tpegLinearLocation>
            <ns2:to xsi:type="ns2:TpegNonJunctionPoint">
              <ns2:pointCoordinates><ns2:latitude>42.908493</ns2:latitude><ns2:longitude>0.6984161</ns2:longitude></ns2:pointCoordinates>
            </ns2:to>
            <ns2:from xsi:type="ns2:TpegNonJunctionPoint">
              <ns2:pointCoordinates><ns2:latitude>42.92285</ns2:latitude><ns2:longitude>0.68384415</ns2:longitude></ns2:pointCoordinates>
            </ns2:from>
          </ns2:tpegLinearLocation>
          <ns2:alertCLinear xsi:type="ns2:AlertCMethod4Linear">
            <ns2:alertCMethod4PrimaryPointLocation>
              <ns2:alertCLocation>
                <ns2:alertCLocationName><ns2:values>
                  <ns2:value lang="fr">Fos</ns2:value>
                </ns2:values></ns2:alertCLocationName>
                <ns2:specificLocation>17855</ns2:specificLocation>
              </ns2:alertCLocation>
            </ns2:alertCMethod4PrimaryPointLocation>
          </ns2:alertCLinear>
          <ns2:linearWithinLinearElement>
            <ns2:linearElement><ns2:roadNumber>N0125</ns2:roadNumber></ns2:linearElement>
          </ns2:linearWithinLinearElement>
        </ns2:groupOfLocations>
        <ns2:roadMaintenanceType>roadworks</ns2:roadMaintenanceType>
      </ns2:situationRecord>
      <ns2:situationRecord xsi:type="ns2:ConstructionWorks" id="FR_1_2" version="1">
        <ns2:groupOfLocations xsi:type="ns2:Linear">
          <ns2:alertCLinear xsi:type="ns2:AlertCMethod4Linear">
            <ns2:alertCMethod4PrimaryPointLocation>
              <ns2:alertCLocation>
                <ns2:alertCLocationName><ns2:values>
                  <ns2:value lang="fr"/>
                </ns2:values></ns2:alertCLocationName>
                <ns2:specificLocation>19091</ns2:specificLocation>
              </ns2:alertCLocation>
            </ns2:alertCMethod4PrimaryPointLocation>
            <ns2:alertCMethod4SecondaryPointLocation>
              <ns2:alertCLocation>
                <ns2:alertCLocationName><ns2:values>
                  <ns2:value lang="fr">Pont-Cerda Tunnel du Puymorens</ns2:value>
                </ns2:values></ns2:alertCLocationName>
                <ns2:specificLocation>18533</ns2:specificLocation>
              </ns2:alertCLocation>
            </ns2:alertCMethod4SecondaryPointLocation>
          </ns2:alertCLinear>
        </ns2:groupOfLocations>
      </ns2:situationRecord>
    </ns2:situation>
  </ns2:payloadPublication>
</d2LogicalModel>
"""


def test_tpeg_linear_location_captures_both_endpoints():
    # Both from/to endpoints must survive as a 2-point line - a plain
    # "first pointCoordinates found anywhere" search used to silently drop
    # whichever endpoint wasn't listed first (confirmed live: France lists
    # `to` before `from`).
    situations = list(iter_situations(io.BytesIO(TPEG_LINEAR_FEED.encode())))
    works = situations[0].roadworks[0]
    assert works.location.kind == "Linear"
    assert works.location.points == ((42.92285, 0.68384415), (42.908493, 0.6984161))
    assert works.location.road_number == "N0125"


def test_alert_c_location_prefers_human_readable_name_over_raw_code():
    situations = list(iter_situations(io.BytesIO(TPEG_LINEAR_FEED.encode())))
    works = situations[0].roadworks[0]
    assert works.location.alert_c_location == "Fos"  # not the raw "17855"


def test_alert_c_location_tries_secondary_point_when_primary_name_is_empty():
    situations = list(iter_situations(io.BytesIO(TPEG_LINEAR_FEED.encode())))
    construction = situations[0].roadworks[1]
    assert construction.record_type == "ConstructionWorks"
    assert construction.location.alert_c_location == "Pont-Cerda Tunnel du Puymorens"


def test_multilingual_skips_empty_placeholder_value():
    situations = list(iter_situations(io.BytesIO(EMPTY_PLACEHOLDER_FEED.encode())))
    comments = situations[0].roadworks[0].comments
    assert comments == ("Raunverulegur texti",)


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
    respx.get("https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz").mock(
        return_value=httpx.Response(200, content=gzip.compress(V3_FEED.encode()))
    )
    with NDWClient() as ndw:
        path = ndw.download_planned_works(tmp_path / "feed.xml.gz")
    assert len(list(iter_roadworks(path))) == 1
