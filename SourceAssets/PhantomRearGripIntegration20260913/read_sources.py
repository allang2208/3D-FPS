import unreal as u,json
from pathlib import Path
P=Path(__file__).parent
paths={'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','AKM':'/Game/Weapons/AKMIntegration/SovietFab/StockV2/SK_AKM_MannyNative','QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SK_QBZ191_Manny'}
out={}
for key,path in paths.items():
    mesh=u.load_asset(path)
    out[key]={'asset':path,'skeleton':mesh.skeleton.get_path_name(),'source_files':list(mesh.get_editor_property('asset_import_data').extract_filenames()),'materials':[{'slot':str(m.material_slot_name),'path':m.material_interface.get_path_name() if m.material_interface else ''} for m in mesh.materials]}
(P/'sources.json').write_text(json.dumps(out,indent=2))
