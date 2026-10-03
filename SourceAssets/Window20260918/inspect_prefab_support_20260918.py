"""只读核对：构件（窗/门/喷泉）的承载关系与调色板条目，用于定位"拆掉支撑后构件浮空"。

在编辑器内远程执行（不修改任何资产、不写存档）：
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/Window20260918/inspect_prefab_support_20260918.py
"""

import unreal


CLASSES = [
    ("VoxelBuildWorld", unreal.VoxelBuildWorld),
    ("VoxelBuildPrefabActor", unreal.VoxelBuildPrefabActor),
    ("ColdSteelWindow", unreal.ColdSteelWindow),
    ("ColdSteelDoubleDoor", unreal.ColdSteelDoubleDoor),
    ("ColdSteelDoor", unreal.ColdSteelDoor),
    ("ColdSteelFountain", unreal.ColdSteelFountain),
]


def worlds():
    found = []
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        found.append(("editor", subsystem.get_editor_world()))
        found.append(("pie", subsystem.get_game_world()))
    except Exception as error:  # noqa: BLE001 - diagnostic script
        print("subsystem unavailable: %s" % error)
    return found


def actor_line(actor, kind):
    parts = ["loc=%s" % (actor.get_actor_location(),)]
    parent = actor.get_attach_parent_actor()
    parts.append("parent=%s" % (parent.get_name() if parent else "None"))
    if kind == "VoxelBuildPrefabActor":
        try:
            logic = actor.get_editor_property("LogicActor")
        except Exception:  # noqa: BLE001
            logic = None
        parts.append("logic=%s" % (logic.get_name() if logic else "None"))
        try:
            parts.append("mesh=%s" % (actor.get_editor_property("MeshComponent").get_editor_property("StaticMesh") or "None"))
        except Exception:  # noqa: BLE001
            pass
    return "%s  %s" % (actor.get_name(), "  ".join(parts))


def dump_world(tag, world):
    print("=" * 78)
    if not world:
        print("%s: (no world)" % tag)
        return
    print("%s world: %s" % (tag, world.get_name()))
    for kind, cls in CLASSES:
        try:
            actors = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
        except Exception as error:  # noqa: BLE001
            print("  %-22s query failed: %s" % (kind, error))
            continue
        print("  %-22s count=%d" % (kind, len(actors)))
        for actor in actors:
            print("      %s" % actor_line(actor, kind))
    for build_world in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.VoxelBuildWorld):
        try:
            print("  build world %s: blocks=%s prefabs=%s ready=%s"
                  % (build_world.get_name(), build_world.block_count(),
                     build_world.prefab_count(), build_world.is_ready()))
        except Exception as error:  # noqa: BLE001
            print("  build world %s: stats unavailable (%s)" % (build_world.get_name(), error))


def dump_palette():
    print("=" * 78)
    path = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
    asset = unreal.load_asset(path)
    if not asset:
        print("palette not loadable: %s" % path)
        return
    print("palette: %s" % asset.get_path_name())
    for entry in asset.get_editor_property("Components"):
        identifier = str(entry.get_editor_property("id"))
        if not any(key in identifier for key in ("window", "door", "torch")):
            continue
        print("  %-22s name=%-28s footprint=%s mount=%s actor=%s mesh=%s"
              % (identifier,
                 str(entry.get_editor_property("display_name")),
                 entry.get_editor_property("footprint"),
                 entry.get_editor_property("mount"),
                 entry.get_editor_property("actor_class"),
                 entry.get_editor_property("mesh")))


def main():
    for tag, world in worlds():
        dump_world(tag, world)
    dump_palette()


main()
