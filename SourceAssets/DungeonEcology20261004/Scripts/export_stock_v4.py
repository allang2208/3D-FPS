"""Read stock geometry for the requested root alignment and asset reuse work."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Sources/StockV4';OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((ROOT/'Config/room.json').read_text('utf8'))
paths={p['mesh'] for r in cfg['rooms'] for p in r['plants']}
paths.add('/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Meshes/SM_WBK_SocketPlug')
for name in ('Tree_L_01','Tree_M_01','Tree_M_02','Tree_M_03','Tree_M_04'):
    paths.add('/Game/RuralAustralia/StaticMeshes/Vegetation/'+name+'/SM_'+name)
rows=[]
for path in sorted(paths):
    m=u.load_asset(path)
    if not m:raise RuntimeError(path)
    dest=OUT/(path.rsplit('/',1)[-1]+'.fbx')
    task=u.AssetExportTask();task.object=m;task.filename=str(dest);task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if not dest.exists() and not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+path)
    b=m.get_bounds();row=dict(asset=path,fbx=str(dest),origin_cm=[b.origin.x,b.origin.y,b.origin.z],extent_cm=[b.box_extent.x,b.box_extent.y,b.box_extent.z],materials=[s.material_interface.get_path_name() for s in m.static_materials])
    if 'RuralAustralia' in path:
        row['material_parameters']=[]
        for s in m.static_materials:
            mat=s.material_interface;ml=u.MaterialEditingLibrary
            row['material_parameters'].append(dict(material=mat.get_path_name(),scalars={str(k):ml.get_material_instance_scalar_parameter_value(mat,k) for k in ml.get_scalar_parameter_names(mat)},textures={str(k):str(ml.get_material_instance_texture_parameter_value(mat,k).get_path_name()) for k in ml.get_texture_parameter_names(mat) if ml.get_material_instance_texture_parameter_value(mat,k)}))
    rows.append(row)
    u.log('ECOLOGY_STOCK_EXPORTED '+path)
(OUT/'assets.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
for name in ('T_LC_GroundSoilExcavated_00A_Height',):
    dest=OUT/(name+'.png');task=u.AssetExportTask();task.object=u.load_asset('/Game/UnrealNormandy/Textures/'+name);task.filename=str(dest);task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterPNG()
    if not dest.exists() and not u.Exporter.run_asset_export_task(task):raise RuntimeError('Soil height export')
u.log('ECOLOGY_STOCK_EXPORT_COMPLETE')
