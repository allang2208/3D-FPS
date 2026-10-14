"""Save only the corrected HK416 stock, retaining its active materials and path."""
import json,re
from pathlib import Path
import unreal as u
from runpy import run_path
O=Path(__file__).parent;P=O.parents[2]
apply_hk416_finish=run_path(str(P/'SourceAssets/WeaponSurface20260930/HK416/current_bindings.py'))['apply_current_bindings']
entry=json.loads((O.parent/'Integration/fitted-models.json').read_text())['models']['HK416']
source=json.loads((O/'sources.json').read_text())['current'];path=entry['asset']
if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved HK416 stock edits')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE state')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=entry['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.options=opt;task.factory=u.FbxFactory();task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
    if not task.imported_object_paths or mesh is None:raise RuntimeError('Stock import failed')
    bindings={v['slot']:v['path'] for v in source['materials']};slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        key=re.sub(r'[._]\d{3}$','',str(s.material_slot_name));s.material_interface=u.load_asset(bindings[key]);slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    apply_hk416_finish(mesh)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'InterfaceAlignment','HK416 original buffer tube axis; 2026-10-08')
    u.EditorAssetLibrary.set_metadata_tag(mesh,'Source',str(O.parent/'Integration/Editable/HK416_TacticalStock.blend'))
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Stock save failed')
    report={'status':'HK416_stock_alignment_saved','asset':mesh.get_path_name(),'source':entry['fbx'],
            'body_alignment_delta_m':entry['body_alignment_delta_m'],
            'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name()} for s in mesh.static_materials],
            'receiver_facing_interface_preserved':True,'other_weapons_modified':False,'game_tested':False}
    (O/'import-receipt.json').write_text(json.dumps(report,indent=2))
    print('HK416_STOCK_ALIGNMENT_SAVED',json.dumps(report))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
