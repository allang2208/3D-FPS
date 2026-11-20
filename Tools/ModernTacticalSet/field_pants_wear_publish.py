"""Publish the new trouser meshes and exact shirt pairings in one scoped config edit."""
import json
from pathlib import Path
import sys

from field_pants_wear import BODIES, CONFIG, ITEM, P, ROOT, body_items, outfit_routes, package_path, plan, read, sha, write
from shoulder_packages import write_revision

sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import span


def insert_fields(text,path,entries):
    offset,_=span(text,path)
    start=text.rfind("\n",0,offset)+1
    indent=len(text[start:offset])-len(text[start:offset].lstrip())
    nl="\r\n" if "\r\n" in text else "\n"
    inner=json.dumps(entries,ensure_ascii=False,indent=2).splitlines()[1:-1]
    return offset+1,offset+1,nl+nl.join(" "*indent+line for line in inner)+","


def publish_config(before,work):
    doc=json.loads(before)
    text=before.decode("utf-8-sig")
    edits=[]
    report={}
    for body in BODIES:
        items=body_items(doc,body)
        prefix=(*BODIES[body],"items")
        pants=items[ITEM]
        routes=outfit_routes(pants,body)
        expected=work["body_routes"][body]
        if routes.keys()!=expected.keys():
            raise ValueError(f"{body} trouser or footwear recipes changed")
        for shoe,value in routes.items():
            record=work["assets"][expected[shoe]]
            if value not in (record["previous"],record["asset"]):
                raise ValueError(f"Another revision is active for {body}/{shoe}: {value}")
            if value!=record["asset"]:
                field=("rig_meshes",body) if shoe=="default" else ("shoe_fit_meshes",shoe,body)
                lo,hi=span(text,(*prefix,ITEM,*field))
                edits.append((lo,hi,json.dumps(record["asset"])))

        shoelist=[key for key,recipe in items.items() if recipe.get("slot")==13]
        wear={"no_footwear":expected["default"],**{shoe:expected.get(shoe,expected["default"]) for shoe in shoelist}}
        report[body]=dict(explicit_routes={shoe:work["assets"][key]["asset"] for shoe,key in expected.items()},
                          wear_states=wear,upper_body_fits={},robe_inner_meshes={})
        for key,recipe in items.items():
            if recipe.get("slot")!=7:
                continue
            # Preload and world/owner consumption all select by the exact fitted
            # trousers path first. Duplicate those keys before changing its recipe.
            for field in ("pants_mesh_fit_meshes","underlayer_meshes"):
                current=recipe.get(field,{})
                aliases={}
                matches={}
                for name in dict.fromkeys(expected.values()):
                    record=work["assets"][name]
                    old,new=record["previous"],record["asset"]
                    if old not in current:
                        continue
                    value=current[old]
                    if new in current and current[new]!=value:
                        raise ValueError(f"Conflicting {key} {field} on {body}: {new}")
                    matches[name]=value
                    if new not in current:
                        aliases[new]=value
                if aliases:
                    edits.append(insert_fields(text,(*prefix,key,field),aliases))
                if field=="pants_mesh_fit_meshes" and matches:
                    report[body]["upper_body_fits"][key]=matches
            if "pants_underlayer_default" in recipe:
                inner=recipe["pants_underlayer_default"]
                mapping=recipe.get("underlayer_meshes",{})
                report[body]["robe_inner_meshes"][key]={}
                for shoe,name in wear.items():
                    old=work["assets"][name]["previous"]
                    inner_mesh=mapping.get(old,inner.get("shoe_fit_meshes",{}).get(shoe,{}).get(body) or inner["rig_meshes"][body])
                    report[body]["robe_inner_meshes"][key][shoe]=inner_mesh
    for lo,hi,value in sorted(edits,reverse=True):
        text=text[:lo]+value+text[hi:]
    bom=b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b""
    return bom+text.encode("utf8"),report


def main():
    work=plan()
    saved=read(ROOT/"wear-saved.json")
    if not saved["complete"] or work["assets"].keys()!=saved["assets"].keys():
        raise RuntimeError("The selected field trousers are still being authored or saved")
    if sha(package_path(saved["policy"]["asset"]))!=saved["policy"]["sha256"]:
        raise RuntimeError("The trouser LOD policy changed after production")
    from field_pants_wear_waist import main as resolve_waists
    resolve_waists()
    waists=read(ROOT/"Wear/waist-interfaces.json")["assets"]
    for name,row in saved["assets"].items():
        if (sha(ROOT/row["source_file"])!=row["source_sha256"] or
            sha(package_path(row["asset"]))!=row["package_sha256"] or
            row["asset"]!=work["assets"][name]["asset"]):
            raise RuntimeError("Changed trouser package or sewing pattern: "+name)
        ring=waists[name]
        # The fitted shirt sits several millimetres inside the waistband.
        # Sewing below it can shift the barycentric hit at its lowest row
        # by hundredths of a millimetre while preserving the same contact.
        if ring["source_sha256"]!=row["source_sha256"] or ring["missing"] or ring["peak_offset_mm"]>.1 or ring["peak_influence_delta"]>.001:
            raise RuntimeError("Cannot reuse the existing tailored upper on a changed waistband: "+name)
    before=CONFIG.read_bytes()
    after,details=publish_config(before,work)
    if before!=after:
        write_revision(CONFIG,before,after)
    write(ROOT/"wear-published.json",dict(config=CONFIG.relative_to(P).as_posix(),assets=saved["assets"],
        policy=saved["policy"],waist_interfaces="Wear/waist-interfaces.json",body_routes=details,gameplay_tested=False))
    print("FIELD_TROUSERS_WEAR_PUBLISHED",len(saved["assets"]),
          {k:sum(map(len,v["upper_body_fits"].values())) for k,v in details.items()},flush=True)


if __name__=="__main__":
    main()
