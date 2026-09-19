"""Author river-owned materials/plant copies and connect the existing biome.

Requires the updated FPSGAMEEditor module. Does not load a map or run gameplay.
Source pack meshes, UVs, Pivot Painter data, textures and LODs remain intact.
For the current dense-bank vegetation, run build_dense_riverbanks.py afterwards;
this older recipe restores the initial six-plant selection and density.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
BASE='/Game/WorldGeneration/TemperateHills'
DEST=BASE+'/RiverEcology'
EAL=u.EditorAssetLibrary
LIB=u.MaterialEditingLibrary
OUT=ROOT/'Saved/RiverEcologySources'
OUT.mkdir(parents=True,exist_ok=True)
BACKUP=OUT/('BeforeAuthoring-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
REPORT={'sources':[
    'https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303',
    'https://www.fab.com/listings/ef6db212-dfcf-4a50-8ade-fbca49963240'],
    'meshes':[], 'saved':[], 'scope':'Asset authoring and integration only; no gameplay/visual tests'}

def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Missing river ecology source: '+path)
    return obj

def backup(path):
    source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if source.exists():
        dest=BACKUP/source.relative_to(ROOT/'Content')
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)

def save(obj):
    if not EAL.save_loaded_asset(obj,False):raise RuntimeError('Unable to save '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    return obj

def copy(source,target):
    backup(target)
    obj=load(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source,target)
    if obj is None:raise RuntimeError('Unable to copy '+source)
    return obj

def node(mat,cls):return LIB.create_material_expression(mat,cls)

def wire(source,target,pin):
    obj,output=source if isinstance(source,tuple) else (source,'')
    if not LIB.connect_material_expressions(obj,output,target,pin):raise RuntimeError('Material connection '+pin)

def prop(source,name):
    obj,output=source if isinstance(source,tuple) else (source,'')
    if not LIB.connect_material_property(obj,output,getattr(u.MaterialProperty,'MP_'+name)):
        raise RuntimeError('Material output '+name)

def custom(mat,code,inputs,count=3):
    expr=node(mat,u.MaterialExpressionCustom)
    expr.set_editor_property('code',code)
    expr.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(count)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    expr.set_editor_property('inputs',pins)
    for name,source in inputs.items():wire(source,expr,name)
    return expr

def scalar(mat,name,value):
    expr=node(mat,u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name',name);expr.set_editor_property('default_value',value)
    return expr

def color(mat,name,rgb):
    expr=node(mat,u.MaterialExpressionVectorParameter)
    expr.set_editor_property('parameter_name',name);expr.set_editor_property('default_value',u.LinearColor(*rgb,1))
    return expr

EAL.make_directory(DEST)
masters={}
materials={}

def plant(source,group):
    original=load(source)
    mesh=copy(source,DEST+'/SM_River_'+original.get_name())
    for index,slot in enumerate(original.get_editor_property('static_materials')):
        source_material=slot.material_interface
        key=(source_material.get_path_name(),group)
        if key not in materials:
            parent=source_material.get_editor_property('parent')
            parent_key=parent.get_path_name()
            if parent_key not in masters:
                master=copy(parent_key,DEST+'/M_River_'+parent.get_name())
                master.set_editor_property('used_with_instanced_static_meshes',True)
                opacity=LIB.get_material_property_input_node(master,u.MaterialProperty.MP_OPACITY_MASK)
                if opacity and opacity.get_editor_property('desc')!='RiverPlantDistanceFade':
                    out=LIB.get_material_property_input_node_output_name(master,u.MaterialProperty.MP_OPACITY_MASK)
                    fade=node(master,u.MaterialExpressionPerInstanceFadeAmount)
                    multiply=node(master,u.MaterialExpressionMultiply)
                    multiply.set_editor_property('desc','RiverPlantDistanceFade')
                    wire((opacity,out),multiply,'A');wire(fade,multiply,'B');prop(multiply,'OPACITY_MASK')
                LIB.recompile_material(master);save(master);masters[parent_key]=master
            mat=copy(source_material.get_path_name(),DEST+'/MI_River_'+group+'_'+source_material.get_name())
            LIB.set_material_instance_parent(mat,masters[parent_key])
            scalar_names={str(n) for n in LIB.get_scalar_parameter_names(masters[parent_key])}
            for name,value in {'Brightness':.78,'Saturation':.62 if group=='bank' else .78,
                'Subsurface Saturation':.65,'Subsurface Strengh':.50}.items():
                if name in scalar_names:LIB.set_material_instance_scalar_parameter_value(mat,name,value)
            switches={str(n) for n in LIB.get_static_switch_parameter_names(masters[parent_key])}
            for level in (1,2,3):
                for name,enabled in [('Level %d Bending'%level,False),('Level %d Wind'%level,level==1)]:
                    if name in switches:LIB.set_material_instance_static_switch_parameter_value(mat,name,enabled)
            LIB.update_material_instance(mat);save(mat);materials[key]=mat
        mesh.set_material(index,materials[key])
    save(mesh)
    REPORT['meshes'].append({'source':source,'copy':mesh.get_path_name(),'habitat':group})
    return mesh

grass='/Game/PN_GrassLibrary/Meshes/grassMesh/'
reeds=[plant(grass+name,'reeds') for name in ('grass_02_01_mesh','grass_04_01_mesh')]
banks=[plant(grass+name,'bank') for name in ('grass_09_02_mesh','grass_10_01_mesh')]
# Only small strap-leaf/rosette forms from the tropical pack. Large palmate and
# elephant-ear forms are excluded from this temperate biome.
understory=[plant('/Game/PN_tropicalGroundPlants/Meshes/'+name,'understory')
    for name in ('tropicalPlant_05_01','tropicalPlant_05_02')]

path=DEST+'/M_RiverFlowWater'
backup(path)
water=load(path) if EAL.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(
    'M_RiverFlowWater',DEST,u.Material,u.MaterialFactoryNew())
LIB.delete_all_material_expressions(water)
water.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
water.set_editor_property('two_sided',True)
water.set_editor_property('tangent_space_normal',False)
water.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
world=node(water,u.MaterialExpressionWorldPosition)
time=node(water,u.MaterialExpressionTime)
mask=node(water,u.MaterialExpressionVertexColor)
speed=scalar(water,'FlowSpeedMultiplier',1)
normal_strength=scalar(water,'RippleStrength',.24)
normals=[]
for name in ('T_River_Waves01_Normals','T_River_Waves02_Normals'):
    tex=node(water,u.MaterialExpressionTextureObject)
    tex.set_editor_property('texture',load('/Game/WaterMaterials/Textures/'+name))
    tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    normals.append(tex)
normal=custom(water,'''
float2 direction=normalize(M.rg*2-1+float2(.00001,0));
float velocity=M.b*160*Speed;
float offset=.12*sin(P.x*.0009+P.y*.0007);
float phase=frac(T*.11+offset), other=frac(phase+.5);
float2 uv=P.xy/340.0;
float2 travel=direction*velocity/(340.0*.11);
float2 a=Texture2DSample(N1,N1Sampler,uv-travel*phase).xy*2-1;
float2 b=Texture2DSample(N1,N1Sampler,uv-travel*other).xy*2-1;
float blend=abs(phase*2-1);
float2 broad=lerp(a,b,blend);
float2 fine=Texture2DSample(N2,N2Sampler,uv*2.13-travel*phase*1.71+3.7).xy*2-1;
float2 fineB=Texture2DSample(N2,N2Sampler,uv*2.13-travel*other*1.71+3.7).xy*2-1;
return normalize(float3((broad+lerp(fine,fineB,blend)*.4)*Strength*(.65+M.b),1));
''',{'P':world,'M':mask,'T':time,'Speed':speed,'Strength':normal_strength,'N1':normals[0],'N2':normals[1]})
prop(normal,'NORMAL')
depth_fade=node(water,u.MaterialExpressionDepthFade)
depth_fade.set_editor_property('fade_distance_default',100.0)
depth=custom(water,'return min(saturate(D),saturate(Scene))*100.0;',{'D':(mask,'A'),'Scene':depth_fade},1)
foam_obj=node(water,u.MaterialExpressionTextureObject)
foam_obj.set_editor_property('texture',load('/Game/WaterMaterials/Textures/T_Ocean_Foam'))
foam=custom(water,'''
float2 dir=normalize(M.rg*2-1+float2(.00001,0));
float phase=frac(T*.11+.12*sin(P.x*.0009+P.y*.0007));
float2 uv=P.xy/210,travel=dir*M.b*160*Speed/(210*.11);
float noise=lerp(Texture2DSample(F,FSampler,uv-travel*phase).r,
    Texture2DSample(F,FSampler,uv-travel*frac(phase+.5)).r,abs(phase*2-1));
float shore=(1-smoothstep(4,25,Depth))*smoothstep(.3,4,Depth);
float rapids=smoothstep(.35,.75,M.b)*smoothstep(15,55,Depth);
return saturate((shore*.55+rapids*.27)*smoothstep(.45,.83,noise)*Amount);
''',{'P':world,'M':mask,'T':time,'Speed':speed,'Depth':depth,'F':foam_obj,'Amount':scalar(water,'FoamAmount',.65)},1)
shallow=color(water,'ShallowTint',(.085,.13,.085))
deep=color(water,'DeepTint',(.012,.058,.047))
absorb=scalar(water,'AbsorptionPerCm',.018)
prop(custom(water,'float a=1-exp(-Depth*Absorb);return lerp(lerp(S,D,a),float3(.54,.60,.54),Foam);',
    {'Depth':depth,'Absorb':absorb,'S':shallow,'D':deep,'Foam':foam}),'BASE_COLOR')
prop(custom(water,'return lerp(.09,.33,Foam);',{'Foam':foam},1),'ROUGHNESS')
prop(scalar(water,'WaterSpecular',.5),'SPECULAR')
fresnel=node(water,u.MaterialExpressionFresnel)
fresnel.set_editor_property('exponent',5.0)
fresnel.set_editor_property('base_reflect_fraction',.02)
opacity=custom(water,'return saturate((.10+.56*(1-exp(-Depth*Absorb))+.18*Fresnel+Foam*.45)*smoothstep(0,6,Depth));',
    {'Depth':depth,'Absorb':absorb,'Fresnel':fresnel,'Foam':foam},1)
prop(opacity,'OPACITY')
LIB.recompile_material(water);save(water)

# The map already references this data asset. Modify only this task's fields.
backup(BASE+'/DA_TemperateHillsStreaming')
assets=load(BASE+'/DA_TemperateHillsStreaming')
assets.set_editor_property('river_reeds',reeds)
assets.set_editor_property('river_bank_grasses',banks)
assets.set_editor_property('river_understory',understory)
assets.set_editor_property('river_plant_coverage',.65)
assets.set_editor_property('river_material',water)
assets.set_editor_property('tree_dormant_days',1.0)
assets.set_editor_property('tree_mature_days',6.0)
save(assets)
REPORT['configuration']=assets.get_path_name()
REPORT['growth']={'dormant_days':1,'mature_days':6,'offline_growth':False}
(OUT/'authoring.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('TEMPERATE_RIVER_ECOLOGY_AUTHORING_COMPLETE')
