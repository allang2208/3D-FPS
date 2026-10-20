"""Four SVCH attachment families over the accepted current V9/base action layer."""
from fit_contact import *
import copy,hashlib
outdir=O/'Profiles';outdir.mkdir(exist_ok=True)
idle=pose('idle',0);idlehand=np.linalg.inv(rigid(idle[root]))@idle[hi]
report={'families':{},'source_profile_sha256':json.loads((O/'Inputs/manifest.json').read_text())['profile']['sha256'],
 'meshes_written':False,'shared_sequences_written':False,'runtime_tested':False,'mount':seat.tolist()}

def contact_weight(role,i,p):
 if role=='reload':return float(1.-ease(0,24,i)+ease(255,304,i))
 if role=='reload_empty':return float(1.-ease(0,24,i)+ease(360,416,i))
 if role=='sprint_enter':return float(1.-ease(0,12,i))
 if role=='sprint_exit':return float(ease(36,48,i))
 if role=='sprint_loop':return 0.
 if role=='inspect':
  h=np.linalg.inv(rigid(p[root]))@p[hi]
  return float(1.-ease(.8,5.5,np.linalg.norm(h[:3,3]-idlehand[:3,3])))
 return 1.

def value(local,base):
 v=np.zeros(10);v[:3]=local[:3,3]-base[:3]
 v[3:7]=(R.from_matrix(rigid(local)[:3,:3])*R.from_quat(base[3:7]).inv()).as_quat()
 # No new bone scaling is authored; callers retain the existing local scales.
 v[7:]=np.linalg.norm(local[:3,:3],axis=0)-base[7:]
 return v

# Pose reconstruction is authoring input, shared by the four independent profiles.
stamp=hashlib.sha256((O/'Inputs/profile_before.json').read_bytes()+(O/'Inputs/motion.json.gz').read_bytes()).hexdigest()
cache=O/'base_poses.npz';stampfile=O/'base_poses.sha256'
if cache.exists() and stampfile.exists() and stampfile.read_text()==stamp:
 source=dict(np.load(cache))
else:
 source={}
 for role,c in motion['clips'].items():
  source[role]=np.array([pose(role,k) for k in range(len(c['times']))])
  print('SVCH_SOURCE_POSES',role,len(source[role]),flush=True)
 np.savez_compressed(cache,**source);stampfile.write_text(stamp)
for family,contact in contacts.items():
 out=copy.deepcopy(profile);out['family']=family;familyreport={}
 for role,c in motion['clips'].items():
  dst=next(x for x in out['clips'] if x['base']==c['path']);oldlayer=next(x for x in profile['clips'] if x['base']==c['path'])
  values={j:[] for j in changed};counts=0;peak=0.;swing_peak=0.
  for i,t in enumerate(c['times']):
   p=source[role][i];w=contact_weight(role,i,p);local0=apply(c['frames'][i],oldlayer,t);local=matrices(local0)
   if w>1e-8:
    fulltarget=rigid(p[root])@contact['hand']
    full,info=fit(p,fulltarget)
    target=mix(p[hi],fulltarget,w)
    shoulder=(1-w)*p[ui,:3,3]+w*full[ui,:3,3]
    elbow=(1-w)*p[li,:3,3]+w*full[li,:3,3]
    q,stats=arm(p,'l',target,shoulder,elbow-shoulder,blend=w)
    for j in changed:
     if j in digits:continue
     local[j]=relative(q[parents[j]],q[j])
     local[j,:3,:3]=rigid(local[j])[:3,:3]*local0[j,7:]
    for j in digits:
     # Accepted grouped rotations; native segment translations/scales unchanged.
     local[j,:3,:3]=mixrot(R.from_quat(local0[j,3:7]).as_matrix(),R.from_quat(contact['digits'][j][3:7]).as_matrix(),w)*local0[j,7:]
    counts+=1;peak=max(peak,float(np.linalg.norm(q[ui,:3,3]-p[ui,:3,3])))
    if w>.999:swing_peak=max(swing_peak,stats['wrist_swing_deg'])
   for j in changed:
    v=value(local[j],np.asarray(c['frames'][i][j]));v[7:]=local0[j,7:]-np.asarray(c['frames'][i][j])[7:]
    if values[j] and values[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
    values[j].append(v)
  if counts:
   dst['tracks']=[x for x in dst['tracks'] if ids[x['bone']] not in changed]
   for j in changed:
    a=np.asarray(values[j]);idx=[0] if np.max(abs(a-a[0]))<1e-8 else list(range(len(a)))
    dst['tracks'].append({'bone':names[j],'times':[c['times'][k] for k in idx],'values':np.round(a[idx],10).ravel().tolist()})
  familyreport[role]={'modified_frames':counts,'total_frames':len(c['times']),'max_shoulder_shift_cm':peak,'max_full_contact_wrist_swing_deg':swing_peak}
  print('SVCH_GRIP_AUTHORED',family,role,counts,round(peak,3),round(swing_peak,3),flush=True)
 (outdir/('DA_SVCH_Grip_'+family+'.json')).write_text(json.dumps(out,separators=(',',':')))
 report['families'][family]=familyreport
(O/'authoring_recipe.json').write_text(json.dumps(report,indent=2))
print('SVCH_FOUR_GRIP_PROFILES_AUTHORED',flush=True)
