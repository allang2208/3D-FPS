# Smelting item assets for FPSGAME — headless UE asset builder.
# Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
#      -unattended -nosplash -multiprocess -AllowCommandletRendering
# Authoring APIs verified against 5.8 by Tools/Smelting/probe_matprop.py.
# Does: import SM_Ingot.fbx; author M_Ingot (parametric metal) + M_Ore_Tinted (enhancement-stone
# textures × tint per user 2026-09-24 "矿石用强化石的模型，做材质替换"); then MI_<def> for
# ironIngot/copperIngot/silverIngot/goldIngot and iron_ore/copper_ore/silver_ore/gold_ore.
import unreal

AT=unreal.AssetToolsHelpers.get_asset_tools()
EAL=unreal.EditorAssetLibrary
MEL=unreal.MaterialEditingLibrary
BASE='/Game/Items/Smelting'
INGOT_DIR=BASE+'/Ingot'; ORE_DIR=BASE+'/Ore'
STONE='/Game/Items/EnhancementMaterials/enhancement_stone'
FBX=r'D:\FPS3D\FPSGAME\Saved\IngotPipeline\SM_Ingot.fbx'
LOG=[]

def exists(a):return EAL.does_asset_exist(a)
def load(a):return EAL.load_asset(a)

def ensure_mat(path,name):
    full=path+'/'+name
    if exists(full):return load(full)
    a=AT.create_asset(name,path,unreal.Material,unreal.MaterialFactoryNew())
    LOG.append('M '+full);return a

def expr(m,cls,x=0,y=0):return MEL.create_material_expression(m,cls,x,y)
def scalar(m,name,val,x=0,y=0):
    e=expr(m,unreal.MaterialExpressionScalarParameter,x,y)
    e.set_editor_property('parameter_name',unreal.Name(name));e.set_editor_property('default_value',float(val));return e
def vector(m,name,col,x=0,y=0):
    e=expr(m,unreal.MaterialExpressionVectorParameter,x,y)
    e.set_editor_property('parameter_name',unreal.Name(name))
    e.set_editor_property('default_value',unreal.LinearColor(col[0],col[1],col[2],1.0));return e
def tex(m,texp,x=0,y=0):
    e=expr(m,unreal.MaterialExpressionTextureObject,x,y);e.set_editor_property('texture',load(texp));return e
def to_main(e,prop):
    assert MEL.connect_material_property(e,'',prop),'connect_material_property 失败'   # 3-arg: e -> its material's input
def link(a,b,aout='',bin=''):
    assert MEL.connect_material_expressions(a,aout,b,bin),'connect_material_expressions 失败 %r->%r'%(aout,bin)
# 5.8 的这两个连线 API 名字写错时只静默返回 False，不抛异常：TextureSample 与 Multiply 唯一
# 可用的输出名是 ''（'RGBA'/'rgb' 也可），写 'color' 一律 False —— 原来矿石链路的 'color' 就是
# 这么丢掉的，Multiply 的 A 空输入让 BaseColor 恒为黑，四个矿种渲染完全一致。
# 实测矩阵见 Tools/Smelting/probe_conn_names.py。

# —— 1) Ingot mesh (Interchange FBX import) ——
if not exists(INGOT_DIR+'/SM_Ingot'):
    task=unreal.AssetImportTask()
    task.set_editor_property('filename',FBX)
    task.set_editor_property('destination_path',INGOT_DIR)
    task.set_editor_property('destination_name','SM_Ingot')
    task.set_editor_property('automated',True);task.set_editor_property('replace_existing',True)
    task.set_editor_property('save',True)
    AT.import_asset_tasks([task])
mesh=load(INGOT_DIR+'/SM_Ingot') if exists(INGOT_DIR+'/SM_Ingot') else None
LOG.append('MESH '+('ok' if mesh else 'MISSING'))

# —— 2) Base material: parametric metal (Tint / Metallic / Roughness) ——
def wipe(m):
    if hasattr(MEL,'delete_expression'):
        for old in list(m.get_editor_property('expressions')):MEL.delete_expression(old)
print('CONN_SIG',unreal.MaterialEditingLibrary.connect_material_expressions.__doc__)
for stale in (BASE+'/M_Ore_Tinted',BASE+'/M_Ingot'):
    if exists(stale):EAL.delete_asset(stale)   # 5.8 无 delete_expression：残留坏节点只能整包重建
