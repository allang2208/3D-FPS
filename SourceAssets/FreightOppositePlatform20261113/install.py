"""Install only the photographed return and north wall finish, with registered floor and toe masks."""
from pathlib import Path
import json,runpy
import unreal as u
R=Path(__file__).resolve().parent;S=R.parent/'FreightStationSurfaces20261113'
BASE='/Game/SceneTests/FreightOppositePlatform20261113'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
meshimport=runpy.run_path(str(S/'install_walls.py'))['import_mesh']
meshimport.__globals__.update(ROOT=R,BASE=BASE)
instances=runpy.run_path(str(S/'install_ground.py'))['instances']
instances.__globals__.update(ROOT=R,BASE=BASE)
def walls(name):
    path=BASE+'/Materials/M_'+name
    if E.does_asset_exist(path):return u.load_asset(path)
    mat=tools.create_asset('M_'+name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    for suffix,compress,sampler,pins in [
        ('Color','TC_DEFAULT','SAMPLERTYPE_COLOR',[('RGB','BASE_COLOR')]),
        ('Normal','TC_NORMALMAP','SAMPLERTYPE_NORMAL',[('RGB','NORMAL')]),
        ('ORM','TC_MASKS','SAMPLERTYPE_MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')])]:
        leaf='T_'+name+'_'+suffix;folder=BASE+'/Textures';texpath=folder+'/'+leaf
        if not E.does_asset_exist(texpath):
            t=u.AssetImportTask();t.filename=str(R/'Textures'/(leaf+'.png'));t.destination_path=folder;t.destination_name=leaf;t.automated=True;t.save=False;tools.import_asset_tasks([t])
        tex=u.load_asset(texpath);tex.modify();tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,compress));tex.set_editor_property('srgb',suffix=='Color')
        tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        if not E.save_loaded_asset(tex,False):raise RuntimeError(texpath)
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex);node.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,sampler))
        for pin,prop in pins:
            if not L.connect_material_property(node,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
    if L.recompile_material(mat) or not E.save_loaded_asset(mat,False):raise RuntimeError(path)
    return mat
def apply(w,req):
    layout=json.loads((R/'wall-plan.json').read_text('utf8'))
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    original=u.load_asset('/Game/SceneTests/FreightCartUpperWall20261113/Materials/M_CastBayConcrete')
    def mesh(n,mat):
        m=meshimport(n);m.modify();m.set_material(0,mat)
        if not E.save_loaded_asset(m,False):raise RuntimeError(n)
        return m
    def standalone(name,pos,mat):
        label='OppositePlatform_'+name
        a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos),u.Rotator())
            a.set_actor_label(label);a.set_folder_path('StationLine/OppositePlatform')
        a.modify();c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh(name,mat));c.set_material(0,mat)
        c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False);c.set_cast_shadow(False);c.set_editor_property('receives_decals',True)
    for old,new in layout['replace'].items():
        a=actors['StationSurface_'+old[10:]];a.modify();c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh(new,original))
    for side in ('Return','Pipe'):
        n='SM_Form_'+side;standalone(n,layout['origins'][n],walls(side))
    # Feet of both walls plus the walkway in the corner. Shallower than tile/prop clearances.
    floor=instances([{'texture':s} for s in ['Aisle','ToeReturn','ToePipe']])
    for name,pos,rot,size in [
        ('Aisle',[6997,-2523,-.90],u.Rotator(pitch=-90),[1.75,513.,823.]),
        ('ToeReturn',[6177.1,-2297,79],u.Rotator(yaw=180),[4.4,739.,79.]),
        ('ToePipe',[6997,-3033.1,79],u.Rotator(yaw=-90),[4.4,823.,79.])]:
        label='OppositePlatform_'+name
        a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.DecalActor,u.Vector(*pos),rot)
            a.set_actor_label(label);a.set_folder_path('StationLine/OppositePlatform')
        c=a.get_component_by_class(u.DecalComponent);c.modify();c.set_editor_property('decal_size',u.Vector(*size));c.set_decal_material(floor[name]);c.set_editor_property('sort_order',6);c.set_editor_property('fade_screen_size',.002)
    return {'forms':layout['counts'],'scopes':layout['sections']}
