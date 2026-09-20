"""Reimport the edited drum meshes and production icons in the open editor."""
import json, shutil
from pathlib import Path
import unreal as u

O = Path('D:/FPS3D/FPSGAME/SourceAssets/LargeDrumUpgrade20260920')
R = O/'Revisions/RemoveTowerRibs20260920'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
S = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is active; stop it before editing these assets')
sources = json.loads((O/'Reference/current_assets.json').read_text())
receipt_path = R/'install_receipt.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'meshes':{},'icons':{},'game_tested':False}

def record(): receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False): raise RuntimeError('Save failed '+obj.get_path_name())
def import_file(file,path,options=None):
    folder,name = path.rsplit('/',1)
    task = u.AssetImportTask(); task.filename=str(file); task.destination_path=folder; task.destination_name=name
    task.automated=True; task.replace_existing=True; task.replace_existing_settings=True; task.save=False
    if options: task.options=options
    A.import_asset_tasks([task])
    if not task.imported_object_paths: raise RuntimeError('Import returned no objects: '+str(file))
    obj=u.load_asset(path)
    if not obj: raise RuntimeError('Import failed '+path)
    return obj

for gun,source in sources.items():
    if receipt['meshes'].get(gun,{}).get('saved'): continue
    path=source['asset']; old=u.load_asset(path)
    prior={str(slot.material_slot_name):slot.material_interface for slot in old.static_materials}
    labels=[entry['slot'] for entry in source['slots']]
    opts=u.FbxImportUI(); opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH; opts.import_as_skeletal=False
    opts.import_materials=False; opts.import_textures=False; opts.import_animations=False
    opts.static_mesh_import_data.combine_meshes=True; opts.static_mesh_import_data.auto_generate_collision=False
    opts.static_mesh_import_data.generate_lightmap_u_vs=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_file(O/'Export'/('SM_'+gun+'_LargeDrum_Upgrade.fbx'),path,opts)
    slots=list(mesh.static_materials); chosen=[]
    for label in labels:
        matches=[slot for slot in slots if str(slot.get_editor_property('imported_material_slot_name'))==label]
        if len(matches)!=1: raise RuntimeError('Cannot map slot '+gun+' '+label)
        slot=matches[0]; slot.material_interface=prior[label]; slot.material_slot_name=label; chosen.append(slot)
    for section in range(mesh.get_num_sections(0)):
        old_index=S.get_lod_material_slot(mesh,0,section)
        label=str(slots[old_index].get_editor_property('imported_material_slot_name'))
        S.set_lod_material_slot(mesh,labels.index(label),0,section)
    mesh.set_editor_property('static_materials',chosen)
    E.set_metadata_tag(mesh,'ModelRevision','LargeDrumUpgrade20260920 / RemoveTowerRibs20260920')
    lod=u.ModelingService.set_lods(path,[1.,.55,.25],True,True)
    if not lod.success: raise RuntimeError(str(lod))
    collision=u.ModelingService.generate_collision(path,'ConvexHulls',3,48,True)
    if not collision.success: raise RuntimeError(str(collision))
    save(mesh)
    receipt['meshes'][gun]={'asset':path,'saved':True,'materials_retained':{k:v.get_path_name() for k,v in prior.items()}}
    record(); print('RIB_REMOVAL_MESH_SAVED '+gun)

icon_folder='/Game/ColdSteelData/AttachmentIcons20260913'
content=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/AttachmentIcons20260913')
backup=R/'Before/InstalledIcons'; backup.mkdir(parents=True,exist_ok=True)
for gun,name in [('M4','magazine_large_drum'),('M4','ue_m4a1_magazine_large_drum'),('AKM','ue_akm_magazine_large_drum'),('QBZ191','ue_qbz191_magazine_large_drum')]:
    if receipt['icons'].get(name,{}).get('saved'): continue
    src=O/'Icons'/(gun+'_magazine_large_drum.png'); dst=content/(name+'.png')
    if dst.exists() and not (backup/dst.name).exists(): shutil.copy2(dst,backup/dst.name)
    shutil.copy2(src,dst)
    texture=import_file(dst,icon_folder+'/'+name)
    texture.srgb=True; texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI
    texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    save(texture)
    receipt['icons'][name]={'asset':texture.get_path_name(),'saved':True}
    record(); print('RIB_REMOVAL_ICON_SAVED '+name)
receipt['status']='models_and_icons_saved'; record()
print('TOWER_RIB_REMOVAL_INSTALLED')
