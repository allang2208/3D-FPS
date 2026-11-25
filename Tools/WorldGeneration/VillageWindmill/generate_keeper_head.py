"""Submit or resume the approved mill keeper head on Meshy's multi-image endpoint."""
import base64
import hashlib
import ipaddress
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "Tools/VillageHerbalist"))
import meshy_asset as pipeline

ROOT = PROJECT / "SourceAssets/HillsVillageWindmill/MillKeeper"
OUT = ROOT / "CharacterR1/MeshyHead"
VIEWS = ("01_front.png", "02_three_quarter.png", "03_profile.png")

class MeshyAddressAdapter(requests.adapters.HTTPAdapter):
    """Optional per-process DNS override. TLS still authenticates api.meshy.ai."""
    def __init__(self, address):
        self.address = str(ipaddress.IPv4Address(address))
        super().__init__()

    def proxy_manager_for(self, proxy, **kwargs):
        return super().proxy_manager_for(proxy, assert_hostname="api.meshy.ai",
                                         server_hostname="api.meshy.ai", **kwargs)

    def send(self, request, **kwargs):
        original = request.url
        request.headers["Host"] = "api.meshy.ai"
        request.url = original.replace("://api.meshy.ai/", "://" + self.address + "/", 1)
        try:
            return super().send(request, **kwargs)
        finally:
            request.url = original


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = pipeline.transfer.credentials()
    if not key:
        raise SystemExit("Meshy credential required")
    views, inputs = [], []
    for name in VIEWS:
        raw = (ROOT / "Head/ConceptR1/Views" / name).read_bytes()
        inputs.append({"view": name, "sha256": hashlib.sha256(raw).hexdigest()})
        views.append("data:image/png;base64," + base64.b64encode(raw).decode("ascii"))
    params = dict(pipeline.SETTINGS, ai_model="meshy-7.1", target_polycount=64000, target_formats=["glb"])
    manifest = {"endpoint": pipeline.transfer.API, "parameters": params, "inputs": inputs}
    if (OUT / "task.json").exists() and json.loads((OUT / "request.json").read_text()) != manifest:
        raise RuntimeError("Existing generation uses different inputs")
    pipeline.save(OUT, "request.json", manifest)
    with pipeline.transfer.session() as api:
        if address := os.environ.get("MESHY_API_CONNECT_IP"):
            api.mount("https://api.meshy.ai/", MeshyAddressAdapter(address))
        api.headers["Authorization"] = "Bearer " + key
        task_id, result = pipeline.submit_and_wait(api, OUT, pipeline.transfer.API,
            dict(params, image_urls=views, texture_image_urls=views))
    entries = [(f"Textures/M{i}_{channel}{Path(urlsplit(url).path).suffix}", url)
               for i, maps in enumerate(result.get("texture_urls") or []) for channel, url in maps.items() if url]
    entries.append(("head.glb", result["model_urls"]["glb"]))
    pipeline.download(OUT, task_id, result, entries)


if __name__ == "__main__":
    main()
