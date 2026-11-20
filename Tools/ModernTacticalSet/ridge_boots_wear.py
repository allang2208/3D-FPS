"""Resolve body-specific footwear, trouser cuffs and the existing robe inner-layer rules."""
from pathlib import Path

from field_pants_wear import BASE, BODIES, CONFIG, P, SET, body_items, package_path, read, sha, write


REV = "RidgeBootsR2"
ROOT = SET / REV
WEAR = ROOT / "Wear"
DEST = BASE + "/" + REV
ITEM = "ue_modern_tactical_boots"
TROUSERS = "ue_modern_tactical_pants"
ROBE = "ue_blue_mage_robe"
SLOTS = ("RB_Suede", "RB_Textile", "RB_Frame", "RB_Outsole", "RB_Lace", "RB_Lining", "RB_Hardware", "RB_Thread")


def plan():
    output = WEAR / "plan.json"
    if output.exists():
        return read(output)
    cfg = read(CONFIG)
    authored = {row["asset"]: row for row in read(SET / "CombatShirtR4/authored.json")["rows"]
                if row.get("kind") == "boots"}
    result = {}
    for body in BODIES:
        items = body_items(cfg, body)
        previous = items[ITEM]["rig_meshes"][body]
        donor = Path(authored[previous.split(".")[0]]["file"])
        stem = f"SK_TS01_RidgeBoots_{body}"
        folder = f"{DEST}/Wear/{body}"
        pants = {}
        for key, item in items.items():
            if item.get("slot") != 15:
                continue
            routes = item.get("shoe_fit_meshes", {})
            if ITEM in routes:
                pants[key] = {"active": routes[ITEM][body]}
            else:
                pants[key] = {"default": item["rig_meshes"][body],
                              **{shoe: routes[shoe][body] for shoe in ("ue_boots", "ue_armored_boots")
                                 if body in routes.get(shoe, {})}}
        # The robe's fitted mage trousers already use the same cuff when these
        # boots are worn. Its exact mesh supplies the appropriate fallback.
        robe = items[ROBE]
        mage_cuff = pants["ue_blue_mage_pants"]["active"]
        robe_pants = robe["underlayer_meshes"][mage_cuff]
        result[body] = dict(body=body, previous=previous, donor_source=donor.relative_to(SET).as_posix(),
            donor_sha256=sha(package_path(previous)), source=f"Authored/boots_{body}.json",
            asset=f"{folder}/{stem}.{stem}", robe_asset=f"{folder}/{stem}_RobeHem.{stem}_RobeHem",
            robe_pants=robe_pants, pants=pants, cover_sections=items[ITEM]["rig_world_covers"][body])
    write(output, result)
    return result


if __name__ == "__main__":
    plan()
