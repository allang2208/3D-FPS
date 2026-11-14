"""Add an uncollidable scanned skim coat within the previously installed dado extents."""
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;BASE='/Game/SceneTests/FreightCartUpperWall20261113'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
def import_asset(name,is_mesh=False):
    folder=BASE+('/Meshes' if is_mesh else '/Textures');path=folder+'/'+name
    existing=u.load_asset(path) if E.does_asset_exist(path) else None
    if existing:return existing
    task=u.AssetImportTask();task.filename=str(ROOT/(name+('.fbx' if is_mesh else '.png')));task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False
    if is_mesh:
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opts.import_as_skeletal=False;opts.import_mesh=True;opts.import_textures=False;opts.import_materials=False
        d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
        d.convert_scene=True;d.convert_scene_unit=True;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=opts;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Cannot import '+name)
    if not is_mesh:
        compression={'Color':u.TextureCompressionSettings.TC_DEFAULT,'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'ORM':u.TextureCompressionSettings.TC_MASKS}[name.split('_')[-1]]
        obj.modify();obj.set_editor_property('compression_settings',compression);obj.set_editor_property('srgb',name.endswith('_Color'))
        obj.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);obj.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+name)
    return obj
def material():
    path=BASE+'/Materials/M_CastBayConcrete'
    if E.does_asset_exist(path):return u.load_asset(path)
    m=u.AssetToolsHelpers.get_asset_tools().create_asset('M_CastBayConcrete',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Cannot create mineral material')
    for key,kind,props in [('Color',u.MaterialSamplerType.SAMPLERTYPE_COLOR,[('RGB','BASE_COLOR')]),
                            ('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,[('RGB','NORMAL')]),
                            ('ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS,[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')])]:
        tex=import_asset('T_CastBay_'+key)
        node=L.create_material_expression(m,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',tex);node.set_editor_property('sampler_type',kind)
        for pin,prop in props:
            if not L.connect_material_property(node,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(m,False):raise RuntimeError('Material not saved')
    return m
def apply(w,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    dado=actors['CartBay_ConcreteDadoAndCoping']
    p=dado.get_actor_location()
    if abs(p.x-8317)>.01 or abs(p.y+332)>.01:raise RuntimeError('Dado position changed')
    if row.get('load_only'):
        mesh=u.load_asset(BASE+'/Meshes/SM_CastBayFace');m=u.load_asset(BASE+'/Materials/M_CastBayConcrete')
    else:
        mesh=import_asset('SM_CastBayFace',True);m=material()
    if not mesh or not m:raise RuntimeError('Missing upper wall assets')
    if not row.get('load_only'):
        mesh.modify();mesh.set_material(0,m)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save finish mesh')
    label='CartBay_CastUpperFace';actor=actors.get(label)
    if not actor:
        api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        actor=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(p.x,p.y,0),u.Rotator())
        actor.set_actor_label(label);actor.set_folder_path('StationLine/ReferenceSurfaceStudy/CartBay')
    c=actor.static_mesh_component;c.modify();c.set_static_mesh(mesh);c.set_material(0,m)
    c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False)
    c.set_cast_shadow(True);c.set_editor_property('receives_decals',True)
