import unreal
pal = unreal.load_asset("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette")
entries = pal.get_editor_property("components") or []
print("[pc] count=%d" % len(entries))
for e in entries:
    fp = e.get_editor_property("footprint")
    print("[pc]   %-24s %2dx%2dx%-2d group=%s" % (str(e.get_editor_property("id")), fp.x, fp.y, fp.z, str(e.get_editor_property("material"))))
