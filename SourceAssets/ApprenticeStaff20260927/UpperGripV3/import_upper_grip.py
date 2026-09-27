"""Install and save the eight meshes changed by the upper grip. No play/test run."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(r'D:/FPS3D/FPSGAME/SourceAssets/ApprenticeStaff20260927')
DEST='/Game/Weapons/ApprenticeStaff20260927'
RECEIPT=ROOT/'UpperGripV3/import-receipt.json'
names={'SM_Staff_Body','SM_Staff_grip_lining_false',
       'SM_Staff_grip_lining_alloy_grip','SM_Staff_grip_lining_pine_grip','SM_Staff_grip_lining_sandalwood_grip',
       'SM_Staff_shaft_rune_eagle_eye_rune','SM_Staff_shaft_rune_crit_rune','SM_Staff_shaft_rune_storm_rune'}
entries=[e for e in json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8')) if e['name'] in names]
if len(entries)!=len(names):raise RuntimeError('Incomplete upper grip source exports.')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before writing staff assets.')
targets={DEST+'/Meshes/'+e['name'] for e in entries}
conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if conflicts:raise RuntimeError('Unsaved changes in staff assets: '+', '.join(conflicts))

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
tools=u.AssetToolsHelpers.get_asset_tools()
options=u.FbxImportUI()
for key,value in {'import_mesh':True,'import_as_skeletal':False,'mesh_type_to_import':u.FBXImportType.FBXIT_STATIC_MESH,
                  'import_materials':False,'import_textures':False}.items():options.set_editor_property(key,value)
data=options.get_editor_property('static_mesh_import_data')
for key,value in {'combine_meshes':True,'auto_generate_collision':False,'import_uniform_scale':1,
                  'normal_import_method':u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                  'reorder_material_to_fbx_order':True}.items():data.set_editor_property(key,value)
saved=[]
for entry in entries:
    task=u.AssetImportTask()
    for key,value in {'filename':entry['fbx'],'destination_path':DEST+'/Meshes','destination_name':entry['name'],
                      'automated':True,'replace_existing':True,'replace_existing_settings':True,
                      'save':False,'options':options}.items():task.set_editor_property(key,value)
    tools.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/Meshes/'+entry['name'])
    if not asset:raise RuntimeError('Import failed: '+entry['name'])
    for i,slot in enumerate(asset.get_editor_property('static_materials')):
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        named=str(slot.get_editor_property('material_slot_name'))
        name=imported if imported in entry['materials'] else named if named in entry['materials'] else entry['materials'][min(i,len(entry['materials'])-1)]
        if not name.startswith('M_Staff_'):name='M_Staff_Wood'
        material=u.load_asset(DEST+'/Materials/'+name)
        if not material:raise RuntimeError('Missing authored material: '+name)
        asset.set_material(i,material)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+entry['name'])
    saved.append(asset.get_path_name())
    RECEIPT.write_text(json.dumps({'revision':3,'complete':False,'saved_assets':saved,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
RECEIPT.write_text(json.dumps({'revision':3,'complete':True,'saved_assets':saved,'grip_center_z_cm':32,
    'grip_limits_z_cm':[22,42],'tested':False,'rendered':False,'editor_restarted':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('STAFF_UPPER_GRIP_V3_SAVED meshes='+str(len(saved)))
