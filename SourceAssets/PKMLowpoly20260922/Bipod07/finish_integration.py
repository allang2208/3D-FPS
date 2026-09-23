import unreal as u,json,datetime
from pathlib import Path
O=Path(__file__).parent
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Stop PIE before replacing PKM animations.')
p=O/'import_motion.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
report={'saved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'geometry_receipt':'mesh_reimport.json','bipod_receipt':'bipod_import.json','material_receipt':'surface_import.json','animation_receipt':'motion_import.json','native_build_log':'Saved/pkm07-native-build.log','gameplay_tested':False,'requested_renders':'Blender source model; PKM_07_*.png'}
(O/'integration_complete.json').write_text(json.dumps(report,indent=2))
print('PKM07 final hand actions imported and saved. No game test performed.')
