"""Tests for streetworks.common.from_datex2.

Covers all DATEX adapters through the one shared converter: a trimmed NDW
v3 fixture (same shape as test_datex2.py's) for the XML path, the real
National Highways closures fixture for the JSON path - the one that
actually carries all three real validityStatus values (active, planned,
suspended), so it's what exercises date_confidence properly - the real
Digitraffic (Finland) fixture, which has no lifecycle-status field at all
and needs the province() lookup for administrative_area, the real IRCA
(Iceland) fixture, the real Bison Futé (France) fixture - which needs the
dir_regions() lookup the same shape of way, and exercises real TPEG linear
geometry surviving as Coordinate.points - the real DGT (Spain) fixture -
which needs its own provinces() lookup and exercises the cause-based
roadworks discriminator (no MaintenanceWorks/ConstructionWorks xsi:type
exists in that feed at all) - and the Vegvesen (Norway) fixture -
**pending live verification**, real DATEX data but from Iceland's
sibling implementation, not Norway itself (see streetworks.datex2.vegvesen).
"""

import io
import json
from datetime import datetime, timezone
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_datex2
from streetworks.datex2 import iter_situations, iter_situations_full
from streetworks.datex2.bisonfute import dir_regions as bisonfute_dir_regions
from streetworks.datex2.dgt import provinces as dgt_provinces
from streetworks.datex2.digitraffic import parse_situations as parse_digitraffic_situations
from streetworks.datex2.digitraffic import provinces
from streetworks.datex2.models import Location, Situation, SituationRecord, Validity
from streetworks.datex2.nationalhighways import parse_situations

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
        <sit:source><com:sourceName><com:values>
          <com:value lang="nl">Provincie Limburg</com:value>
        </com:values></com:sourceName></sit:source>
        <sit:validity>
          <com:validityStatus>definedByValidityTimeSpec</com:validityStatus>
          <com:validityTimeSpecification>
            <com:overallStartTime>2026-07-13T07:00:00Z</com:overallStartTime>
            <com:overallEndTime>2026-07-15T14:00:00Z</com:overallEndTime>
          </com:validityTimeSpecification>
        </sit:validity>
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
  </mc:payload>
