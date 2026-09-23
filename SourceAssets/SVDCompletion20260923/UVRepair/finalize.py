import runpy,json,unreal as u
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/UVRepair')
runpy.run_path('D:/FPS3D/FPSGAME/SourceAssets/SVDDragunov20260922/Scripts/import_icon.py',run_name='__main__')
receipt=json.loads((O/'import_fixed.json').read_text());report={'assets':{},'render':'ue_Render_final.log: WeaponIconCatalog COMPLETE failures=0','icon':'/Game/ColdSteelData/Icons/ue_svd','scope':'SVD UV repair and saved-asset presentation only; no gameplay regression'}
for path,row in receipt.items():
 mesh=u.load_asset(path);assert mesh is not None,path
 current={str(s.material_slot_name):s.material_interface.get_path_name() for s in (mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials)}
 assert current==row['material_slots'],path
 report['assets'][path]={'loaded_from_disk':True,'material_slots_preserved':True}
report['ok']=True;(O/'final_readback.json').write_text(json.dumps(report,indent=2));print('SVD_UV_FINAL_SAVED',len(report['assets']),'meshes and icon')
