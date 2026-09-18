"""Probe 8 (user asked): water material inventory + M_Water_Opaque parameters + GS primitives API."""

import unreal

# 1) full water-material inventory grouped by pack
reg = unreal.AssetRegistryHelpers.get_asset_registry()
mats = reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Material"), True)
groups = {}
for a in mats:
    nm = str(a.package_name)
    low = nm.lower()
    if any(k in low for k in ("water", "lake", "ocean", "river", "puddle", "splash")):
        pack = "/".join(nm.split("/")[:3])
        groups.setdefault(pack, []).append(nm)
total = sum(len(v) for v in groups.values())
print("[inv] water-ish materials total=%d in %d packs" % (total, len(groups)))
for pack in sorted(groups, key=lambda p: -len(groups[p])):
    print("[inv] %s (%d)" % (pack, len(groups[pack])))
    for n in groups[pack][:12]:
        print("[inv]    ", n)
    if len(groups[pack]) > 12:
        print("[inv]    ... +%d more" % (len(groups[pack]) - 12))

# 2) instances/MICs too (they may be the actually-assignable variants)
mics = reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "MaterialInstanceConstant"), True)
w_mics = [str(a.package_name) for a in mics
          if any(k in str(a.package_name).lower() for k in ("water", "river", "lake", "ocean"))]
print("[inv] water MICs=%d" % len(w_mics))
for n in w_mics[:20]:
    print("[inv]    ", n)

# 3) what does M_Water_Opaque expose?
for path in ("/Game/WaterMaterials/Materials/M_Water_Opaque", "/Game/WaterMaterials/Materials/M_Water_Clean"):
    m = unreal.load_asset(path)
    if not m:
        print("[par] %s NOT LOADABLE" % path)
        continue
    print("[par] %s  blend=%s" % (path, m.get_editor_property("blend_mode")))
    for prop in ("vector_parameter_values", "scalar_parameter_values"):
        try:
            arr = m.get_editor_property(prop)
            names = []
            for p in arr:
                names.append(str(p.get_editor_property("parameter_name")))
            print("[par]   %s: %s" % (prop, names))
        except Exception as exc:  # noqa: BLE001
            print("[par]   %s read failed: %s" % (prop, exc))

# 4) GS primitives available for the socle append
prim = [n for n in dir(unreal.GeometryScript_Primitives) if not n.startswith("_")]
print("[gs] Primitives: %s" % sorted(prim))
print("[gs] con signatures:")
for fn in ("append_cone", "append_cylinder", "append_disc"):
    f = getattr(unreal.GeometryScript_Primitives, fn, None)
    if f:
        print("[gs] --- %s%s" % (fn, getattr(f, "__doc__", "") or ""))

# 5) world state (screenshot needs non-PIE)
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    w = sub.get_editor_world() if sub else None
    print("[st] world=%s PIE=%s" % (w.get_path_name() if w else None,
                                    les.is_in_play_in_editor() if les else None))
except Exception as exc:  # noqa: BLE001
    print("[st] state probe failed: %s" % exc)
print("[st] DONE")
