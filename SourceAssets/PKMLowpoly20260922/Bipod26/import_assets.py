"""Background import of three articulated pieces with the live PKM finish."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];D='/Game/Weapons/PKMLowpoly20260922/Bipod26'
spec=json.loads((O/'authoring.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();report={}
old=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Bipod07/SM_PKM_Bipod')
if not old:raise RuntimeError('Existing separated PKM bipod missing')
material=old.static_materials[0].material_interface
table=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Finish20/DA_PKM_WetMaterials')
wet={str(k):v.get_path_name() for k,v in table.get_editor_property('wet_materials').items() if v}
if not material or material.get_path_name() not in wet:raise RuntimeError('Existing PKM bipod finish/wet pair unavailable')
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,info in spec['parts'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
        data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(O/'Exports'/(info['name']+'.fbx'))
        task.destination_path=D;task.destination_name=info['name'];task.options=opt;task.factory=u.FbxFactory()
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);path=D+'/'+info['name'];mesh=u.load_asset(path)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Import failed: '+key)
        slots=mesh.static_materials
        for i,slot in enumerate(slots):slot.material_interface=material;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        size=list((mesh.get_bounds().box_extent*2).to_tuple())
        if max(abs(a-b) for a,b in zip(size,info['size_cm']))>.05:raise RuntimeError('FBX unit mismatch '+key+': '+str(size))
        E.set_metadata_tag(mesh,'PKMBipodRevision','Bipod26; fixed mount and legs-down rest pose at measured hinge')
        if not E.save_asset(path,False):raise RuntimeError('Save failed: '+path)
        disk=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
        report[key]={'asset':mesh.get_path_name(),'saved':True,'size_cm':size,
            'material':material.get_path_name(),'wet':wet[material.get_path_name()],
            'sha256':hashlib.sha256(disk.read_bytes()).hexdigest()}
        (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
    icons=P/'Content/ColdSteelData/AttachmentIcons20260913'
    for key in ['ue_pkm_lowpoly_category_bipod','ue_pkm_lowpoly_bipod_pkm_bipod','bipod_false']:
        task=u.AssetImportTask();task.filename=str(icons/(key+'.png'));task.destination_path=D+'/Icons'
        task.destination_name='T_'+key;task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);texture=u.load_asset(D+'/Icons/T_'+key)
        if not texture:raise RuntimeError('Icon import failed: '+key)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
        if not E.save_loaded_asset(texture,False):raise RuntimeError('Icon save failed: '+key)
        report[key]={'asset':texture.get_path_name(),'saved':True,'png':task.filename}
        (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM26_ASSETS_SAVED',json.dumps(report),flush=True)
