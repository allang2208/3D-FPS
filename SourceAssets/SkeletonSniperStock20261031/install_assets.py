"""Import only owned stock meshes/materials and the corrected catalog icons."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1];D='/Game/Weapons/SkeletonSniperStock20261031'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=dict(complete=False,saved=[],runtime_tested=False,host_partitioned=False)
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
    receipt['saved'].append(a.get_path_name())
def import_tex(file,name,folder,kind):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(folder+'/'+name)
    tex.set_editor_property('srgb',kind in ('color','icon'))
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_MASKS if kind=='data' else u.TextureCompressionSettings.TC_EDITOR_ICON if kind=='icon' else u.TextureCompressionSettings.TC_DEFAULT)
    if kind=='normal':tex.set_editor_property('flip_green_channel',True)
    if kind=='icon':
        for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,max_texture_size=1024).items():tex.set_editor_property(k,v)
    save(tex);return tex
tex={key:import_tex(O/'Textures'/file,'T_SniperStock_'+key,D+'/Textures',kind) for key,file,kind in [('Color','texture_0.png','color'),('Normal','normal.png','normal'),('Roughness','roughness.png','data'),('Metallic','metallic.png','data'),('Mask','surface_mask.png','data')]}
path=D+'/Materials/M_SniperStockSurface'
fresh=not E.does_asset_exist(path)
master=E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',path) if fresh else load(path)
for prop in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):
    master.set_editor_property(prop,False)
if fresh:
    m=L.create_material_expression(master,u.MaterialExpressionTextureSampleParameter2D,-500,600);m.set_editor_property('parameter_name','SourceMetallic');m.set_editor_property('texture',tex['Metallic']);m.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    L.connect_material_property(m,'R',u.MaterialProperty.MP_METALLIC)
L.recompile_material(master);save(master)
materials={}
for name in ('SniperStock_MeshySurface','SniperStock_Interface'):
    path=D+'/Materials/MI_'+name
    mi=load(path) if E.does_asset_exist(path) else A.create_asset('MI_'+name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,master)
    for k,v in dict(SourceColorWeight=1 if name.endswith('MeshySurface') else 0,SourceRoughnessWeight=1 if name.endswith('MeshySurface') else 0,Roughness=.5 if name.endswith('MeshySurface') else .36,SourceRoughnessPivot=.5,GrainRoughness=0,MottleRoughness=0,MottleColor=0,Stipple=0,EdgeWear=0,EdgeHighlight=0,CavityDarken=0,CavityRoughness=0,HandlingPolish=0,ScratchAmount=0,MaskUVChannel=0,AOStrength=0).items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    L.set_material_instance_texture_parameter_value(mi,'SurfaceMask',tex['Mask'])
    if name.endswith('MeshySurface'):
        for param,key in [('SourceBaseColor','Color'),('SurfaceNormal','Normal'),('SourceRoughness','Roughness'),('SourceMetallic','Metallic')]:L.set_material_instance_texture_parameter_value(mi,param,tex[key])
    else:
        L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(.026,.029,.031,1))
        L.set_material_instance_texture_parameter_value(mi,'SourceMetallic',load('/Engine/EngineResources/WhiteSquareTexture'))
    L.update_material_instance(mi);save(mi);materials[name]=mi
flag='Interchange.FeatureFlags.Import.FBX';prev=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    spec=json.loads((O/'authoring.json').read_text())
    for family,row in spec['models'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Meshes';task.destination_name='SM_SniperSkeleton_'+family;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);mesh=load(task.destination_path+'/'+task.destination_name)
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
        sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=family=='SVD';bs.use_mikk_t_space=family!='SVD';bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True;u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
        lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False;lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))];sub.set_lods(mesh,lod)
        E.set_metadata_tag(mesh,'Source',str(O/('SkeletonSniperStock_'+family+'_Editable.blend')));save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prev))
mapping={
 'stock_sniper_skeleton_stock':['stock_sniper_skeleton_stock'],
 'ue_m24_bolt_false':['ue_m24_bolt_false','ue_m24_category_bolt'],
 'bolt_m24_carbon_light_bolt':['bolt_m24_carbon_light_bolt','ue_m24_bolt_m24_carbon_light_bolt'],
 'ue_m24_reargrip_false':['ue_m24_reargrip_false'],
 'body_m24_advanced_action':['body_m24_advanced_action','ue_m24_body_m24_advanced_action','ue_m24_category_body','category_body'],
 'ue_m24_body_false':['ue_m24_body_false'],
 'stock_m24_cheekrest':['stock_m24_cheekrest','ue_m24_stock_m24_cheekrest'],
 'ue_svch_stock_false':['ue_svch_stock_false'],
}
folder=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
for source,keys in mapping.items():
    for key in keys:
        target=folder/(key+'.png');backup=O/'Before'/(key+'.png')
        if target.exists() and not backup.exists():shutil.copy2(target,backup)
        shutil.copy2(O/'Icons'/(source+'.png'),target)
        import_tex(target,'T_'+key,'/Game/UI/AttachmentIcons20260913/FramedFirearms','icon')
receipt.update(complete=True,icon_mapping=mapping,source_triangles=198545)
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SKELETON_SNIPER_ASSETS_SAVED',len(receipt['saved']))
