"""Prepare inventory icons from the archived Godot inputs, preserving published UE artwork."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


PROJECT = Path(__file__).resolve().parents[2]
LIBRARY = PROJECT / "SourceAssets/LegacyGodotFPS"
GODOT = LIBRARY / "ui/InventoryReference"
CATALOG = PROJECT / "Content/ColdSteelData"
PUBLISHED_BOXES = {
    "assets/ui/icons/equip/ammo_556.png": LIBRARY / "PublishedInventoryIcons/ammo_556_green_box_v1.png",
    "assets/ui/icons/equip/ammo_762.png": LIBRARY / "PublishedInventoryIcons/ammo_762.png",
}


def normalized(path):
    return str(path).replace("\\", "/").casefold()


def replace_file(path, content, previous):
    """Publish complete bytes and leave a version edited during preparation alone."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        current = path.read_bytes() if path.exists() else None
        if current != previous:
            raise RuntimeError(f"Changed during inventory preparation: {path}")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare():
    if not GODOT.is_dir():
        raise FileNotFoundError(f"Missing recovered inventory inputs: {GODOT}")
    catalog_file = CATALOG / "items.json"
    manifest_file = CATALOG / "provenance.json"
    initial_catalog = catalog_file.read_bytes()
    initial_manifest = manifest_file.read_bytes() if manifest_file.exists() else None
    items = json.loads(initial_catalog)
    records = json.loads(initial_manifest) if initial_manifest is not None else []
    by_target = {normalized(row["target"]): row for row in records if "target" in row}
    catalog_changed = manifest_changed = False
    if "ue_m4a1" not in items and "fps_hk416" in items:
        items["ue_m4a1"] = dict(items["fps_hk416"], id="ue_m4a1", name="M4A1",
                                desc="当前 UE 第一人称 M4A1。使用 5.56mm 弹药。",
                                icon="res://assets/ui/icons/equip/fps_hk416.png")
        items["ue_m4a1"].pop("ue_icon", None)
        catalog_changed = True

    users = {}
    for definition in items.values():
        if definition.get("ue_icon"):
            users.setdefault(normalized(definition["ue_icon"]), set()).add(definition.get("icon"))

    refreshed = 0
    for key, item in items.items():
        icon = item.get("icon") or ""
        target = f"Icons/{key}.png"
        if not icon.startswith("res://") or not icon.lower().endswith(".png"):
            continue
        if item.get("ue_icon") and normalized(item["ue_icon"]) != normalized(target):
            continue
        resource = icon[6:]
        parts = resource.split("/")
        if any(part in ("", ".", "..") or "\\" in part or ":" in part for part in parts):
            raise ValueError(f"Invalid Godot icon reference for {key}: {icon}")
        if Path(key).name != key or ":" in key:
            raise ValueError(f"Invalid inventory icon id: {key}")
        # The game published its own artwork for these two item IDs.
        published_box = PUBLISHED_BOXES.get(resource) if Path(resource).stem == key else None
        source = published_box or GODOT / resource
        if not source.is_file():
            print(f"Source unavailable: {key} ({icon})")
            continue
        content = source.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        destination = CATALOG / target
        relative = destination.relative_to(PROJECT).as_posix()
        record = by_target.get(normalized(relative))
        existing = destination.read_bytes() if destination.exists() else None
        if users.get(normalized(target), set()) - {icon}:
            continue
        if existing != content:
            if not published_box and record and record.get("sha256") != checksum:
                if not normalized(record.get("source", "")).endswith("/" + normalized(resource)):
                    continue
            if existing is not None and (not record or hashlib.sha256(existing).hexdigest() != record.get("sha256")):
                continue
            if existing is None and not published_box and record and record.get("sha256") != checksum:
                continue
            replace_file(destination, content, existing)
            refreshed += 1
        if not item.get("ue_icon"):
            item["ue_icon"] = target
            catalog_changed = True
        if record is None:
            record = dict(source=str(source), target=relative, sha256=checksum)
            records.append(record)
            by_target[normalized(relative)] = record
            manifest_changed = True
        elif existing != content and record.get("sha256") != checksum:
            record.update(source=str(source), sha256=checksum)
            manifest_changed = True

    if manifest_changed:
        replace_file(manifest_file, json.dumps(records, ensure_ascii=False, indent=2).encode(), initial_manifest)
    if catalog_changed:
        replace_file(catalog_file, json.dumps(items, ensure_ascii=False, indent=2).encode(), initial_catalog)
    print(f"{len(items)} definitions; {refreshed} icon files written")


if __name__ == "__main__":
    prepare()
