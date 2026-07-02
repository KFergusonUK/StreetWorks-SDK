"""A complete Street Manager Open Data receiver using FastAPI.

Run:  pip install fastapi uvicorn "streetworks[sns]"
      uvicorn opendata_fastapi:app --host 0.0.0.0 --port 8443

Point your Street Manager Open Data subscription at this endpoint (HTTPS is
required in production - terminate TLS in front of uvicorn).
"""

import os

from fastapi import FastAPI, Request, Response

from streetworks.exceptions import SignatureVerificationError
from streetworks.opendata import EventNotification, handle

app = FastAPI()
TOPIC_ARN = os.environ.get("SM_TOPIC_ARN")  # optional but recommended


@app.post("/street-manager/events")
async def receive(request: Request) -> Response:
    body = await request.body()
    try:
        payload = handle(body, verify=True, expected_topic_arn=TOPIC_ARN)
    except SignatureVerificationError:
        return Response(status_code=403)

    if payload is None:  # subscription handshake - already confirmed
        return Response(status_code=200)

    event = EventNotification.model_validate(payload)
    print(f"{event.event_type}: {event.object_type} {event.object_reference}")
    # ...persist / queue / react here...
    return Response(status_code=200)
