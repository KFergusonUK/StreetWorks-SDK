"""Look up any GB street by USRN with geometry - no credentials required.

OS Open USRN is Ordnance Survey OpenData (OGL v3): every Unique Street
Reference Number in Great Britain with a simplified street geometry in
British National Grid (EPSG:27700) - the same USRNs referenced by Street
Manager works, DataVIA streets, D-TRO regulated places and SRWR activities.

Run: python examples/openusrn_lookup.py
"""

from streetworks.openusrn import OpenUSRNClient, UsrnDatabase, extract_gpkg

with OpenUSRNClient() as client:
    info = client.product_info()
    print(info.get("name"), "-", info.get("version"))

    # ~300 MB, streamed to disk (do this once, then reuse the file)
    archive = client.download("osopenusrn.zip")

gpkg = extract_gpkg(archive)

with UsrnDatabase(gpkg) as db:
    print(f"{db.count():,} USRNs in Great Britain")

    street = db.get(33909869)  # a real Durham USRN
    if street:
        print(f"USRN {street.usrn}: {street.geometry[:80]}...")
