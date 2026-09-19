import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ResonanceGrip20260913/Integration');P.mkdir(exist_ok=True)
paths={'M4':'/Game/Weapons/M4AngledForegripCompact75/SM_M4_AngledForegrip','AKM':'/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_angled','QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_angled'}
r={}
for k,p in paths.items():
 m=u.load_asset(p);t=u.AssetExportTask();t.object=m;t.filename=str(P/(k+'_reference.fbx'));t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.StaticMeshExporterFBX();o=u.FbxExportOption();o.ascii=False;o.level_of_detail=False;o.collision=False;t.options=o
 if not u.Exporter.run_asset_export_task(t):raise RuntimeError(p)
 r[k]={'path':p,'slots':[{ 'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in m.static_materials]}
(P/'sources.json').write_text(json.dumps(r,indent=2))
