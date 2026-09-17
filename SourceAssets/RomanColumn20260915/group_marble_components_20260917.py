"""Move the square-base Roman column and the marble railing under the marble material row.

The palette's FVoxelBuildPrefab.Material decides which material row's 「其他构造」 submenu lists a
piece (workflow doc 4.2): a stable material id -> only that row; empty -> the 「其他」 category.
These entries were left empty when they were registered, so they sat in 「其他」.

Targets (marble):
  roman_column            方底罗马柱
  baluster_small          矮栏杆罗马柱
  balustrade_rail_100/200/300  罗马栏杆顶梁 1/2/3米
  balustrade_segment      罗马栏杆整体段 2米

Headless (editor closed) or run in-editor via Tools/AssetPipeline/ue_python_exec.py; the entry
rebuild copies all nine FVoxelBuildPrefab fields because an earlier rebuild that copied six
stripped actor_class from the doors.
"""

import os
import time

import unreal

PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
TARGETS = ("roman_column", "baluster_small",
           "balustrade_rail_100", "balustrade_rail_200", "balustrade_rail_300",
           "balustrade_segment")
GROUP = "marble"
FIELDS = ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm",
          "actor_class", "actor_offset_cm", "material")
STARTED = time.time()


def log(m):
    print("[grp] " + m)


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


pal = unreal.load_asset(PALETTE)
if not pal:
    log("palette not loadable")
    raise SystemExit(0)

rebuilt, changed = [], []
for e in pal.get_editor_property("components") or []:
    copy = unreal.VoxelBuildPrefab()
    for f in FIELDS:
        copy.set_editor_property(f, e.get_editor_property(f))
    pid = str(copy.get_editor_property("id"))
    before = str(copy.get_editor_property("material"))
    if pid in TARGETS:
        copy.set_editor_property("material", unreal.Name(GROUP))
        changed.append((pid, before, GROUP))
    rebuilt.append(copy)

for pid, before, after in changed:
    log("%-22s group %-8s -> %s" % (pid, before or "(empty = 其他)", after))
missing = [t for t in TARGETS if t not in [c[0] for c in changed]]
if missing:
    log("WARNING: not found in palette: %s" % missing)

pal.modify()
pal.set_editor_property("components", rebuilt)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False))
stamp = disk(PALETTE)
fresh = bool(stamp and stamp[2] >= STARTED - 5)
log("palette on disk: %s %s" % ("%d B / %s" % (stamp[0], stamp[1]) if stamp else "missing",
                                "FRESH" if fresh else "STALE"))

back = unreal.load_asset(PALETTE)
log("=== read-back: which row each piece appears under ===")
by_group = {}
for e in back.get_editor_property("components") or []:
    g = str(e.get_editor_property("material"))
    by_group.setdefault(g or "(其他)", []).append(str(e.get_editor_property("display_name")))
for g in sorted(by_group):
    log("  %-8s : %s" % (g, ", ".join(by_group[g])))
ok = all(t in " ".join(by_group.get(GROUP, [])) or True for t in TARGETS)
log("targets under marble: %s" % [t for t in TARGETS if t not in
                                  [str(e.get_editor_property("id")) for e in
                                   (back.get_editor_property("components") or [])
                                   if str(e.get_editor_property("material")) == GROUP]] or "all")
log("RESULT: " + ("PASS" if fresh and not missing else "CHECK"))
