from pathlib import Path
import unreal as u, hashlib,json
O=Path(__file__).resolve().parent
paths={'action':'/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action','native':'/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native','advanced':'/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Advanced','host':'/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9'}
r={}
for k,p in paths.items():
    m=u.load_asset(p)
    path=Path(u.Paths.project_content_dir())/(p[6:]+'.uasset')
    slots=m.materials if k=='host' else m.static_materials
    r[k]={'path':p,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'lods':[]}
    if k!='host':
        sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        r[k]['lods']=[m.get_num_triangles(i) for i in range(sub.get_lod_count(m))]
    if k=='action':
        t=u.AssetExportTask();t.object=m;t.filename=str(O/'Inputs/action.fbx');t.exporter=u.StaticMeshExporterFBX();t.options=u.FbxExportOption()
        t.options.level_of_detail=False;t.options.collision=False;t.automated=True;t.prompt=False;t.replace_identical=True
        if not u.Exporter.run_asset_export_task(t):raise RuntimeError('active action export')
(O/'Inputs/current.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('M24_CURRENT_JUNCTION_INPUTS')
