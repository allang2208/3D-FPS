"""Create scoped GPU lamp faults and a bounded exposure Blueprint; no gameplay test."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'Config/lighting.json').read_text(encoding='utf-8'));BASE=C['ue_base']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
saved=[]
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name())
def node(m,kind,**properties):
    n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
    for k,v in properties.items():n.set_editor_property(k,v)
    return n
def wire(n,target,pin):
    if not L.connect_material_expressions(n,'',target,pin):raise RuntimeError('Cannot connect '+pin)
def prop(m,n,name):
    if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Cannot author '+name)
def scalar(m,k,v):return node(m,'ScalarParameter',parameter_name=k,default_value=v)
def color(m,k,v):return node(m,'VectorParameter',parameter_name=k,default_value=u.LinearColor(*v,1))
def custom(m,code,inputs,width=1):
    n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,value in inputs.items():wire(value,n,key)
    return n
def make(name,domain):
    path=BASE+'/Materials/'+name
    if E.does_asset_exist(path):return u.load_asset(path),False
    m=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('material_domain',domain)
    if domain==u.MaterialDomain.MD_SURFACE:
        m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
    return m,True
def finish(m):
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material build failed '+str(errors))
    L.layout_material_expressions(m);save(m)
def instance(name,parent,params,tint=None):
    path=BASE+'/Materials/'+name
    if E.does_asset_exist(path):return u.load_asset(path)
    mi=A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,parent)
    for k,v in params.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    if tint:L.set_material_instance_vector_parameter_value(mi,'LampTint',u.LinearColor(*tint,1))
    L.update_material_instance(mi);save(mi);return mi

# Shared shader time and seed keep the tube and projected illumination in phase.
# Each 19.7 s window chooses different event timing and dropout length.
fault_code='''
float t=max(T,0)+Phase;
float cycle=floor(t/19.7), q=t-cycle*19.7;
float r=frac(sin(cycle*12.9898+Phase*7.13+3.1)*43758.5453);
float r2=frac(sin(cycle*39.346+Phase*4.7+8.2)*23421.631);
float e=q-(2.0+r*8.0), a=1.0;
if(e>=0 && e<.12)a=.035;
else if(e>=.12 && e<.28)a=.62;
else if(e>=.28 && e<.44)a=.055;
else if(e>=.44 && e<.78)a=lerp(.28,1.,(e-.44)/.34);
float b=e-(2.8+r2*1.7), duration=.55+r*.95;
if(b>=0 && b<duration)a=.025;
else if(b>=duration && b<duration+.38)a=lerp(.22,1.,(b-duration)/.38);
return lerp(1.,a,Fault)*(1.-Dead);
'''
def factor(m):return custom(m,fault_code,{'T':node(m,'Time'),'Phase':scalar(m,'Phase',0),
                                        'Fault':scalar(m,'Fault',0),'Dead':scalar(m,'Dead',0)})
function,new=make('M_MorgueFaultFunction',u.MaterialDomain.MD_LIGHT_FUNCTION)
if new:prop(function,factor(function),'EMISSIVE_COLOR');finish(function)
diffuser,new=make('M_MorgueLampDiffuser',u.MaterialDomain.MD_SURFACE)
if new:
    emission=custom(diffuser,'return Tint*Factor*Strength;',{'Tint':color(diffuser,'LampTint',(.68,.82,.78)),
                    'Factor':factor(diffuser),'Strength':scalar(diffuser,'Emission',1)},3)
    inputs={'BASE_COLOR':color(diffuser,'DiffuserColor',(.16,.18,.17)),
            'ROUGHNESS':scalar(diffuser,'Roughness',.58),'SPECULAR':scalar(diffuser,'Specular',.26),'EMISSIVE_COLOR':emission}
    slab=node(diffuser,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for key,value in inputs.items():
        prop(diffuser,value,key);wire(value,slab,{'BASE_COLOR':'BaseColor','ROUGHNESS':'Roughness','SPECULAR':'Specular','EMISSIVE_COLOR':'Emissive Color'}[key])
    prop(diffuser,slab,'FRONT_MATERIAL');finish(diffuser)
for s in C['lights']:
    params=dict(Phase=s['phase'],Fault=float(s['fault']=='flicker'),Dead=float(s['fault']=='dead'),Emission=s['emission'])
    instance('MI_Diffuser_'+s['id'],diffuser,params,s['tint'])
    if s['fault']=='flicker':instance('MI_Fault_'+s['id'],function,params)

path=BASE+'/Blueprints/BP_MorgueExposure'
if not E.does_asset_exist(path):
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Actor)
    bp=A.create_asset('BP_MorgueExposure',BASE+'/Blueprints',u.Blueprint,factory)
    S=u.get_engine_subsystem(u.SubobjectDataSubsystem);F=u.SubobjectDataBlueprintFunctionLibrary
    handles=S.k2_gather_subobject_data_for_blueprint(bp)
    def obj(h):return F.get_object(F.get_data(h))
    roots=[h for h in handles if F.is_root_component(F.get_data(h))]
    root=roots[0]
    def component(name,cls,parent):
        h,reason=S.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp))
        if not F.is_handle_valid(h):raise RuntimeError('Component '+name+': '+str(reason))
        S.rename_subobject(h,u.Text(name));return h,obj(h)
    box_h,box=component('BasementBounds',u.BoxComponent,root)
    box.set_box_extent(u.Vector(*C['postprocess']['extent_cm']));box.set_collision_profile_name('NoCollision')
    box.set_editor_property('generate_overlap_events',False);box.set_hidden_in_game(True)
    pp_h,pp=component('BasementExposure',u.PostProcessComponent,box_h)
    pp.set_editor_property('unbound',False);pp.set_editor_property('priority',20.)
    pp.set_editor_property('blend_radius',C['postprocess']['blend_radius_cm']);pp.set_editor_property('blend_weight',1.)
    config=C['postprocess'];settings=pp.get_editor_property('settings')
    values=dict(auto_exposure_min_brightness=config['exposure_ev'],auto_exposure_max_brightness=config['exposure_ev'],
                auto_exposure_bias=config['exposure_bias'],indirect_lighting_intensity=config['indirect_intensity'],
                color_saturation=u.Vector4(config['saturation'],config['saturation'],config['saturation'],1),
                color_contrast=u.Vector4(config['contrast'],config['contrast'],config['contrast'],1),
                vignette_intensity=config['vignette'],bloom_intensity=config['bloom'])
    for key,value in values.items():settings.set_editor_property('override_'+key,True);settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Exposure Blueprint compilation failed')
    cdo=u.get_default_object(bp.generated_class());tick=cdo.get_editor_property('primary_actor_tick')
    tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick);save(bp)
(ROOT/'Receipts/assets.json').write_text(json.dumps(dict(stage='lighting_assets_saved',saved=saved,tests_run=False),indent=2),encoding='utf-8')
print('MORGUE_LIGHTING_ASSETS_SAVED',len(saved),flush=True)
