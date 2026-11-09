"""Update the M249 workbench recipe and its material indices without replacing other entries."""
from pathlib import Path
import json
import os
import re
import tempfile

root=Path(__file__).resolve().parents[1]
data=root.parents[1]/"Content/ColdSteelData"
def replace(file,pattern,update):
    path=data/file
    before=path.read_bytes()
    text=before.decode("utf-8-sig")
    matches=list(re.finditer(pattern,text))
    if not matches:raise RuntimeError("M249 entry missing in "+file)
    for match in reversed(matches):
        start=match.start("entry")
        original,count=json.JSONDecoder().raw_decode(text[start:])
        indent=len(text[text.rfind("\n",0,start)+1:start])
        replacement=json.dumps(update(original),ensure_ascii=False,indent=2).replace("\n","\n"+" "*indent)
        # Existing catalogues use an indented key before nested values.
        if file=="modular_outfits.json":
            line=text[text.rfind("\n",0,start)+1:start]
            padding=len(line)-len(line.lstrip())
            replacement=json.dumps(update(original),ensure_ascii=False,indent=2).replace("\n","\n"+" "*padding)
        text=text[:start]+replacement+text[start+count:]
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as handle:
        temp=Path(handle.name);handle.write(text.encode("utf-8-sig" if before.startswith(b"\xef\xbb\xbf") else "utf8"))
    if path.read_bytes()!=before:temp.unlink();raise RuntimeError("Concurrent catalog edit")
    os.replace(temp,path)

recipe=json.loads((root/"assembly.json").read_text(encoding="utf8"))
replace("gun-assembly.json",r'(?P<entry>\{\s*"id":\s*"assemble_m249",)',lambda old:recipe)
slots=json.loads((root/"assets_saved.json").read_text())["skin_slots"]
replace("modular_outfits.json",r'"/Game/Weapons/M249/SK_M249_V7.SK_M249_V7":\s*(?P<entry>\{)',
        lambda old:{**old,"hide_source_materials":slots})
print("M249_REPAIR02_CATALOG",len(recipe["parts"])+1,slots)
