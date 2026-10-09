"""GPU-driven fault functions and matching lamp skins; no actor ticking."""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
P=runpy.run_path(str(ROOT/'profile.py'))
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
BASE=P['BASE']+'/Materials'
saved=[]
FAULT_CODE='''
float t=max(T,0.0)+Phase;
// A fault must be visible within a short walk past the fixture. Independent
// periods and phases avoid flashing the whole hall in synchrony.
float period=6.4+frac(Phase*.37)*2.2;
float cycle=floor(t/period), q=t-cycle*period;
float outageEnd=1.7+frac(cycle*.37+Phase*.61)*.45, a=1.0;
if(q<.16)a=.015;
else if(q<.32)a=.72;
else if(q<.50)a=.008;
else if(q<.72)a=.38;
else if(q<outageEnd)a=.003;
else if(q<outageEnd+.55)a=lerp(.12,1.0,(q-outageEnd)/.55);
float factor=lerp(1.0,a,Fault)*(1.0-Dead);
'''


def node(m,kind,**properties):
    n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
    for key,value in properties.items():n.set_editor_property(key,value)
    return n


def wire(n,target,pin):
    if not L.connect_material_expressions(n,'',target,pin):raise RuntimeError('Cannot connect '+pin)


def prop(m,n,key):
    if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Cannot author '+key)


def custom(m,code,inputs,width=1):
    n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,n,name)
    return n


def scalar(m,key,value):return node(m,'ScalarParameter',parameter_name=key,default_value=value)


def make(name,domain):
    m=u.load_asset(BASE+'/'+name)
    if not m:m=A.create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
    m.modify();L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain',domain)
    if domain==u.MaterialDomain.MD_SURFACE:
        m.set_editor_property('used_with_nanite',True)
        m.set_editor_property('used_with_instanced_static_meshes',True)
    return m


def save(asset):
    if isinstance(asset,u.Material):
        error=L.recompile_material(asset)
        if error:raise RuntimeError('Lighting material build failed '+str(error))
        L.layout_material_expressions(asset)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Lighting asset save failed')
    saved.append(asset.get_path_name())


def surface(m,emission):
    slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    base=node(m,'Constant3Vector',constant=u.LinearColor(.14,.16,.145,1))
    for key,pin,n in [('BASE_COLOR','BaseColor',base),('ROUGHNESS','Roughness',scalar(m,'Roughness',.62)),
                      ('SPECULAR','Specular',scalar(m,'Specular',.22)),('EMISSIVE_COLOR','Emissive Color',emission)]:
        prop(m,n,key);wire(n,slab,pin)
    prop(m,slab,'FRONT_MATERIAL')


def main():
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(P['BASE']+'/') for p in dirty):raise RuntimeError('Preserve unsaved hall lighting material')
    layouts={g:json.loads((P['PROJECT']/'SourceAssets'/folder/'Config/layout.json').read_text('utf8'))
             for g,folder in [('Reception','DungeonReceptionHall20261006'),('Transit','DungeonFacilityTransit20261007')]}
    function=make('M_FaultFunction',u.MaterialDomain.MD_LIGHT_FUNCTION)
    factor=custom(function,FAULT_CODE+'return factor;',
        {'T':node(function,'Time'),'Phase':scalar(function,'Phase',0),
         'Fault':scalar(function,'Fault',1),'Dead':scalar(function,'Dead',0)})
    prop(function,factor,'EMISSIVE_COLOR');save(function)
    for group,cfg in layouts.items():
        lights=P['revise_layout'](cfg,group)['lights']
        for p in lights:
            if p['fault']!='flicker':continue
            name=p['light_function'].rsplit('/',1)[-1]
            mi=u.load_asset(BASE+'/'+name) or A.create_asset(name,BASE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
            mi.modify();L.set_material_instance_parent(mi,function)
            for key,value in dict(Phase=p['phase'],Fault=1.,Dead=0.).items():L.set_material_instance_scalar_parameter_value(mi,key,value)
            L.update_material_instance(mi);save(mi)
        # The source diffusers are one authored mesh per hall. Local-space masks
        # select each whole fixture; relocated/rotated modules keep the same phase.
        m=make('M_'+group+'Diffusers',u.MaterialDomain.MD_SURFACE)
        world=node(m,'WorldPosition')
        local=node(m,'TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                   transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(world,local,str(L.get_material_expression_input_names(local)[0]))
        code='float Phase=0, Fault=0, Dead=0, Strength=.65; float3 Tint=float3(.91,.82,.64);\n'
        for p in lights:
            if group=='Transit' and p['id'].startswith('Approach'):continue
            x,y,z=p['position_m']
            z=z+.144 if group=='Reception' else 7.037 if p['type']=='spot' else z+.07
            c=p['color']
            code+=('if(all(abs(P-float3(%f,%f,%f))<float3(155,24,19)))'
                   '{Phase=%f;Fault=%f;Dead=%f;Strength=%f;Tint=float3(%f,%f,%f);}\n')%(
                       x*100,-y*100,z*100,p['phase'],float(p['fault']=='flicker'),float(p['fault']=='dead'),p['emission'],*c)
        emission=custom(m,code+FAULT_CODE+'return Tint*Strength*factor;',{'P':local,'T':node(m,'Time')},3)
        surface(m,emission);save(m)
    m=make('M_SteadyDiffuser',u.MaterialDomain.MD_SURFACE)
    surface(m,node(m,'Constant3Vector',constant=u.LinearColor(.42,.40,.30,1)));save(m)
    (ROOT/'Receipts/materials.json').write_text(json.dumps(dict(stage='materials_saved',assets=saved,tests_run=False),indent=2),encoding='utf8')
    return saved


if __name__=='__main__':main()
