"""Replace only the three requested G18 meshes and their option icons."""
import unreal as u,json,hashlib,runpy,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'G18Integration20260929';P=O.parents[1]
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
ROOT='/Game/Weapons/G18/Integrated20260929';report={'saved':[],'meshes':{},'runtime_tested':False}

def save(asset):
    if not E.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(report,indent=2))

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing material '+path)
    return obj

holo_helpers=runpy.run_path(str(P/'Tools/Weapons/g18_holographic_material.py'))
holo_body=holo_helpers['ensure_holo_body'](save)
holo_helpers['register_wet_material'](holo_body,save)
fix=json.loads((O/'authoring.json').read_text())
materials={
 'M_G18_Magazine':ROOT+'/Materials/M_G18_SourcePBR',
 'M_G18_AttachmentFinish':ROOT+'/Materials/M_G18_AttachmentFinish',
 'M_HoloBody':holo_body.get_path_name(),
 'M_HoloReticle':'/Game/Weapons/M4Holographic/M_HoloReticle',
 'M_Panoramic_Glass':'/Game/Weapons/PanoramicRedDot/M_Panoramic_Glass',
 'M_Panoramic_Reticle':'/Game/Weapons/PanoramicRedDot/M_Panoramic_Reticle',
 'M_Panoramic_Body':ROOT+'/Materials/M_G18_AttachmentFinish'}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,entry in fix.items():
        name='SM_G18_'+key;dest=ROOT+'/Attachments';file=Path(entry['fbx'])
        before=O/'BeforePackages';before.mkdir(exist_ok=True)
        package=P/'Content/Weapons/G18/Integrated20260929/Attachments'/(name+'.uasset')
        if not (before/package.name).exists():shutil.copy2(package,before/package.name)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=load(dest+'/'+name);slots=list(mesh.static_materials)
        for i,s in enumerate(slots):
            label=str(s.material_slot_name)
            if label not in materials:raise RuntimeError('Unmapped repaired material '+label)
            s.material_interface=load(materials[label]);slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        E.set_metadata_tag(mesh,'G18SourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
        E.set_metadata_tag(mesh,'G18AttachmentRepair','20260930: closed shell and measured dovetail optic seat')
        save(mesh);report['meshes'][key]={'path':mesh.get_path_name(),'source':str(file),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

for file in sorted((O/'Icons').glob('*.png')):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=ROOT+'/Icons';task.destination_name=file.stem
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=load(ROOT+'/Icons/'+file.stem);tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(tex)

# Keep the original authoring manifest pointed at the repaired FBX so a later
# explicit full import cannot silently restore the failed geometry.
path=S/'attachment_authoring.json';data=json.loads(path.read_text())
for key,entry in fix.items():data[key]['fbx']=entry['fbx'];data[key]['repair_source']=str(O/'author_repair.py')
path.write_text(json.dumps(data,indent=2))
path=S/'icon_geometry.json';data=json.loads(path.read_text());data.update(json.loads((O/'icon_geometry.json').read_text()));path.write_text(json.dumps(data,separators=(',',':')))
report['status']='repaired_assets_imported_and_saved'
(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
print('G18_ATTACHMENT_REPAIR_SAVED',flush=True)
