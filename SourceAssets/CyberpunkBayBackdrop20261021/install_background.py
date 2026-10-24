"""Import the native cube and save only the apartment's exterior backdrop.
Reusable apply_saved_background() is called by the apartment rebuild entry.
No PIE, acceptance capture or game launch.
"""
from pathlib import Path
from datetime import datetime
import json,hashlib,shutil,traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
MAP='/Game/GameMaps/L_CyberpunkApartment'
BASE='/Game/Props/CyberpunkBayBackdrop20261021'
TEXTURE=BASE+'/T_CyberpunkBayNight_Cube'
MATERIAL=BASE+'/M_CyberpunkBayNight_Cube'
INSTANCE=BASE+'/MI_CyberpunkBayNight_Apartment'
LABEL='Bay_NightEnvironment'
RETIRED={'CITY_blocks','CITY_bridges','CITY_fog','CITY_ground',
         'CITY_horizon','CITY_signs','CITY_traffic'}
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
DIRECTION=r'''
float3 d=normalize(P-Eye);
// Bay lies along world +Y; retain the captured high-floor viewpoint while
// a finite 3D box gives small, ground-anchored motion when walking to a window.
float3 signD=lerp(-1.0,1.0,step(0.0,d));
float3 safeD=signD*max(abs(d),0.00001);
float3 farT=(lerp(BoxMin,BoxMax,step(0.0,d))-Eye)/safeD;
float t=min(farT.x,min(farT.y,farT.z));
float3 v=(t>0.0)?(Eye+d*t-Origin):d;
// DDS axes: screen right, up, forward. UE looking +Y has screen-right -X.
return normalize(float3(-v.x,v.z,v.y));
'''

def save(asset):
    asset.modify()
    if not E.save_loaded_asset(asset,only_if_is_dirty=False):
        raise RuntimeError('Asset save failed: '+asset.get_path_name())

