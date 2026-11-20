"""Native TS01 trousers selected by the live normal and footwear recipes."""
import json
from pathlib import Path

from coyote_glove_wear import package_path, sha, write


P = Path(__file__).resolve().parents[2]
SET = P / "SourceAssets/ModernTacticalSet20261113"
REV = "FieldTrousersR2"
ROOT = SET / REV
BASE = "/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113"
DEST = BASE + "/" + REV
CONFIG = P / "Content/ColdSteelData/modular_outfits.json"
ITEM = "ue_modern_tactical_pants"
BODIES = {"Jason": (), "Kaitlin": ("body_variants","kaitlin")}


def read(path):
    return json.loads(Path(path).read_bytes())


def body_items(data,body):
    for key in BODIES[body]:
        data = data[key]
    return data["items"]


def outfit_routes(recipe,body):
    return {"default":recipe["rig_meshes"][body],
            **{shoe:entry[body] for shoe,entry in recipe.get("shoe_fit_meshes",{}).items() if body in entry}}


def plan():
    path=ROOT/"Wear/plan.json"
    if path.is_file():
        return read(path)
    current=read(CONFIG)
    authored=read(SET/"CombatShirtR4/authored.json")["rows"]
    old_sources={row["asset"]:Path(row["file"]) for row in authored if (row.get("kind") or "").startswith("pants")}
    assets={}
    route_map={}
    for body in BODIES:
        recipe=body_items(current,body)[ITEM]
        routes=outfit_routes(recipe,body)
        route_map[body]={}
        for fit,old in routes.items():
            package=old.split(".")[0]
            if package not in old_sources or not package.startswith(f"{BASE}/CombatShirtR4/Wear/{body}/SK_TS01_pants"):
                raise ValueError(f"Unrecognised native trousers in {body}/{fit}: {old}")
            name=package.rsplit("/",1)[1].removeprefix("SK_TS01_")
            route_map[body][fit]=name
            if name in assets:
                continue
            new_name="SK_TS01_FieldTrousers"+name.removeprefix("pants")
            asset=f"{DEST}/Wear/{body}/{new_name}.{new_name}"
            source=old_sources[package]
            assets[name]=dict(body=body,previous=old,asset=asset,
                              donor_source=source.relative_to(SET).as_posix(),donor_source_sha256=sha(source),
                              donor_sha256=sha(package_path(old)),source="Authored/"+name+".json")
    result=dict(assets=assets,body_routes=route_map)
    write(path,result)
    return result


if __name__=="__main__":
    work=plan()
    print("FIELD_TROUSERS_INPUTS",len(work["assets"]),{k:len(v) for k,v in work["body_routes"].items()})
