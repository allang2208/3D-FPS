import unreal as u, json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927'); O=R/'Exported'; O.mkdir(exist_ok=True)
r=json.loads((R/'current_scene.json').read_text(encoding='utf8'))
paths=sorted({m['mesh'] for a in r['actors'] for m in a['meshes'] if m['mesh'].startswith('/Game/Props/') and not any(n in m['mesh'] for n in ['BronzeTorch','WaterFX','Overflow','WaterWaves','GamedevPortal_Energy'])})
out=[]
for p in paths:
    m=u.load_asset(p); f=O/(m.get_name()+'.fbx')
    task=u.AssetExportTask(); task.object=m; task.filename=str(f); task.automated=True; task.prompt=False; task.replace_identical=False; task.exporter=u.StaticMeshExporterFBX(); opts=u.FbxExportOption(); opts.ascii=False; opts.level_of_detail=False; opts.collision=False; task.options=opts
    if not u.Exporter.run_asset_export_task(task): raise RuntimeError('Export failed: '+p)
    b=m.get_bounding_box()
    def v(x):return [x.x,x.y,x.z]
    out.append(dict(mesh=p,file=str(f),bounds=[v(b.min),v(b.max)],materials=[str(x.material_slot_name) for x in m.static_materials]))
(R/'exported_meshes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('Exported '+str(len(out))+' existing meshes to independent preview source directory; no assets or maps saved.')
