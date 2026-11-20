"""Read the saved reference-shell LODs against both captured native heads and hairstyles."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
import helmet_nape_clearance as native

native.R=native.S/"ExfilReferenceR4"
rows={rig:[native.review(rig,i) for i in range(3)] for rig in ("Jason","Kaitlin")}
(native.R/"Review/hair-clearance.json").write_text(json.dumps(dict(rigs=rows,
    scope="Native rest pose; render LODs read from saved UE assets. The open rim is reported separately."),indent=2))
