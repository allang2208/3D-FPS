"""Save three fitted static grip skins with WS materials and the M24 factory icon."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1];D='/Game/Weapons/M24/RearGrip20261029'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
R=dict(complete=False,saved=[],runtime_tested=False,geometry_changed=False,animation_changed=False)
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    R['saved'].append(a.get_path_name());(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
if any(p.get_name().startswith(D) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved rear-grip edits retained')
def texture(name,normal):
    t=u.AssetImportTask();t.filename=str(O/'Textures'/(name+'.png'));t.destination_path=D+'/Textures';t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);a=load(t.destination_path+'/'+name)
    a.srgb=False;a.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS
    a.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON
    if normal:a.flip_green_channel=True
    save(a);return a
mask=texture('T_M24_GripSurfaceMask',False)
path=D+'/Materials/M_M24RearGripSurface'
master=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',path)
for k,v in dict(automatically_set_usage_in_editor=False,used_with_skeletal_mesh=False,used_with_morph_targets=False,used_with_clothing=False).items():master.set_editor_property(k,v)
errors=list(L.recompile_material(master) or [])
if errors:raise RuntimeError('Rear grip material compile '+str(errors[:4]))
save(master)
variants=json.loads((O/'authoring.json').read_text())['variants']
material={}
for row in variants:
    key=row['id'];normal=texture('T_M24_'+key+'_N',True);path=D+'/Materials/MI_M24_'+key
    mi=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolymer',path)
    L.set_material_instance_parent(mi,master)
    color={'phantom_reargrip':(.012,.013,.013),'stable_antislip_reargrip':(.016,.016,.015),'balanced_reargrip':(.022,.022,.021)}[key]
    L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1))
    for k,v in dict(Metallic=0,EdgeMetallic=0,Specular=.42,Roughness={'phantom_reargrip':.50,'stable_antislip_reargrip':.67,'balanced_reargrip':.56}[key],
        MaskUVChannel=0,SourceColorWeight=0,SourceRoughnessWeight=0,EdgeWear=0,EdgeHighlight=0,ScratchAmount=0,CavityDarken=0,CavityRoughness=0,HandlingPolish=0).items():
        L.set_material_instance_scalar_parameter_value(mi,k,v)
    L.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',normal)
    L.set_material_instance_texture_parameter_value(mi,'SurfaceMask',mask)
    L.update_material_instance(mi);save(mi);material[key]=mi
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for row in variants:
        key=row['id'];opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Meshes';task.destination_name='SM_M24_'+key
        task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
        mesh=load(task.destination_path+'/'+task.destination_name)
        for i in range(len(mesh.static_materials)):mesh.set_material(i,material[key])
        E.set_metadata_tag(mesh,'M24RearGripSource','Original stock-neck conformal surface; offset 0.055-0.16 mm; no hand or host changes')
        save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
icons=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms';key='ue_m24_reargrip_false'
target=icons/(key+'.png');shutil.copy2(O/'Icons/false.png',target)
task=u.AssetImportTask();task.filename=str(target);task.destination_path='/Game/UI/AttachmentIcons20260913/FramedFirearms';task.destination_name='T_'+key
task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);icon=load(task.destination_path+'/'+task.destination_name)
for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,srgb=True,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,max_texture_size=1024).items():icon.set_editor_property(k,v)
save(icon)
R.update(complete=True,shared_icons=['category_reargrip',*['reargrip_'+r['id'] for r in variants]],
    meshes={r['id']:D+'/Meshes/SM_M24_'+r['id'] for r in variants})
(O/'install_receipt.json').write_text(json.dumps(R,indent=2));print('M24_REAR_GRIP_ASSETS_SAVED',len(R['saved']))
