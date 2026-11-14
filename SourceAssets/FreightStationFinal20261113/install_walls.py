"""Install new finish assets without editing original station wall/floor material slots."""
from pathlib import Path
import json,runpy
import unreal as u
R=Path(__file__).resolve().parent;BASE='/Game/SceneTests/FreightStationFinal20261113'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;T=u.AssetToolsHelpers.get_asset_tools()
import_mesh=runpy.run_path(str(R.parent/'FreightStationSurfaces20261113/install_walls.py'))['import_mesh']
import_mesh.__globals__.update(ROOT=R,BASE=BASE)
def master():
    path=BASE+'/Materials/M_StationMineral'
    if E.does_asset_exist(path):return u.load_asset(path)
    mat=T.create_asset('M_StationMineral',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    for suffix,sampler,pins in [('Color','SAMPLERTYPE_COLOR',[('RGB','BASE_COLOR')]),('Normal','SAMPLERTYPE_NORMAL',[('RGB','NORMAL')]),('ORM','SAMPLERTYPE_MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')])]:
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property('parameter_name',suffix)
        # Compatible defaults use the approved opposite-wall scan textures.
        node.set_editor_property('texture',u.load_asset('/Game/SceneTests/FreightOppositePlatform20261113/Textures/T_Return_'+suffix))
        node.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,sampler))
        for pin,prop in pins:L.connect_material_property(node,pin,getattr(u.MaterialProperty,'MP_'+prop))
    if L.recompile_material(mat) or not E.save_loaded_asset(mat,False):raise RuntimeError('Master save')
    return mat
def material(key,parent):
    path=BASE+'/Materials/MI_'+key
    if E.does_asset_exist(path):return u.load_asset(path)
    textures=[]
    for suffix in ['Color','Normal','ORM']:
        name='T_'+key+'_'+suffix
        t=u.AssetImportTask();t.filename=str(R/'Textures'/(name+'.png'));t.destination_path=BASE+'/Textures';t.destination_name=name;t.automated=True;t.save=False
        T.import_asset_tasks([t]);tex=u.load_asset(BASE+'/Textures/'+name)
        if not tex:raise RuntimeError(name)
        tex.modify();tex.set_editor_property('srgb',suffix=='Color')
        tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,dict(Color='TC_DEFAULT',Normal='TC_NORMALMAP',ORM='TC_MASKS')[suffix]))
        tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        if not E.save_loaded_asset(tex,False):raise RuntimeError(name)
        textures.append((suffix,tex))
    mi=T.create_asset('MI_'+key,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,parent)
    for suffix,tex in textures:L.set_material_instance_texture_parameter_value(mi,suffix,tex)
    if not E.save_loaded_asset(mi,False):raise RuntimeError(path)
    return mi
def apply(w,req):
    plan=json.loads((R/'wall-plan.json').read_text('utf8'));api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    parent=master();installed=[]
    for name,s in plan.items():
        mat=material(name[10:],parent);mesh=import_mesh(name);mesh.modify();mesh.set_material(0,mat)
        # Low-count bevelled surface triangles, no collision; preserve importer LOD settings.
        if not E.save_loaded_asset(mesh,False):raise RuntimeError(name)
        label='StationFinal_'+name[10:]
        a=actors.get(label) or api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*s['origin']),u.Rotator())
        a.set_actor_label(label);a.set_folder_path('StationLine/StationSurface/FinalConcrete')
        a.modify();c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh);c.set_material(0,mat)
        c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False)
        c.set_cast_shadow(False);c.set_editor_property('receives_decals',True)
        installed.append(label)
    # Every old finish section is replaced; the original wall actors and approved samples remain.
    retired=[]
    source=json.loads((R.parent/'FreightStationSurfaces20261113/wall-sections.json').read_text('utf8'))
    for name in source['locations']:
        label='StationSurface_'+name[10:]
        if label in actors:
            api.destroy_actor(actors[label]);retired.append(label)
    return dict(installed=installed,retired=retired,base_wall_floor_slots_modified=False)