def create_material(tex):
    m=u.load_asset(MATERIAL) if E.does_asset_exist(MATERIAL) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        MATERIAL.rsplit('/',1)[1],BASE,u.Material,u.MaterialFactoryNew())
    m.modify();L.delete_all_material_expressions(m)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('is_sky',True)
    def node(kind,**props):
        n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin='',out=''):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material pin '+pin)
    position=node('WorldPosition');eye=node('CameraPositionWS')
    code=node('Custom',code=DIRECTION,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
              desc='Ground anchored bay cubemap, world +Y facing the opposite shore')
    inputs=[]
    for name in ('P','Eye','Origin','BoxMin','BoxMax'):
        p=u.CustomInput();p.set_editor_property('input_name',name);inputs.append(p)
    code.set_editor_property('inputs',inputs)
    wire(position,code,'P');wire(eye,code,'Eye')
    for name,value in [('Origin',(1000.,0.,170.)),
                       ('BoxMin',(-449000.,-450000.,-19000.)),
                       ('BoxMax',(451000.,450000.,200000.))]:
        n=node('VectorParameter',parameter_name='Capture'+name,default_value=u.LinearColor(*value,1))
        wire(n,code,name,'RGB')
    sample=node('TextureSampleParameterCube',parameter_name='BayNightCube',texture=tex,
                sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    wire(code,sample,'UVs')
    gain=node('ScalarParameter',parameter_name='NightLuminance',default_value=1.)
    emission=node('Multiply');wire(sample,emission,'A','RGB');wire(gain,emission,'B')
    slab=node('SubstrateUnlitBSDF');wire(emission,slab,'EmissiveColor')
    wire(node('Constant3Vector',constant=u.LinearColor(0,0,0,1)),slab,'TransmittanceColor')
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.layout_material_expressions(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation failed: '+str(errors))
    save(m)
    mi=u.load_asset(INSTANCE) if E.does_asset_exist(INSTANCE) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        INSTANCE.rsplit('/',1)[1],BASE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mi.modify();L.set_material_instance_parent(mi,m)
    L.set_material_instance_scalar_parameter_value(mi,'NightLuminance',1.)
    L.update_material_instance(mi);save(mi)
    return mi

def apply_saved_background(world):
    layered=ROOT.parent/'CyberpunkBayLayered20261022'
    if (layered/'installed.json').exists():
        import runpy
        return runpy.run_path(str(layered/'install_level.py'))['apply_saved_background'](world)
    if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong backdrop target map')
    mi=u.load_asset(INSTANCE)
    if not mi:raise RuntimeError('Bay backdrop material has not been saved')
    AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    changed=[]
    for label in sorted(RETIRED):
        a=actors.get(label)
        if not a:continue
        a.modify();a.set_actor_hidden_in_game(True);a.set_actor_enable_collision(False)
        for c in a.get_components_by_class(u.PrimitiveComponent):
            c.set_visibility(False);c.set_hidden_in_game(True)
            c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            c.set_editor_property('cast_shadow',False)
        changed.append(label)
    actor=actors.get(LABEL)
    if not actor:
        actor=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(1000,0,170),u.Rotator())
        actor.set_actor_label(LABEL)
    actor.modify()
    c=actor.static_mesh_component
    c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere.Sphere'))
    c.set_mobility(u.ComponentMobility.STATIC)
    actor.set_actor_location(u.Vector(1000,0,170),False,False)
    actor.set_actor_scale3d(u.Vector(10000,10000,10000))
    actor.set_actor_hidden_in_game(False)
    actor.set_actor_enable_collision(False)
    actor.set_editor_property('tags',[u.Name('CyberpunkApartment.BayNight20261021')])
    c.set_material(0,mi)
    c.set_visibility(True);c.set_hidden_in_game(False)
    c.set_collision_profile_name(u.Name('NoCollision'))
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    c.set_editor_property('cast_shadow',False)
    c.set_editor_property('affect_distance_field_lighting',False)
    c.set_editor_property('affect_dynamic_indirect_lighting',False)
    # Retain reflection visibility; no global Lumen/ray-tracing change.
    c.set_editor_property('visible_in_ray_tracing',True)
    return {'background_actor':LABEL,'disabled_old_backgrounds':changed,
            'preserved_near_building':'CITY_our_tower','material':mi.get_path_name(),
            'bay_forward_world':[0,1,0],'night_luminance':1.0}

def main():
    layered=ROOT.parent/'CyberpunkBayLayered20261022'
    if (layered/'installed.json').exists():
        import runpy
        runpy.run_path(str(layered/'publish.py'),run_name='__main__')
        return
    report={'stage':'preparing','map':MAP,'game_run':False,'tests_run':False,
            'editor_opened':False,'acceptance_rendered':False,'production_texture_baked':True}
    def record():(ROOT/'install-attempt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    record()
    try:
        if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('Active PIE prevents background asset installation')
        previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else None
        report['existing_editor_used']=editor is not None
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
        source=json.loads((ROOT/'cube.json').read_text())
        task=u.AssetImportTask();task.filename=source['file'];task.destination_path=BASE
        task.destination_name=TEXTURE.rsplit('/',1)[1];task.factory=u.TextureFactory()
        task.automated=True;task.replace_existing=True;task.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        tex=u.load_asset(TEXTURE)
        if not isinstance(tex,u.TextureCube):raise RuntimeError('DDS did not import as TextureCube')
        tex.modify()
        for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,
             lod_group=u.TextureGroup.TEXTUREGROUP_SKYBOX,max_texture_size=source['size'],
             mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():tex.set_editor_property(k,v)
        save(tex)
        mi=create_material(tex)
        report.update(stage='assets_saved',texture=tex.get_path_name(),material_instance=mi.get_path_name(),
                      cube_face_size=source['size'],source_sha256=source['sha256'])
        record()
        backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        backup.mkdir(parents=True,exist_ok=True)
        src=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap'
        shutil.copy2(src,backup/src.name)
        report['map_backup']=str(backup/src.name)
        world=u.EditorLoadingAndSavingUtils.load_map(MAP)
        if not world:raise RuntimeError('Cannot load apartment')
        report.update(apply_saved_background(world))
        if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map save failed')
        report['stage']='map_saved';record()
        (ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        u.log('CYBERPUNK_BAY_BACKGROUND_SAVED '+MAP)
        if previous and previous!=MAP and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)
    except Exception:
        report['error']=traceback.format_exc();record();raise

if __name__=='__main__':main()