</mc:messageContainer>
"""

NH_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "nationalhighways_closures_planned.json").read_text(
        encoding="utf-8"
    )
)


def test_from_datex2_ndw_maps_one_site_per_roadworks_record_only():
    situation = next(iter_situations(io.BytesIO(V3_FEED.encode())))
    assert len(situation.roadworks) == 1 and len(situation.measures) == 1

    works = from_datex2(situation, territory="Netherlands")
    assert works.reference == "NDW03_554987"
    assert works.promoter == "Provincie Limburg"
    # territory can't be inferred (see module docstring) - caller states it;
    # administrative_area defaults to source_name, a real province name here.
    assert works.territory == "Netherlands"
    assert works.administrative_area == "Provincie Limburg"
    assert works.coordinate.value == (50.857113, 5.8124113)
    assert works.coordinate.crs == "EPSG:4326"
    assert works.coordinate.points is None  # a genuine point location, not a line
    assert works.source_grade is SourceGrade.OPERATOR
    # Only the MaintenanceWorks record becomes a site - the SpeedManagement
    # measure record is deliberately left out of the common model.
    assert len(works.sites) == 1

    site = works.sites[0]
    assert site.reference == "NDW03_554987_MAN"
    assert site.works_type == "maintenanceWork"
    assert site.status == "definedByValidityTimeSpec"
    assert site.date_confidence is DateConfidence.UNKNOWN  # unrecognised status
    assert site.proposed_start == datetime(2026, 7, 13, 7, tzinfo=timezone.utc)
    assert site.proposed_end == datetime(2026, 7, 15, 14, tzinfo=timezone.utc)
    assert site.actual_start is None
    assert site.location_description == "mainCarriageway"
    assert site.traffic_management == "Verminderd aantal rijstroken beschikbaar"


def test_from_datex2_linear_location_survives_as_coordinate_points():
    # A LinearLocation/posList with several vertices used to collapse to
    # just the first one (Location.point) - Coordinate.points now carries
    # the whole line, value staying the first vertex for compatibility.
    situation = Situation(
        id="linear-1",
        records=[
            SituationRecord(
                id="linear-1-rec",
                record_type="MaintenanceWorks",
                validity=Validity(),
                location=Location(
                    kind="LinearLocation",
                    points=((50.85, 5.81), (50.86, 5.82), (50.87, 5.83)),
                ),
            )
        ],
    )
    works = from_datex2(situation, territory="Netherlands")
    assert works.coordinate.value == (50.85, 5.81)
    assert works.coordinate.points == ((50.85, 5.81), (50.86, 5.82), (50.87, 5.83))
    assert works.sites[0].coordinate.points == ((50.85, 5.81), (50.86, 5.82), (50.87, 5.83))


def test_from_datex2_without_territory_leaves_it_unset():
    situation = next(iter_situations(io.BytesIO(V3_FEED.encode())))
    works = from_datex2(situation)  # no territory passed
    assert works.territory is None
    assert works.administrative_area == "Provincie Limburg"  # still defaults from source_name


def _site_for(situation_id: str):
    situation = next(s for s in parse_situations(NH_FIXTURE) if s.id == situation_id)
    return from_datex2(situation).sites[0]


def test_from_datex2_national_highways_overrides_administrative_area():
    # National Highways' source_name is a generic "roadworks" label, not an
    # authority name - the operator is the authority, passed explicitly.
    situation = next(s for s in parse_situations(NH_FIXTURE) if s.id == "467118")
    works = from_datex2(situation, territory="England", administrative_area="National Highways")
    assert works.territory == "England"
    assert works.administrative_area == "National Highways"
    assert works.sites[0].territory == "England"  # delegates from the parent Works
    assert works.sites[0].administrative_area == "National Highways"


def test_from_datex2_nh_planned_status_is_estimated():
    site = _site_for("467118")
    assert site.status == "planned"
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.actual_start is None
    assert site.proposed_start is not None


def test_from_datex2_nh_active_status_is_verified():
    site = _site_for("458159")
    assert site.status == "active"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_start == site.proposed_start
    assert site.works_type == "roadImprovementOrUpgrading"


def test_from_datex2_nh_suspended_status_is_also_verified():
    # Suspended means temporarily paused, not that the dates are estimates -
    # a real occurrence with genuine validity dates, same as active.
    site = _site_for("473996")
    assert site.status == "suspended"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_start == site.proposed_start


DIGITRAFFIC_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "digitraffic_roadworks.json").read_text(
        encoding="utf-8"
    )
)


def test_from_datex2_digitraffic_uses_province_lookup_for_administrative_area():
    situations = parse_digitraffic_situations(DIGITRAFFIC_FIXTURE)
    situation_provinces = provinces(DIGITRAFFIC_FIXTURE)
    situation = next(s for s in situations if s.id == "GUID50465119")

    works = from_datex2(
        situation,
        territory="Finland",
        administrative_area=situation_provinces.get(situation.id),
    )
    assert works.territory == "Finland"
    assert works.administrative_area == "Pohjois-Savo"  # genuinely stated, not inferred
    # source_name (a Fintraffic traffic centre) is promoter, not administrative_area.
    assert works.promoter == "Fintraffic Tieliikennekeskus Tampere"
    assert len(works.sites) == 3  # one per roadWorkPhase


def test_from_datex2_digitraffic_date_confidence_is_always_unknown():
    # Digitraffic has no active/planned/suspended-equivalent field, so
    # validity.status is always None and date_confidence honestly reflects
    # that - never guessed at from severity or anything else.
    situations = parse_digitraffic_situations(DIGITRAFFIC_FIXTURE)
    situation = next(s for s in situations if s.id == "GUID50467185")
    works = from_datex2(situation, territory="Finland")
    site = works.sites[0]
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.actual_start is None
    assert site.proposed_start is not None  # the date itself is still known, just unverified


def test_from_datex2_vegvesen_norway_pending_live_verification():
    """Norway (Vegvesen) - pending live verification, see
    streetworks.datex2.vegvesen. The fixture is real DATEX snapshotPull data
    from Iceland (IRCA), used only to confirm from_datex2 works unchanged
    against whatever the shared XML parser produces from a real
    SOAP-wrapped snapshotPull document - not a claim about Norway's own
    feed shape."""
    fixture = Path(__file__).parent / "fixtures" / "vegvesen_getsituation_sample.xml"
    situation = next(iter_situations(fixture))

    works = from_datex2(situation, territory="Norway")
    assert works.territory == "Norway"
    # No administrative_area passed - no confirmed source field yet (see
    # module docstring), so it falls back to source_name, which is None
    # here (the fixture's records carry no <source> element).
    assert works.administrative_area is None
    assert works.source_grade is SourceGrade.OPERATOR
    assert works.coordinate.crs == "EPSG:4326"
    assert len(works.sites) == 1
    # Regression check for the multilingual-comments bug fix (see
    # streetworks.datex2.parser._multilingual) - this real comment lists an
    # empty lang="en" placeholder before the real lang="is" text.
    assert works.sites[0].traffic_management == (
        "Unnið við endurbyggingu vegarins, hann er grófur, ósléttur og "
        "seinfarinn, akið mjög varlega. Þetta er vinnusvæði!!"
    )


def test_from_datex2_bisonfute_france():
    fixture = Path(__file__).parent / "fixtures" / "bisonfute_content.xml"
    situations = list(iter_situations_full(fixture))
    regions = bisonfute_dir_regions([s for s in situations if s.roadworks])
    situation = next(s for s in situations if s.id == "260122-001686")

    works = from_datex2(
        situation, territory="France", administrative_area=regions.get(situation.id)
    )
    assert works.territory == "France"
    assert works.administrative_area == "Direction interdépartementale des routes/DIR Sud-Ouest"
    assert works.source_grade is SourceGrade.OPERATOR
    # Real TPEG linear geometry (both endpoints) survives all the way
    # through to the common model, not just the first vertex.
    assert works.coordinate.points == ((42.92285, 0.68384415), (42.908493, 0.6984161))
    assert works.sites[0].coordinate.points == ((42.92285, 0.68384415), (42.908493, 0.6984161))


def test_from_datex2_dgt_spain():
    fixture = Path(__file__).parent / "fixtures" / "dgt_situations.xml"
    situations = list(iter_situations_full(fixture))
    regions = dgt_provinces([s for s in situations if s.roadworks])
    situation = next(s for s in situations if s.id == "2816645")

    works = from_datex2(situation, territory="Spain", administrative_area=regions.get(situation.id))
    assert works.territory == "Spain"
    assert works.administrative_area == "Toledo"
    assert works.source_grade is SourceGrade.OPERATOR
    assert works.promoter is None  # no sourceName on any real record, only sourceIdentification
    # roadName fallback (Spain never states roadNumber)
    assert works.sites[0].location_description == "N-400, unspecifiedCarriageway"
    # validityStatus was "active" on every real roadworks record fetched.
    assert works.sites[0].date_confidence is DateConfidence.VERIFIED

    # The situation with two roadworks records of different xsi:types
    # (SpeedManagement + RoadOrCarriagewayOrLaneManagement) both survive as
    # sites - the cause-based discriminator isn't limited to one xsi:type.
    mixed = next(s for s in situations if s.id == "14590355")
    mixed_works = from_datex2(mixed, territory="Spain")
    assert len(mixed_works.sites) == 2


def test_from_datex2_irca_iceland():
    fixture = Path(__file__).parent / "fixtures" / "irca_situations.xml"
    situation = next(s for s in iter_situations_full(fixture) if s.roadworks)

    works = from_datex2(situation, territory="Iceland")
    assert works.territory == "Iceland"
    # No administrative_area - checked exhaustively against the live feed,
    # no region/authority field exists there at all (see module docstring
    # in streetworks.datex2.irca).
    assert works.administrative_area is None
    assert works.promoter is None  # no <source> element on any record seen
    assert works.source_grade is SourceGrade.OPERATOR
    assert works.coordinate.crs == "EPSG:4326"
    # .raw is the Situation itself here (from_datex2 always sets this), which
    # in turn carries the source XML Element - iter_situations_full populates
    # it since Iceland's small response doesn't need streaming/clearing.
    assert works.sites[0].raw.raw is not None
    assert len(works.sites) == 1
