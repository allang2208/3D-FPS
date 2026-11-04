"""Save the blade LODs, real translucent Substrate surfaces, mote and framed icon."""
from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
D='/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE active: end play before importing Rift Piercer assets')
if any(p.get_path_name().startswith(D) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved Rift Piercer packages')
saved=[]
def save(obj):
    if isinstance(obj,u.Material):
        errors=L.recompile_material(obj)
        if errors:raise RuntimeError(str(errors))
        L.get_statistics(obj)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    saved.append(obj.get_path_name())
def n(mat,cls,**kw):
    node=L.create_material_expression(mat,cls)
    if kw:node.set_editor_properties(kw)
    return node
def connect(a,out,b,pin):
    names=[str(s) for s in L.get_material_expression_input_names(b)]
    target=next((s for s in names if s.replace(' ','').lower()==pin.replace(' ','').lower()),pin)
    if pin=='Input' and names:target=names[0]
    if not L.connect_material_expressions(a,out,b,target):raise RuntimeError('Pin '+pin+' '+str(names))
def material(name,particle=False):
    m=E.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    m.set_editor_properties(dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE,
        shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=False,used_with_instanced_static_meshes=particle))
    # This task owns these new packages. Reuse nodes when rerunning a failed save.
    for old in L.get_material_expressions(m):L.delete_material_expression(m,old)
    inputs={}
    for key,value in [('Fade',1.),('Age',0.),('HitGlow',0.)]:
        inputs[key]=(n(m,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value),'')
    inputs['Tint']=(n(m,u.MaterialExpressionVectorParameter,parameter_name='Tint',default_value=u.LinearColor(.12,.72,1.,1.)),'RGB')
    if particle:
        data=n(m,u.MaterialExpressionPerInstanceCustomData,data_index=0,const_default_value=1.)
        interp=n(m,u.MaterialExpressionVertexInterpolator);connect(data,'',interp,'Input');inputs['Life']=(interp,'')
        code=(P/'mote.hlsl').read_text(encoding='utf8')
    else:
        inputs['Rim']=(n(m,u.MaterialExpressionFresnel,exponent=2.5),'')
        pos=n(m,u.MaterialExpressionPreSkinnedPosition)
        interp=n(m,u.MaterialExpressionVertexInterpolator);connect(pos,'',interp,'Input');inputs['P']=(interp,'')
        code=(P/'phantom.hlsl').read_text(encoding='utf8')
    custom=n(m,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for key,(node,out) in inputs.items():connect(node,out,custom,key)
    rgb=n(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);connect(custom,'',rgb,'Input')
    alpha=n(m,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);connect(custom,'',alpha,'Input')
    trans=n(m,u.MaterialExpressionOneMinus);connect(alpha,'',trans,'Input')
    surface=n(m,u.MaterialExpressionSubstrateUnlitBSDF)
    connect(rgb,'',surface,'EmissiveColor');connect(trans,'',surface,'TransmittanceColor')
    if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Missing Substrate front')
    L.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
    response=n(m,u.MaterialExpressionTemporalResponsivenessOutput)
    one=n(m,u.MaterialExpressionConstant,r=1.)
    connect(one,'',response,'Input')
    save(m);return m
phantom=material('M_RiftPiercer_Phantom');motes=material('M_RiftPiercer_Mote',True)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.set_editor_properties(dict(automated_import_should_detect_type=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_materials=False,import_textures=False))
opt.static_mesh_import_data.set_editor_properties(dict(combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS,vertex_color_import_option=u.VertexColorImportOption.REPLACE))
def import_mesh(file,name):
    t=u.AssetImportTask();t.set_editor_properties(dict(filename=str(P/'Export'/file),destination_path=D,destination_name=name,options=opt,automated=True,replace_existing=True,save=False))
    A.import_asset_tasks([t]);mesh=E.load_asset(D+'/'+name)
    if not mesh:raise RuntimeError('Mesh import failed '+name)
    return mesh
blade=import_mesh('SM_FrostSword_Blade_rift_piercer_LOD0.fbx','SM_FrostSword_Blade_rift_piercer')
finish=E.load_asset('/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze')
if not finish:raise RuntimeError('Current crystal material missing')
for index in range(len(blade.static_materials)):blade.set_material(index,finish)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for level in [1,2]:
    if sub.import_lod(blade,level,str(P/'Export'/('SM_FrostSword_Blade_rift_piercer_LOD'+str(level)+'.fbx')))<0:raise RuntimeError('LOD import failed')
save(blade)
mesh=import_mesh('SM_RiftPiercer_Mote.fbx','SM_RiftPiercer_Mote');mesh.set_material(0,motes);save(mesh)
key='ue_frost_crystal_sword_blade_1_rift_piercer'
t=u.AssetImportTask();t.set_editor_properties(dict(filename=str(P/'Export/RiftPiercer_Icon_Framed.png'),destination_path='/Game/ColdSteelData/AttachmentIcons20260913',destination_name=key,automated=True,replace_existing=True,save=False,factory=u.TextureFactory()))
A.import_asset_tasks([t]);icon=E.load_asset(t.destination_path+'/'+key)
icon.set_editor_properties(dict(srgb=True,lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS));save(icon)
(P/'import-receipt.json').write_text(json.dumps({'assets_saved':True,'assets':saved,'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
u.log('RIFT_PIERCER_ASSETS_SAVED')
