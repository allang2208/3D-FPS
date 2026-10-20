"""Snapshot current shared animation dependencies after the parallel writer exits."""
import gzip,hashlib,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();out=O/'CurrentSource';out.mkdir(exist_ok=True)
old=json.loads((O.parent/'R7NativeV9/compressed_inputs.json').read_text())
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
names=[u.Name(n) for n in old['names']]
def digest(path):return hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def xf(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
data={'names':old['names'],'parents':old['parents'],'reader':'COMPRESSED','clips':{}}
for role,spec in old['clips'].items():
 path=spec['path'];sha=digest(path);seq=u.load_asset(path);length=seq.get_play_length()
 assert abs(length-spec['duration'])<.00001,'Shared clock changed; preserve source'
 times=[min(i/120,length) for i in range(len(spec['frames']))];frames=[]
 for time in times:
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,time,opts)
  frames.append([xf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
 assert sha==digest(path),'Animation changed during collection'
 data['clips'][role]={'path':path,'duration':length,'fps':120,'times':times,'frames':frames,'sha256':sha}
 print('SVCH_SHARED_SOURCE_COLLECTED',role,len(times),sha,flush=True)
with gzip.open(out/'motion.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
(out/'manifest.json').write_text(json.dumps({k:{a:b for a,b in v.items() if a not in ('frames','times')} for k,v in data['clips'].items()},indent=2))
print('SVCH_CURRENT_SOURCE_SAVED',flush=True)
