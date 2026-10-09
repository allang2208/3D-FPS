"""Save only the botanical display and its replacement floor guidance in both hall subjects."""
import unreal as u
import json,hashlib,importlib.util,traceback,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent
CFG=json.loads((ROOT/'assembly.json').read_text('utf8'));MAN=json.loads((ROOT/'manifest.json').read_text('utf8'));BASE=CFG['base'];OWNER=CFG['owner']
spec=importlib.util.spec_from_file_location('botanical_facility_support',PARENT/'install.py');I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
R=I.R;E=R.E;L=R.L;A=R.A;AA=R.AA
report=dict(stage='preparing',saved_assets=[],maps=[],plants=0,glass_panels=0,lights=0,tests_run=False,rendered=False,game_run=False,production_registered=False)
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for key,v in dict(ROOT=ROOT,OWNER=OWNER,BASE=BASE,MAN=MAN,report=report,record=record).items():setattr(R,key,v)
def tag(a):a.set_editor_property('tags',list(a.tags)+[u.Name(OWNER)]);return a

def material():
    f=ROOT/'Authored/Textures/T_BotanicalDisplay_Label.png';key=hashlib.sha256(f.read_bytes()).hexdigest();path=BASE+'/Textures/'+f.stem;t=R.reuse(path,key)
    if not t:
        t=R.imported(path,f);t.set_editor_property('srgb',True);t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);t.set_editor_property('never_stream',False);R.saved(t,key)
    path=BASE+'/Materials/M_BotanicalDisplay_Label';key+=':substrate-label-v1'
    if R.reuse(path,key):return
    m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew());m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
    slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',t);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    L.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR);L.connect_material_expressions(n,'RGB',slab,'BaseColor')
    for value,pin,prop in ((.65,'Roughness',u.MaterialProperty.MP_ROUGHNESS),(.12,'Metallic',u.MaterialProperty.MP_METALLIC)):
        n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);L.connect_material_expressions(n,'',slab,pin);L.connect_material_property(n,'',prop)
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Label material build failed: '+str(errors))
    R.saved(m,key)

def tree_materials(a,p):
    paths=[]
    for index,slot in enumerate(a.static_mesh_component.static_mesh.static_materials):
        src=slot.material_interface;name='MI_EcoTree_'+hashlib.sha1(src.get_path_name().encode()).hexdigest()[:10];stock='/Game/Dungeons/Ecology20261004/RefineV6/Materials/'+name
        if E.does_asset_exist(stock):mi=R.asset(stock)
        else:
            path=BASE+'/Materials/'+name;key=src.get_path_name()+':indoor-wind-v1';mi=R.reuse(path,key)
            if not mi:
                mi=A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,src)
                for parameter in L.get_scalar_parameter_names(src):
                    if ('Wind' in str(parameter) and 'Strength' in str(parameter)) or str(parameter)=='ShadowLength':L.set_material_instance_scalar_parameter_value(mi,parameter,0.)
                L.update_material_instance(mi);R.saved(mi,key)
        a.static_mesh_component.set_material(index,mi);paths.append(mi.get_path_name())
    p['material_overrides']=paths

def place(world,path):
    removed=[]
    for a in list(AA.get_all_level_actors()):
        if u.Name(OWNER) in a.tags or a.get_actor_label() in CFG['replaces_actor_labels']:
            removed.append(a.get_actor_label());AA.destroy_actor(a)
    for m in MAN['meshes']:
        if m['kind']=='Fracture' or (m['kind']=='Glass' and not m.get('roof')):continue
        tag(R.static(m['mesh'],[0,0,0],m['name'],m['collision'],shadow=m['cast_shadow'],folder='BotanicalDisplay/Case'))
    groups={}
    for p in CFG['plants']:
        a=tag(R.static(p['mesh'],p['position_m'],'Botanical_'+p['id'],p['collision'],p['yaw_deg'],p['scale'],p['cast_shadow'],'BotanicalDisplay/Plants'))
        if p.get('indoor_tree_materials'):tree_materials(a,p)
        else:groups.setdefault(p['mesh'],[]).append(a)
        report['plants']+=1
    for mesh,actors in groups.items():
        if len(actors)<2:continue
        for a in actors:a.set_editor_property('tags',list(a.tags)+[u.Name('ColdSteel.MainPlaza.Generated')])
        cluster=u.PlazaInstanceTools.create_plaza_cluster(actors,'FacilityTransit_Botanical_Instances_'+mesh.rsplit('/',1)[1])
        if cluster:
            cluster.set_editor_property('tags',[u.Name('FacilityTransit.Subject'),u.Name(OWNER)]);cluster.set_folder_path('FacilityTransit/BotanicalDisplay/Plants')
            for a in actors:AA.destroy_actor(a)
    for p in CFG['glass']:
        a=tag(I.spawn(u.WardGlassWindow,p['position_m'],'Botanical_'+p['id'],'BotanicalDisplay/Glazing',p['yaw_deg']));pane=a.get_editor_property('glass_pane')
        pane.set_static_mesh(R.asset(p['pane']));pane.set_cast_shadow(False);pane.set_editor_property('receives_decals',False)
        for key,value in dict(fracture_mesh=p['fracture'],fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',break_sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0').items():pane.set_editor_property(key,R.asset(value))
        pane.set_editor_property('pane_dimensions',u.Vector(p['width_m']*100,p['height_m']*100,.8));report['glass_panels']+=1
    for p in CFG['lights']:
        a=tag(I.spawn(u.PointLight,p['position_m'],p['id'],'BotanicalDisplay/Lighting'));c=a.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(p['intensity']);c.set_editor_property('attenuation_radius',p['radius']*100);c.set_editor_property('cast_shadows',False)
        c.set_editor_property('max_draw_distance',3200);c.set_editor_property('max_distance_fade_range',500);c.set_editor_property('source_radius',8.);c.set_editor_property('source_length',30.);c.set_editor_property('indirect_lighting_intensity',.5);c.set_editor_property('volumetric_scattering_intensity',.0);c.set_light_color(u.LinearColor(.89,1.,.86,1))
        a.set_editor_property('tags',list(a.tags)+[u.Name('DungeonLight.Local')]);report['lights']+=1
    E.set_metadata_tag(world,OWNER+'.Revision',CFG['revision'])
    runpy.run_path(str(PARENT.parent/'HallLighting20261007/profile.py'))['reapply_if_installed']()
    if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Unable to save '+path)
    report['maps'].append(dict(path=path,saved=True,removed_owned_actors=len(removed),plants=25,glass_panels=12));record()

def main():
    R.guard();record();material();R.meshes();report['stage']='assets_saved';record()
    for path in CFG['maps']:
        R.guard();world=u.EditorLoadingAndSavingUtils.load_map(path)
        if not world:raise RuntimeError('Existing subject unavailable: '+path)
        place(world,path)
    (ROOT/'assembly.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
    parent=json.loads((PARENT/'Config/layout.json').read_text('utf8'));parent['central_display']=dict(assembly=str(ROOT/'assembly.json'),manifest=str(ROOT/'manifest.json'),revision=CFG['revision'],status='saved_subject_assembly');(PARENT/'Config/layout.json').write_text(json.dumps(parent,ensure_ascii=False,indent=2),encoding='utf8')
    runpy.run_path(str(PARENT/'draft.py'),run_name='__main__')
    report['stage']='maps_saved';record();u.log('BOTANICAL_DISPLAY_MAPS_SAVED')
if __name__=='__main__':
    try:main()
    except Exception:report['error']=traceback.format_exc();record();raise
