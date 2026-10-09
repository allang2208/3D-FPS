import unreal as u,json,sys,importlib
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O));import material_surface
importlib.reload(material_surface)
m=u.load_asset('/Game/Weapons/Super90/Cransh20261006/Materials/M_S90_TTI_Benelli_M4')
material_surface.apply_receiver_surface(m)
if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Material save failed')
r=json.loads((O/'import_receipt.json').read_text());r['saved'].append(m.get_path_name());r['completed']=True
(O/'import_receipt.json').write_text(json.dumps(r,indent=2));print('SUPER90_SURFACE_SAVED',len(r['saved']))
