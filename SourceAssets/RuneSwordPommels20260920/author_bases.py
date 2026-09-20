"""Author three manufacture profiles with Vibe3D in the current editor."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent; E=P/'Interface'; D='/Game/Weapons/AzureRunesword20260913/Pommels20260920/Source'
S=u.ModelingService
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before authoring; keep editor open.')
profiles={
 'MeteorBody':{'steps':8,'rotation':22.5,'points':[[0,-.9],[2.10,-.9],[1.96,-1.22],[1.90,-2.20],[2.02,-2.85],[2.48,-3.65],[3.65,-4.65],[4.40,-5.35],[4.55,-5.85],[4.55,-8.10],[4.15,-8.85],[3.55,-9.72],[3.32,-10.15],[3.32,-10.35],[0,-10.35]]},
 'JadeCrystal':{'steps':32,'rotation':0,'points':[[0,-1.15],[1.80,-1.15],[1.77,-1.65],[1.93,-2.30],[2.34,-3.2],[2.98,-4.40],[3.57,-5.60],[3.88,-6.60],[3.92,-7.20],[3.76,-8.0],[3.30,-8.95],[2.62,-9.90],[1.72,-10.78],[.75,-11.35],[0,-11.58]]},
 'SwiftEndcap':{'steps':64,'rotation':0,'points':[[0,-10.52],[1.42,-10.52],[1.64,-10.63],[1.72,-10.86],[1.70,-11.10],[1.51,-11.4],[1.12,-11.7],[.60,-11.9],[0,-12.02]]}
}
def done(r):
    if not r.success:raise RuntimeError(r.message)
    return r
rows=[]
for name,p in profiles.items():
    h=done(S.create_mesh()).handle
    try:
        done(S.append_revolve_polygon(h,u.Transform(rotation=u.Rotator(roll=0,pitch=0,yaw=p['rotation'])),[u.Vector2D(*v) for v in p['points']],0.,p['steps'],360.,0))
        done(S.recompute_normals(h,35. if name=='MeteorBody' else 50.))
        done(S.auto_uv(h,'PatchBuilder',0))
        path=D+'/SM_RunePommel_'+name
        done(S.save_mesh_to_static_mesh(h,path,False,False,False,True))
        asset=u.load_asset(path)
        task=u.AssetExportTask();task.object=asset;task.filename=str(E/(name+'.fbx'))
        task.automated=True;task.prompt=False;task.replace_identical=True
        task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
        task.options.ascii=False;task.options.level_of_detail=False;task.options.collision=False
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+name)
        rows.append({'name':name,'asset':asset.get_path_name(),'export':task.filename,**p})
        print('POMMEL_PROFILE_AUTHORED',name)
    finally:S.release_mesh(h)
(P/'base_profiles.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
