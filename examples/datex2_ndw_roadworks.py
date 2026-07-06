"""European roadworks via DATEX II - the Netherlands' open NDW feed.

DATEX II is the European standard for traffic and roadworks data. NDW
publishes the Dutch national planned-works feed credential-free; this
example downloads it and walks the roadworks.

Run: python examples/datex2_ndw_roadworks.py
"""

from streetworks.datex2 import NDWClient, iter_roadworks

with NDWClient() as ndw:
    feed = ndw.download_planned_works("ndw-planned.xml.gz")   # ~15 MB

urgent = 0
for situation in iter_roadworks(feed):
    for works in situation.roadworks:
        if works.urgent:
            urgent += 1
        # A fully-typed record: who, what, when, where
        if works.location.point and works.comments:
            lat, lon = works.location.point
            print(f"{situation.id}: {works.record_type} by {works.source_name}")
            print(f"  {works.comments[0][:70]}")
            print(f"  {works.validity.overall_start} -> {works.validity.overall_end}")
            print(f"  @ ({lat}, {lon})  delay: {works.impact_delay_band}")
            break
    else:
        continue
    break

count = sum(1 for _ in iter_roadworks(feed))
print(f"\n{count:,} roadworks situations in the Dutch national feed ({urgent} urgent)")

# Note: DATEX II coordinates are WGS84 latitude/longitude - not the British
# National Grid eastings/northings used by the UK providers in this SDK.
