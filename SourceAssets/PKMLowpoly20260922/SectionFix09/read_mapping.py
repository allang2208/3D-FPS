import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922'
mesh=u.load_asset(P+'/SK_PKM_Manny')
report={'mesh':mesh.get_path_name(),'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),'source':mesh.get_editor_property('asset_import_data').get_first_filename(),'slots':[]}
for i,s in enumerate(mesh.materials):
 try:imported=str(s.get_editor_property('imported_material_slot_name'))
 except Exception as e:imported=str(e)
 report['slots'].append({'index':i,'slot':str(s.material_slot_name),'imported':imported,'material':s.material_interface.get_path_name() if s.material_interface else None})
try:report['lod_info']=[{'map':list(x.lod_material_map)} for x in mesh.get_editor_property('lod_info')]
except Exception as e:report['lod_info_error']=str(e)
(O/'mapping_before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
