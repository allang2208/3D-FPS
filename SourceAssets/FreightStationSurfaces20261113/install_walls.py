from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightStationSurfaces20261113'
E=u.EditorAssetLibrary
def import_mesh(name):
    directory=BASE+'/Meshes';path=directory+'/'+name
    if E.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(ROOT/'Meshes'/(name+'.fbx'));task.destination_path=directory;task.destination_name=name;task.automated=True;task.save=False
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_as_skeletal=False;opts.import_mesh=True;opts.import_textures=False;opts.import_materials=False
    d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.convert_scene=True;d.convert_scene_unit=True;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opts;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Mesh import failed '+name)
    return obj
def apply(w):
    manifest=json.loads((ROOT/'wall-sections.json').read_text('utf8'))
    mat=u.load_asset('/Game/SceneTests/FreightCartUpperWall20261113/Materials/M_CastBayConcrete')
    if not mat:raise RuntimeError('Approved material missing')
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    for name,pos in manifest['locations'].items():
        mesh=import_mesh(name);mesh.modify();mesh.set_material(0,mat)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+name)
        label='StationSurface_'+name[10:]
        a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos),u.Rotator())
            a.set_actor_label(label);a.set_folder_path('StationLine/StationSurface/Concrete')
        c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh)
        c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False)
        c.set_cast_shadow(False);c.set_editor_property('receives_decals',True)
    return dict(section_meshes=len(manifest['locations']),areas=manifest['areas'],material=mat.get_path_name())
