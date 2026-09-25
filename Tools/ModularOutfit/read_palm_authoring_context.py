import unreal as u
print('PALM_AUTHORING_CONTEXT',u.Paths.project_dir(),'playing',bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()))
for cls,names in ((u.GeometryScript_MeshEdits,['append_mesh']),
 (u.GeometryScript_Materials,['delete_triangles_by_material_id','remap_material_i_ds']),
 (u.SkeletalMeshEditorSubsystem,['get_lod_count','get_lod_build_settings','set_lod_build_settings'])):
    for name in names:print(name,getattr(cls,name).__doc__)
print(u.GeometryScriptAppendMeshOptions.__doc__)
