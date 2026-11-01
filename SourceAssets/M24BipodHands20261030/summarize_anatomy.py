from pathlib import Path
import gzip,json,math,bisect,hashlib
O=Path(__file__).resolve().parent
with gzip.open(O/'AnatomyBefore/compressed.json.gz','rt') as f:before=json.load(f)
with gzip.open(O/'Review/compressed.json.gz','rt') as f:after=json.load(f)
parents=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['parents']
def owned(n):
    if n=='ik_hand_l':return True
    while n:
        if n=='clavicle_l':return True
        n=parents.get(n)
    return False
def angle(a,b):
    q,r=a[3:7],b[3:7];dot=abs(sum(x*y for x,y in zip(q,r)))/math.sqrt(sum(x*x for x in q)*sum(x*x for x in r))
    return math.degrees(2*math.acos(min(1.,dot)))
def interpolate(t,times,values):
    k=min(len(times)-2,max(0,bisect.bisect_right(times,t)-1));w=max(0,min(1,(t-times[k])/(times[k+1]-times[k])))
    return values[k]*(1-w)+values[k+1]*w
curves=json.loads((O/'elbow_curves.json').read_text());unchanged={};curve_error=0
for family,clip in after['clips'].items():
    pos=rot=scale=0.
    for old,new in zip(before['clips'][family]['frames'],clip['frames']):
        for n,a,b in zip(after['names'],old,new):
            if owned(n):continue
            pos=max(pos,math.dist(a[:3],b[:3]));rot=max(rot,angle(a,b));scale=max(scale,math.dist(a[7:],b[7:]))
    unchanged[family]={'max_nonowned_position_delta_cm':pos,'max_nonowned_rotation_delta_deg':rot,'max_nonowned_scale_delta':scale}
    for n,weights in clip['curve_weights'].items():
        c=curves[n]
        curve_error=max(curve_error,max(abs(v-interpolate(t,c['times'],c['values'])) for t,v in zip(clip['curve_times'],weights)))
contacts=json.loads((O/'Review/AnatomyFinal/hand_contact.json').read_text())
surface=json.loads((O/'Review/saved_surface_check.json').read_text())
anatomy=json.loads((O/'Review/anatomy_AnatomyFinal.json').read_text())['summary']
report={'unchanged_tracks':unchanged,'max_compressed_curve_error':curve_error,'anatomy':anatomy,
        'contact_samples':len(contacts),'max_hand_penetration_mm':max(x['max_depth_mm'] for x in contacts),
        'elbow_fold_triangles':{k:v['max_elbow_folds'] for k,v in surface.items()},
        'saved_assets_match_receipt':all(hashlib.sha256((O.parents[1]/'Content'/ (v['path'].split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()==v['sha256'] for v in json.loads((O/'install_receipt.json').read_text())['saved']),
        'runtime_game_tested':False}
(O/'Review/final_review_summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
