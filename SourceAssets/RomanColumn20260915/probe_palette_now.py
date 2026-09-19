import unreal

pal = unreal.load_asset("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette")
print("[pp] palette loadable:", pal is not None)
for e in (pal.get_editor_property("components") or []):
    mesh = e.get_editor_property("mesh")
    surf = e.get_editor_property("surface")
    print("[pp] %-24s group=%-8s surf=%-20s mesh=%s" % (
        str(e.get_editor_property("id")), str(e.get_editor_property("material")),
        surf.get_path_name().split(".")[-1] if surf else "None",
        mesh.get_name() if mesh else "None"))
print("[pp] marble material row:", [str(m.get_editor_property("id")) for m in (pal.get_editor_property("materials") or [])])

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
print("[pp] map=%s" % world.get_name())
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if "avilion" in label or "Pavilion" in label:
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
        mesh = comps[0].get_editor_property("static_mesh").get_name() if comps and comps[0].get_editor_property("static_mesh") else "?"
        print("[pp] map actor %-26s mesh=%s" % (label, mesh))
