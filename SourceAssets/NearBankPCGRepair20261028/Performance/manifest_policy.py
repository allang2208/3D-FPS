"""Reapply the saved district performance policy after layout regeneration."""
import copy
def optimize(manifest,jobs):
    if any('/Performance/Meshes/SM_ContinuousRoad_' in r['mesh'] for r in manifest['rows']):return manifest,jobs
    replacement=[];extra=[]
    for job in jobs:
        if '/Collision/SM_RoadSupport_' not in job['asset']:continue
        source=next((r for r in manifest['rows'] if r['mesh'].split('.')[0]==job['asset']),None)
        if source is None:continue
        name=job['asset'].rsplit('/',1)[-1].replace('SM_RoadSupport_','SM_ContinuousRoad_');path='/Game/NativeNearBank20261028/Performance/Meshes/'+name
        j=copy.deepcopy(job);j.update(asset=path,hidden=False);extra.append(j)
        row=copy.deepcopy(source);row.update(actor='NBPCG_ContinuousRoad',component=name,mesh=path+'.'+name,collision_only=False);replacement.append(row)
    if not replacement:raise RuntimeError('Continuous road requires the repaired road support geometry')
    manifest['rows']=[r for r in manifest['rows'] if not any(k in r['mesh'] for k in ['SM_Lane_Car_','/Repair/Meshes/SM_RoadClosure_','/Repair/Meshes/SM_ParkingApron_'])]+replacement
    manifest['counts'].update(instances=sum(len(r['transforms']) for r in manifest['rows']),components=len(manifest['rows']),meshes=len({r['mesh'] for r in manifest['rows']}))
    manifest['performance_policy']='distance-and-proxy-20261028'
    return manifest,jobs+extra
