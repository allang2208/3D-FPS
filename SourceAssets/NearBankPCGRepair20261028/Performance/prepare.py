from pathlib import Path
from datetime import datetime
import json,copy,shutil,hashlib
R=Path(__file__).resolve().parent;P=R.parent
M=json.loads((P/'publish_manifest.json').read_text());jobs=json.loads((P/'Repair/mesh_jobs.json').read_text())
if (R/'source_manifest.json').exists():raise RuntimeError('Use saved performance source rather than overwrite it')
shutil.copy2(P/'publish_manifest.json',R/'source_manifest.json');shutil.copy2(P/'publish_assets.json',R/'source_assets.json');shutil.copy2(P/'installed.json',R/'source_installed.json')
old_count=sum(len(r['transforms']) for r in M['rows']);selected=[];new=[];removed=[]
for job in jobs:
 if '/Collision/SM_RoadSupport_' not in job['asset']:continue
 name=job['asset'].rsplit('/',1)[-1].replace('SM_RoadSupport_','SM_ContinuousRoad_');path='/Game/NativeNearBank20261028/Performance/Meshes/'+name
 j=copy.deepcopy(job);j['asset']=path;j['hidden']=False;selected.append(j)
 source=next(r for r in M['rows'] if r['mesh'].split('.')[0]==job['asset'])
 row=copy.deepcopy(source);row.update(actor='NBPCG_ContinuousRoad',component=name,mesh=path+'.'+name,collision_only=False);new.append(row)
for row in M['rows']:
 if any(k in row['mesh'] for k in ['SM_Lane_Car_','/Repair/Meshes/SM_RoadClosure_','/Repair/Meshes/SM_ParkingApron_']):removed.append(row)
M['rows']=[r for r in M['rows'] if r not in removed]+new
M['counts']['instances']=sum(len(r['transforms']) for r in M['rows']);M['counts']['components']=len(M['rows']);M['counts']['meshes']=len({r['mesh'] for r in M['rows']});M['performance_policy']='distance-and-proxy-20261028'
(R/'manifest.json').write_text(json.dumps(M,separators=(',',':')));(R/'mesh_jobs.json').write_text(json.dumps(selected,separators=(',',':')))
plan=dict(before=old_count,after=M['counts']['instances'],removed_road_instances=sum(len(r['transforms']) for r in removed),new_road_patches=len(new),road_materials=sorted({m for r in removed for m in r['materials']}),collision_footprint_preserved=True)
(R/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