m_ingot=ensure_mat(BASE,'M_Ingot');wipe(m_ingot)
to_main(vector(m_ingot,'Tint',(0.55,0.56,0.60),-600,0),unreal.MaterialProperty.MP_BASE_COLOR)
to_main(scalar(m_ingot,'Metallic',1.0,-600,300),unreal.MaterialProperty.MP_METALLIC)
to_main(scalar(m_ingot,'Roughness',0.45,-600,600),unreal.MaterialProperty.MP_ROUGHNESS)
EAL.save_asset(BASE+'/M_Ingot');LOG.append('M_Ingot wired')

# —— 3) Base material: ore。USE_TEX=True 用强化石贴图（TextureSample 正确采样节点）×Tint；
#         若 headless 编译仍失败，把 USE_TEX 改 False 落回纯参数母质（Tint 区分矿种）。——
USE_TEX=True
m_ore=ensure_mat(BASE,'M_Ore_Tinted');wipe(m_ore)
tint=vector(m_ore,'Tint',(1.0,1.0,1.0),-900,300)
if USE_TEX:
    def sample(m,texp,styp,x=0,y=0):
        e=expr(m,unreal.MaterialExpressionTextureSample,x,y)
        e.set_editor_property('texture',load(texp));e.set_editor_property('sampler_type',styp);return e
    sb=sample(m_ore,STONE+'/T_enhancement_stone_0_Base_Color',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,-900,0)
    mul=expr(m_ore,unreal.MaterialExpressionMultiply,-500,100)
    link(sb,mul,'','A');link(tint,mul,'','B')
    to_main(mul,unreal.MaterialProperty.MP_BASE_COLOR)
    sn=sample(m_ore,STONE+'/T_enhancement_stone_0_Normal',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,-900,-400)
    to_main(sn,unreal.MaterialProperty.MP_NORMAL)
    to_main(scalar(m_ore,'Metallic',0.15,-500,600),unreal.MaterialProperty.MP_METALLIC)
    to_main(scalar(m_ore,'Roughness',0.62,-500,800),unreal.MaterialProperty.MP_ROUGHNESS)
    LOG.append('M_Ore_Tinted wired (textured)')
else:
    to_main(tint,unreal.MaterialProperty.MP_BASE_COLOR)
    to_main(scalar(m_ore,'Metallic',0.15,-600,300),unreal.MaterialProperty.MP_METALLIC)
    to_main(scalar(m_ore,'Roughness',0.6,-600,600),unreal.MaterialProperty.MP_ROUGHNESS)
    LOG.append('M_Ore_Tinted wired (parametric)')
EAL.save_asset(BASE+'/M_Ore_Tinted')

if mesh:
    sm=mesh.get_editor_property('static_materials')
    if len(sm)>0:
        sm[0].set_editor_property('material_interface',m_ingot)
        mesh.set_editor_property('static_materials',sm)
        EAL.save_asset(INGOT_DIR+'/SM_Ingot');LOG.append('ingot slot -> M_Ingot')

# —— 4) Instances (C++ resolves MI_<Definition>) ——
def make_mi(full,parent,vec,sca):
    folder,name=full.rsplit('/',1)
    a=load(full) if exists(full) else AT.create_asset(name,folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    a.set_editor_property('parent',parent)
    for k,v in (vec or {}).items():MEL.set_material_instance_vector_parameter_value(a,k,unreal.LinearColor(v[0],v[1],v[2],1.0))
    for k,v in (sca or {}).items():MEL.set_material_instance_scalar_parameter_value(a,k,float(v))
    MEL.update_material_instance(a)
    EAL.save_asset(full);LOG.append('MI '+full)

INGOTS={'ironIngot':((0.55,0.56,0.60),0.50),'copperIngot':((0.75,0.33,0.19),0.40),
        'silverIngot':((0.85,0.88,0.92),0.25),'goldIngot':((0.93,0.65,0.18),0.30)}
for defid,(col,rough) in INGOTS.items():
    make_mi(INGOT_DIR+'/MI_'+defid,m_ingot,{'Tint':col},{'Metallic':1.0,'Roughness':rough})
ORES={'iron_ore':(0.78,0.60,0.50),'copper_ore':(0.40,0.80,0.68),
      'silver_ore':(0.82,0.90,1.00),'gold_ore':(1.00,0.80,0.32)}
for defid,col in ORES.items():
    make_mi(ORE_DIR+'/MI_'+defid,m_ore,{'Tint':col},None)

EAL.save_directory(BASE)
print('SMELTING_ASSETS_OK');print('\n'.join(LOG))
