import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V2=ROOT.parent/'DungeonCombatExpansion20260922';BASE='/Game/Dungeons/CombatExpansionV3_20260922';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
saved=[]
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    saved.append(a.get_path_name())
def node(k):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+k))
def wire(src,dst,pin):
    if not L.connect_material_expressions(src,'',dst,pin):raise RuntimeError('Wire '+pin)
def out(n,p):
    if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+p)):raise RuntimeError(p)
def scalar(name,v):
    n=node('ScalarParameter');n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',v);return n
def custom(code,inputs,width=3):
    n=node('Custom');n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));pins=[]
    for k in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,n,k)
    return n
fluid=json.loads((ROOT/'Authored/fluids.json').read_text());fall=fluid['falltime']
parent_path=BASE+'/Materials/M_PusRadialSurface'
parent=u.load_asset(parent_path)
if not parent:
    parent=E.duplicate_asset('/Game/Dungeons/CombatExpansion20260922/Materials/M_PusFluidV2',parent_path)
    parent.modify()
    for expression in L.get_material_expressions(parent):
        if not isinstance(expression,u.MaterialExpressionCustom):continue
        code=expression.get_editor_property('code')
        if 'float p1=dot(UV' not in code:continue
        code=code.replace('i==1?.34:.73','i==1?.37:.73').replace('frac(T/1.55+phase-Fall/1.55)*1.55','frac((T-1.48-Fall)/2.35+phase)*2.35').replace('i==1?.037:-.032','i==1?.035:-.028')
        expression.set_editor_property('code',code)
    errors=L.recompile_material(parent)
    if errors:raise RuntimeError(str(errors))
    save(parent)
path=BASE+'/Materials/MI_PusPuddleRadial';mi=u.load_asset(path) or A.create_asset('MI_PusPuddleRadial',BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
mi.modify();L.set_material_instance_parent(mi,parent)
for k,v in {'WaveScale':.16,'NormalSlope':2.1,'ImpactStrength':2.5,'BaseOpacity':.20,'DepthScaleCm':4,'Roughness':.07,'DropFallSeconds':fall,'MicroNormalStrength':.12}.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
L.update_material_instance(mi);save(mi)
shared=(ROOT/'Scripts/drip_shape.hlsl').read_text()
for attached,name in [(False,'M_PusReleasedDrops'),(True,'M_PusGatheringNeck')]:
    path=BASE+'/Materials/'+name;mat=u.load_asset(path)
    if mat:continue
    mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT);mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING);mat.set_editor_property('tangent_space_normal',False);mat.set_editor_property('two_sided',True);mat.set_editor_property('screen_space_reflections',True)
    inputs={'UV':node('TextureCoordinate'),'Meta':node('VertexColor'),'T':node('Time'),'Attached':scalar('Attached',1 if attached else 0),'Fall':scalar('FallSeconds',fall)}
    out(custom(shared+'\nreturn (shape.position(UV,age,Meta.g,Attached,Fall)-shape.base(UV,Attached))*float3(1,-1,1);',inputs),'WORLD_POSITION_OFFSET')
    out(custom(shared+'''float2 q=float2(UV.x,clamp(UV.y,.002,.998));
float3 du=shape.position(q+float2(.001,0),age,Meta.g,Attached,Fall)-shape.position(q-float2(.001,0),age,Meta.g,Attached,Fall);
float3 dv=shape.position(q+float2(0,.001),age,Meta.g,Attached,Fall)-shape.position(q-float2(0,.001),age,Meta.g,Attached,Fall);
return normalize(cross(dv,du))*float3(1,-1,1);''',inputs),'NORMAL')
    out(custom('return float3(.095,.22,.036);',{}),'BASE_COLOR');out(scalar('Roughness',.11),'ROUGHNESS');out(scalar('Specular',.55),'SPECULAR')
    out(scalar('Opacity',.78) if attached else custom('float age=frac(T/2.35+Meta.r)*2.35;return step(1.48,age)*(1-step(1.48+Fall,age))*.85;',inputs,1),'OPACITY')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)
(ROOT/'Receipts/materials.json').write_text(json.dumps({'saved':saved,'tests_run':False},indent=2));print('RADIAL_DRIP_MATERIALS_SAVED',len(saved))
