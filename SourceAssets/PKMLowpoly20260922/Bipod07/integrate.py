import unreal as u,json,datetime
from pathlib import Path
O=Path(__file__).parent
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Stop PIE before replacing PKM assets.')
for name in ['import_surfaces.py','reimport_mesh.py','import_bipod.py','import_motion.py']:
 p=O/name;exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
(O/'integration_complete.json').write_text(json.dumps({'saved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'assets_saved':True,'gameplay_tested':False},indent=2))
print('PKM07 asset integration saved; gameplay test remains with user.')
