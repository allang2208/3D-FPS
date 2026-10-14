"""Replace only the six HK416 fitted meshes, preserving the active asset paths."""
import json,re
from pathlib import Path
import unreal as u
from runpy import run_path
O=Path(__file__).parent;entries=json.loads((O/'manifest.json').read_text());sources=json.loads((O/'sources.json').read_text())
apply_hk416_finish=run_path(str(O.parents[2]/'SourceAssets/WeaponSurface20260930/HK416/current_bindings.py'))['apply_current_bindings']
D='/Game/Weapons/TacticalDevices20260913/DualFit20261008/HK416';A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
targets={D+f'/SM_{e["kind"]}_{e["side"]}' for e in entries.values()}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
pending_path=O/'pending-import.json';pending=json.loads(pending_path.read_text()) if pending_path.exists() else []
if targets.intersection(dirty).difference(pending):raise RuntimeError('Unsaved HK416 edits outside this import batch; preserve editor state')
report={'saved':{},'runtime_tested':False};receipt=O/'import-receipt.json'
def clean(s):return re.sub(r'[._]\d{3}$','',s)
flag=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for key,e in entries.items():
        name=f'SM_{e["kind"]}_{e["side"]}';path=D+'/'+name;existing=u.load_asset(path)
        pending_path.write_text(json.dumps([path]))
        if existing:
            existing.get_editor_property('asset_import_data').set_editor_property('remove_degenerates',False)
            # These six meshes are full replacements with explicit source material
            # bindings below. Reset the old slot table before FBX rebuild so UE
            # does not preserve the discarded Tactical_Fitted_Bearing section.
            # The importer then builds sections against the new FBX slot table.
            existing.set_editor_property('static_materials',[])
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        options.reset_to_fbx_on_material_conflict=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=e['fbx'];task.destination_path=D;task.destination_name=name;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        pending_path.write_text(json.dumps([path]));A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not task.imported_object_paths or mesh is None:raise RuntimeError('Import failed '+key)
        bindings={clean(n):p for n,p in e['materials'].items()};bindings.update({m['slot']:m['path'] for m in sources[e['kind']]['materials']})
        slots=list(mesh.static_materials)
        for i,s in enumerate(slots):
            label=clean(str(s.material_slot_name));material_path=bindings.get(label)
            if not material_path:raise RuntimeError('Unexpected material '+key+' '+label)
            mat=u.load_asset(material_path)
            if mat is None:raise RuntimeError('Missing material '+material_path)
            s.material_interface=mat
            original=next((m['slot'] for m in sources[e['kind']]['materials'] if m['path']==material_path),None)
            if original and e['kind']!='blessed_laser':s.material_slot_name=original
            slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        apply_hk416_finish(mesh)
        for name,pos in e['sockets'].items():
            socket=mesh.find_socket(name)
            if socket is None:socket=u.StaticMeshSocket(outer=mesh);socket.socket_name=name;mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
        E.set_metadata_tag(mesh,'TacticalMount','HK416 original rail clamp; native emitter/clamp preserved; no generated bridge')
        E.set_metadata_tag(mesh,'SourceDevice',e['source'])
        if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed '+key)
        pending_path.write_text('[]')
        report['saved'][key]={'path':mesh.get_path_name(),'sockets':e['sockets'],'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name()} for s in mesh.static_materials]}
        receipt.write_text(json.dumps(report,indent=2),encoding='utf-8');print('HK416_NATIVE_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(flag))
report['status']='six_native_rail_variants_saved';receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
