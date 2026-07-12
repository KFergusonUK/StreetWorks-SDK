"""Consume the Scottish Road Works Register Open Data feed.

No credentials required - the SRWR publishes its full noticing data daily
under the Open Government Licence v3.

Run: python examples/srwr_opendata.py
"""

from streetworks.srwr import SRWRClient, describe

with SRWRClient() as srwr:
    # The /daily endpoint always holds the latest daily extract (a few MB).
    archive = srwr.download_daily("srwr-daily.zip")

    road_closures = 0
    for activity in srwr.iter_activities(archive):
        record = activity.activity
        for phase in activity.phases:
            status = describe("activity_status", phase.activity_status)
            works = describe("works_type", phase.works_type)
            print(
                f"{activity.activity_id} {record.activity_reference}: "
                f"{works} - {status} @ {phase.location}"
            )
        for up in activity.undertaker_phases:
            if (
                up.traffic_management_type
                and describe("traffic_management_type", up.traffic_management_type)
                == "Road Closure"
            ):
                road_closures += 1

    print(f"\n{road_closures} phases involve a full road closure")

# Monthly/yearly archives concatenate daily extracts, so an activity appears
# once per day it changed; latest_activities() applies the spec's
# "most recent occurrence wins" rule:
#
#     archive = srwr.download_archive("JUN.zip", "srwr-june.zip")
#     for activity in srwr.latest_activities(archive):
#         ...
