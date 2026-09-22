import unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Polish20260922');ROOT.mkdir(exist_ok=True)
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
path='/Game/Monsters/WitchRebuilt/Materials/M_WitchRebuilt_Fabric'
m=u.load_asset(path) if L.does_asset_exist(path) else AT.create_asset('M_WitchRebuilt_Fabric','/Game/Monsters/WitchRebuilt/Materials',u.Material,u.MaterialFactoryNew())
M.delete_all_material_expressions(m)
for k,v in [('two_sided',True),('used_with_skeletal_mesh',True),('used_with_clothing',True)]:m.set_editor_property(k,v)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
slab=M.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
def constant(value):
    n=M.create_material_expression(m,u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant)
    n.set_editor_property('constant' if isinstance(value,tuple) else 'r',u.LinearColor(*value,1) if isinstance(value,tuple) else value);return n
def output(n,p,pin):
    M.connect_material_property(n,'',p);M.connect_material_expressions(n,'',slab,pin)
samples={}
for semantic in ('base_color','normal','roughness'):
    n=M.create_material_expression(m,u.MaterialExpressionTextureSample)
    n.texture=u.load_asset('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_'+semantic)
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic=='normal' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if semantic=='roughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    samples[semantic]=n
output(samples['base_color'],u.MaterialProperty.MP_BASE_COLOR,'BaseColor')
normal=M.create_material_expression(m,u.MaterialExpressionLinearInterpolate);normal.set_editor_property('const_alpha',.4)
M.connect_material_expressions(constant((0.,0.,1.)),'',normal,'A');M.connect_material_expressions(samples['normal'],'RGB',normal,'B')
normalize=M.create_material_expression(m,u.MaterialExpressionNormalize);M.connect_material_expressions(normal,'',normalize,'VectorInput')
output(normalize,u.MaterialProperty.MP_NORMAL,'Normal')
mul=M.create_material_expression(m,u.MaterialExpressionMultiply);mul.set_editor_property('const_b',.25);M.connect_material_expressions(samples['roughness'],'R',mul,'A')
rough=M.create_material_expression(m,u.MaterialExpressionAdd);rough.set_editor_property('const_b',.65);M.connect_material_expressions(mul,'',rough,'A')
output(rough,u.MaterialProperty.MP_ROUGHNESS,'Roughness');output(constant(.28),u.MaterialProperty.MP_SPECULAR,'Specular')
output(constant(0.),u.MaterialProperty.MP_METALLIC,'Metallic');M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
M.recompile_material(m)
if not L.save_loaded_asset(m,False):raise RuntimeError('Fabric save failed')
# Export only the existing licensed skin color for the requested authoring comparison.
for a in L.list_assets('/Game/ZombieFemale',True,False):
    if a.rsplit('/',1)[-1].split('.')[0]=='T_MaidenZombieBody3BaseColor':
        task=u.AssetExportTask();task.object=u.load_asset(a);task.filename=str(ROOT/'skin_preview.png')
        task.exporter=u.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Skin preview export failed')
        break
print('Saved independent opaque fabric; original Witch materials unchanged')
