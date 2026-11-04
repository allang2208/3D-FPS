"""Import the actual blade, charge-core material and grayscale workbench icon."""
from pathlib import Path
import unreal as u,json
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
D='/Game/Weapons/FrostCrystalSword20260915/StarMarrow20261102'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE is running; preserve loaded assets')
if any(p.get_path_name().startswith(D) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved StarMarrow assets')
saved=[]
def save(obj):
    if isinstance(obj,u.Material):
        errors=L.recompile_material(obj)
        if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    saved.append(obj.get_path_name())
core=E.load_asset(D+'/M_StarMarrow_Core') if E.does_asset_exist(D+'/M_StarMarrow_Core') else A.create_asset('M_StarMarrow_Core',D,u.Material,u.MaterialFactoryNew())
for n in L.get_material_expressions(core):L.delete_material_expression(core,n)
params={}
for key in ['CoreCharges','CoreFlash','BladeFinishMode']:
    n=L.create_material_expression(core,u.MaterialExpressionScalarParameter)
    n.set_editor_properties(dict(parameter_name=key,default_value=0));params[key]=n
color=L.create_material_expression(core,u.MaterialExpressionVertexColor)
inputs=[('Charges',params['CoreCharges'],''),('Flash',params['CoreFlash'],''),('Mode',params['BladeFinishMode'],''),('Index',color,'R')]
front=L.create_material_expression(core,u.MaterialExpressionSubstrateShadingModels)
front.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
def custom(code,kind):
    n=L.create_material_expression(core,u.MaterialExpressionCustom);n.set_editor_properties(dict(code=code,output_type=kind))
    pins=[]
    for k,_,_ in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',k);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for k,v,o in inputs:L.connect_material_expressions(v,o,n,k)
    return n
base=custom('return Mode>7.5&&Mode<8.5?float3(.42,.035,.065):float3(.12,.36,.52);',u.CustomMaterialOutputType.CMOT_FLOAT3)
glow=custom('float on=step(Index*3-.1,Charges); float3 tint=Mode>7.5&&Mode<8.5?float3(1,.55,.38):float3(.35,.72,1); return tint*(.06+on*1.3+Flash*5);',u.CustomMaterialOutputType.CMOT_FLOAT3)
rough=custom('return Mode>8.5?.09:.16;',u.CustomMaterialOutputType.CMOT_FLOAT1)
metal=L.create_material_expression(core,u.MaterialExpressionConstant);metal.set_editor_property('r',.38)
for node,pin,prop in [(base,'BaseColor',u.MaterialProperty.MP_BASE_COLOR),(glow,'EmissiveColor',u.MaterialProperty.MP_EMISSIVE_COLOR),(rough,'Roughness',u.MaterialProperty.MP_ROUGHNESS),(metal,'Metallic',u.MaterialProperty.MP_METALLIC)]:
    L.connect_material_expressions(node,'',front,pin);L.connect_material_property(node,'',prop)
L.connect_material_property(front,'',u.MaterialProperty.MP_FRONT_MATERIAL);save(core)
temporal_path=D+'/M_StarMarrow_Core_Whirlwind'
temporal=E.load_asset(temporal_path) if E.does_asset_exist(temporal_path) else E.duplicate_asset(core.get_path_name(),temporal_path)
if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in L.get_material_expressions(temporal)):
    output=L.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
    value=L.create_material_expression(temporal,u.MaterialExpressionConstant);value.set_editor_property('r',1.)
    L.connect_material_expressions(value,'',output,'')
save(temporal)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task=u.AssetImportTask();task.filename=str(P/'Export/SM_FrostSword_Blade_star_marrow_LOD0.fbx');task.destination_path=D;task.destination_name='SM_FrostSword_Blade_star_marrow'
task.options=opt;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
mesh=E.load_asset(D+'/SM_FrostSword_Blade_star_marrow')
if not mesh:raise RuntimeError('Blade import failed')
finish=E.load_asset('/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze')
for i,slot in enumerate(mesh.static_materials):
    mesh.set_material(i,core if 'StarMarrow' in str(slot.material_slot_name) else finish)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for level in [1,2]:
    if sub.import_lod(mesh,level,str(P/'Export'/('SM_FrostSword_Blade_star_marrow_LOD'+str(level)+'.fbx')))<0:raise RuntimeError('LOD import failed')
save(mesh)
icon=P/'Export/StarMarrow_Icon_Framed.png'
if icon.exists():
    t=u.AssetImportTask();t.filename=str(icon);t.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';t.destination_name='ue_frost_crystal_sword_blade_1_star_marrow';t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t])
    tex=E.load_asset(t.destination_path+'/'+t.destination_name)
    tex.set_editor_properties(dict(srgb=True,lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS));save(tex)
(P/'import-receipt.json').write_text(json.dumps({'assets_saved':True,'assets':saved,'mesh':mesh.get_path_name(),'material':core.get_path_name(),'temporal_bindings':{core.get_path_name():temporal.get_path_name()},'game_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
u.log('STAR_MARROW_ASSETS_SAVED')
