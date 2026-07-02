"""Consume from the D-TRO service: recent events, then fetch each D-TRO."""

import os

from streetworks.dtro import DTROClient, Environment

with DTROClient(
    os.environ["DTRO_CLIENT_ID"],
    os.environ["DTRO_CLIENT_SECRET"],
    app_id=os.environ.get("DTRO_APP_ID"),
    environment=Environment.INTEGRATION,
) as dtro:
    events = dtro.search_events(since="2026-06-01T00:00:00", page=1, pageSize=50)
    print(events.get("totalCount"), "events since June")

    for event in events.get("events", []):
        record = dtro.get_dtro(event["id"])
        print(event["eventType"], "-", record.get("data", {}).get("source", {}).get("troName"))

    # Or grab everything as CSV via a signed URL (valid 60 minutes)
    print(dtro.get_all_dtros_url())
