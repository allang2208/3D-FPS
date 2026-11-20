"""Switch only the wearing mesh, boot-specific cuffs and robe underlayers after saved assets exist."""
import json
import sys
from pathlib import Path

from field_pants_wear_publish import insert_fields
from ridge_boots_wear import BODIES, CONFIG, ITEM, P, ROBE, ROOT, WEAR, body_items, package_path, plan, read, sha, write
from shoulder_packages import write_revision

sys.path.insert(0, str(P / "Tools/BrownLeatherSet"))
from json_entries import span


def publish():
    saved, fits = read(ROOT / "wear-saved.json"), read(WEAR / "cuff-pairings.json")
    if not saved["complete"]:
        raise ValueError("The body-specific boots or robe variants are still being saved")
    rows = plan()
    before = CONFIG.read_bytes()
    cfg = json.loads(before)
    text = before.decode("utf-8-sig")
    edits = []
    report = {}
    for body, row in rows.items():
        item = saved["assets"][body]
        robe_item = saved["robe_assets"][body]
        if (sha(ROOT / row["source"]) != item["source_sha256"]
                or fits[body]["boot_source_sha256"] != item["source_sha256"]
                or item["source_sha256"] != robe_item["source_sha256"]
                or sha(package_path(row["asset"])) != item["package_sha256"]
                or sha(package_path(row["robe_asset"])) != robe_item["package_sha256"]):
            raise ValueError("Boot meshes, fit inputs or dressing assets changed for " + body)
        items = body_items(cfg, body)
        prefix = (*BODIES[body], "items")
        active = items[ITEM]["rig_meshes"][body]
        if active not in (row["previous"], row["asset"]) or items[ITEM]["rig_world_covers"][body] != row["cover_sections"]:
            raise ValueError("Another footwear revision is active on " + body)
        if active != row["asset"]:
            lo, hi = span(text, (*prefix, ITEM, "rig_meshes", body))
            edits.append((lo, hi, json.dumps(row["asset"])))
        pairs = fits[body]["pants"]
        if set(pairs) != {key for key, r in items.items() if r.get("slot") == 15}:
            raise ValueError("The choice of installed trousers changed for " + body)
        robe = items[ROBE]
        current_inners = robe["underlayer_meshes"]
        fallback = row["robe_pants"]
        if fallback != current_inners[pairs["ue_blue_mage_pants"]["asset"]]:
            raise ValueError("The matched mage-trouser underlayer changed")
        updates = [((*prefix, ROBE, "underlayer_meshes"), current_inners, row["asset"], row["robe_asset"]),
                   ((*prefix, ROBE, "pants_underlayer_default", "shoe_fit_meshes"),
                    robe["pants_underlayer_default"]["shoe_fit_meshes"], ITEM, {body: fallback})]
        equipped = {}
        for key, match in pairs.items():
            routes = items[key]["shoe_fit_meshes"]
            selected = match["asset"]
            prior = row["pants"][key]
            for key_fit, mesh in prior.items():
                if key_fit == "active":
                    current = routes.get(ITEM, {}).get(body)
                elif key_fit == "default":
                    current = items[key]["rig_meshes"][body]
                else:
                    current = routes.get(key_fit, {}).get(body)
                if current != mesh:
                    raise ValueError(f"Trouser cut changed for {body}/{key}/{key_fit}")
            if "active" not in prior and selected != prior["default"]:
                updates.append(((*prefix, key, "shoe_fit_meshes"), routes, ITEM, {body: selected}))
            equipped[key] = dict(trousers=selected, under_robe=current_inners.get(selected, fallback),
                                 cut=match["cut"])
        for path, mapping, name, value in updates:
            if name in mapping:
                if mapping[name] != value:
                    raise ValueError("Another revision owns " + str((*path, name)))
            else:
                edits.append(insert_fields(text, path, {name: value}))
        report[body] = dict(worn=row["asset"], under_robe=row["robe_asset"], paired_trousers=equipped,
                            no_trousers=row["asset"], native_cover_sections=row["cover_sections"])
    for lo, hi, replacement in sorted(edits, reverse=True):
        text = text[:lo] + replacement + text[hi:]
    after = (b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf8")
    if before != after:
        write_revision(CONFIG, before, after)
    write(ROOT / "wear-published.json", dict(config=CONFIG.relative_to(P).as_posix(), assets=saved["assets"],
        robe_assets=saved["robe_assets"], policy=saved["policy"], body_routes=report,
        cuff_pairings="Wear/cuff-pairings.json", gameplay_tested=False))


if __name__ == "__main__":
    publish()
