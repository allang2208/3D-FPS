"""Repair only SVCH quick-melee right-arm support over the accepted V9 bind.

Gun, palm, digits, other actions, native scales and source timing are inputs.
The saved profile replacements are installed by merging just this action.
"""
from pathlib import Path
import sys, ast, copy, json, hashlib

OUT = Path(__file__).resolve().parent
INPUT = OUT.parent / 'ForegripFit20261019'
sys.path.insert(0, str(INPUT))
from arm_math import *
from scipy.ndimage import gaussian_filter1d

PROJECT = OUT.parents[2]
manifest = json.loads((INPUT/'Inputs/manifest.json').read_text())
for spec in list(manifest.values()) + list(motion['clips'].values()):
    f = PROJECT/'Content'/(spec['path'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(f.read_bytes()).hexdigest() != spec['sha256']:
        raise RuntimeError('Changed authoring input: '+spec['path'])

ref = matrices(arms['reference'])
source = OUT.parent/'LeftBolt20261019/author_left_bolt.py'
code = source.read_text(encoding='utf-8').replace('(L1+L2)*.94', '(L1+L2)*max(.94,np.linalg.norm(H-A)/(L1+L2))')
tree = ast.parse(code)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
    and n.name in ('mixrot','frame','twist','arm')],type_ignores=[]),str(source),'exec'),globals())

u,l,h,c = [ids[n+'_r'] for n in ('upperarm','lowerarm','hand','clavicle')]
axis_ref = unit(ref[h,:3,3]-ref[l,:3,3])
changed = [j for j,n in enumerate(names) if n.endswith('_r')
    and n.startswith(('clavicle','upperarm','lowerarm','hand'))]
clip = motion['clips']['quick_melee']
old = np.asarray([pose('quick_melee',i) for i in range(len(clip['times']))])
# The inherited recovery elbow reverses sharply over a few samples. Smooth
# only its support guide, never the weapon/palm trajectory or contact clock.
elbow_guide = gaussian_filter1d(old[:,l,:3,3],1.5,axis=0,mode='nearest')
shoulder_guide = gaussian_filter1d(old[:,u,:3,3],1.5,axis=0,mode='nearest')
new = []
rows = []
for i,(t,p) in enumerate(zip(clip['times'],old)):
    A,E,H = [p[j,:3,3] for j in (u,l,h)]
    L1,L2 = np.linalg.norm(E-A),np.linalg.norm(H-E)
    ideal = rigid(p[h])[:3,:3] @ rigid(ref[h])[:3,:3].T @ axis_ref
    before = np.degrees(np.arccos(np.clip(ideal@unit(H-E),-1.,1.)))
    delta = R.from_matrix(swing(ideal,unit(H-elbow_guide[i]))).as_rotvec()
    # A soft cone preserves the relaxed original wrist and starts changing
    # support continuously. It does not rotate the hand away from the grip.
    angle = np.linalg.norm(delta)
    limit = np.deg2rad(25.)
    softness = np.deg2rad(5.)
    capped = min(angle, limit-softness*np.log1p(np.exp((limit-angle)/softness)))
    capped = max(0.,capped)
    direction = R.from_rotvec(delta*(capped/max(angle,1e-9))).apply(ideal)
    elbow = H-L2*direction
    shoulder = elbow+L1*unit(shoulder_guide[i]-elbow)
    weight = float(ease(0,.075,t)*(1-ease(.73,clip['duration'],t)))
    # Interpolate forearm direction on the sphere, then reproject the upper
    # segment at its original length. No joint or tissue is lengthened.
    direction = unit(R.from_rotvec(R.from_matrix(swing(unit(H-E),direction)).as_rotvec()*weight).apply(unit(H-E)))
    elbow = H-L2*direction
    anchor = A*(1-weight)+shoulder_guide[i]*weight
    shoulder = elbow+L1*unit(anchor-elbow)
    q,info = arm(p,'r',p[h],shoulder,elbow-shoulder,blend=weight)
    if i in (0,len(old)-1):q=p.copy()
    new.append(q)
    rows.append(dict(time=t,before_wrist_deg=before,after_wrist_deg=info['wrist_swing_deg'],
        shoulder_shift_cm=float(np.linalg.norm(q[u,:3,3]-A)),elbow_shift_cm=float(np.linalg.norm(q[l,:3,3]-E)),
        pronation_deg=info['pronation_deg']))

new = np.asarray(new)
output_dir=OUT/'Profiles';output_dir.mkdir(exist_ok=True)
report={'action':clip['path'],'duration':clip['duration'],'inputs':manifest,'families':{},'samples':rows,
    'source_animation_written':False,'V9_mesh_written':False,'other_actions_written':False}
for family in ('base','angled','vertical','canted','prism'):
    original=profile if family=='base' else json.loads((INPUT/'Profiles'/('DA_SVCH_Grip_'+family+'.json')).read_text())
    out=copy.deepcopy(original)
    entry=next(x for x in out['clips'] if x['base']==clip['path'])
    source_entry=copy.deepcopy(entry)
    values={j:[] for j in changed}
    palm_error=length_error=scale_error=digits_error=0.
    for i,t in enumerate(clip['times']):
        local0=apply(clip['frames'][i],source_entry,t)
        local=matrices(local0)
        for j in changed:
            local[j]=relative(new[i,parents[j]],new[i,j])
            local[j,:3,:3]=rigid(local[j])[:3,:3]*local0[j,7:]
        posed=comp(local)
        original_pose=comp(matrices(local0))
        palm_error=max(palm_error,float(np.max(abs(posed[h]-original_pose[h]))))
        for a,b in ((u,l),(l,h)):
            length_error=max(length_error,abs(np.linalg.norm(posed[a,:3,3]-posed[b,:3,3])-np.linalg.norm(original_pose[a,:3,3]-original_pose[b,:3,3])))
        for j in changed:
            v=np.zeros(10);v[:3]=local[j,:3,3]-np.asarray(clip['frames'][i][j])[:3]
            v[3:7]=(R.from_matrix(rigid(local[j])[:3,:3])*R.from_quat(clip['frames'][i][j][3:7]).inv()).as_quat()
            v[7:]=local0[j,7:]-np.asarray(clip['frames'][i][j])[7:]
            if values[j] and values[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values[j].append(v)
    entry['tracks']=[tr for tr in entry['tracks'] if ids[tr['bone']] not in changed]
    for j in changed:
        entry['tracks'].append(dict(bone=names[j],times=clip['times'],values=np.round(values[j],10).ravel().tolist()))
    (output_dir/(family+'.json')).write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    report['families'][family]={'palm_matrix_error':palm_error,'bone_length_error_cm':length_error,
        'other_entries_identical':all(a==b for a,b in zip(original['clips'],out['clips']) if a['base']!=clip['path'])}
    assert palm_error<1e-6 and length_error<1e-6

np.savez_compressed(OUT/'poses.npz',before=old,after=new)
report['max_before_wrist_deg']=max(r['before_wrist_deg'] for r in rows)
report['max_after_wrist_deg']=max(r['after_wrist_deg'] for r in rows)
report['max_shoulder_shift_cm']=max(r['shoulder_shift_cm'] for r in rows)
report['max_elbow_shift_cm']=max(r['elbow_shift_cm'] for r in rows)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('samples','inputs')},indent=2),flush=True)
