"""Pull several reporting datasets concurrently with the async client."""

import asyncio
import os

from streetworks.streetmanager import AsyncStreetManagerClient


async def main() -> None:
    async with AsyncStreetManagerClient(os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"]) as sm:
        permits, inspections, fpns = await asyncio.gather(
            sm.reporting.permits(status="submitted"),
            sm.reporting.inspections(),
            sm.reporting.fixed_penalty_notices(status="disputed"),
        )
        print(len(permits.get("rows", [])), "submitted permits")
        print(len(inspections.get("rows", [])), "inspections")
        print(len(fpns.get("rows", [])), "disputed FPNs")

        # For complete result sets, let the SDK walk every page:
        total = 0
        async for _permit in sm.reporting.iter_permits(status="submitted"):
            total += 1
        print(total, "submitted permits across all pages")


if __name__ == "__main__":
    asyncio.run(main())
