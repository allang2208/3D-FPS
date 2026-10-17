"""Requested read-only audit of the installed M870 R3 animation and profiles."""
import gzip,json,math
from pathlib import Path
import unreal as u

O=Path(__file__).parent;A=O.parent/'M870QuickMeleeElbowR3_20261017'
patch=json.loads((A/'animation_patch.json').read_text())
with gzip.open(A/'inputs.json.gz','rt') as f:source=json.load(f)['weapons']['m870']
checks=[]
def check(name,passed,detail=None):
    checks.append(dict(case=name,passed=bool(passed),detail=detail))
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def near(a,b):
    if not all(math.isfinite(x) for x in a+b):return False
    pos=max(abs(a[i]-b[i]) for i in (0,1,2,7,8,9))
    an=math.sqrt(sum(x*x for x in a[3:7]));bn=math.sqrt(sum(x*x for x in b[3:7]))
    dot=abs(sum(x*y for x,y in zip(a[3:7],b[3:7]))/(an*bn)) if an*bn else 0
    return pos<.0001 and dot>1.-1.e-7
def clips(asset):
    return [dict(base=c.get_editor_property('base').get_path_name(),duration=float(c.get_editor_property('duration')),
        retained=c.get_editor_property('retained').get_path_name() if c.get_editor_property('retained') else None,
        tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')])
        for c in asset.get_editor_property('clips')]

mesh=u.load_asset(source['mesh']);clip=u.load_asset(patch['melee_path'])
material_slots=[dict(slot=str(s.get_editor_property('material_slot_name')),
    material=s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.materials] if mesh else []
check('base clip and current native mesh load',mesh and clip)
if mesh and clip:
    check('R3 revision metadata',u.EditorAssetLibrary.get_metadata_tag(clip,'M870QuickMeleeSource')==patch['revision'])
    check('base animation uses native skeleton',clip.get_editor_property('skeleton')==mesh.skeleton)
    check('0.9 second source clock',abs(clip.get_play_length()-.9)<1.e-6)
    check('217 keys at 240 Hz',u.AnimationLibrary.get_num_keys(clip)==217)
    expected={t['bone']:t for t in patch['base_tracks']};names=patch['write_bones'];matched=True
    for i in range(patch['frames']+1):
        poses=u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/patch['fps'],False,mesh)
        for name,pose in zip(names,poses):
            t=expected[name];start=0 if len(t['times'])==1 else i*10
            matched &= near(pack(pose),t['values'][start:start+10])
    check('all seven saved right-arm tracks match R3 authoring',matched)
    curve=patch['ownership_curve']
    present=u.AnimationLibrary.does_curve_exist(clip,curve['name'],u.RawCurveTrackTypes.RCT_FLOAT)
    check('authored support curve present',present)
    if present:
        ts,vs=u.AnimationLibrary.get_float_keys(clip,curve['name'])
        check('support ownership curve unchanged',list(ts)==curve['times'] and list(vs)==curve['values'])
    check('source FBX exists',(A/'A_M870_QuickMelee_Elbow_R3.fbx').is_file())
    check('editable five-action source exists',(A/'M870_QuickMelee_Elbow_R3.blend').is_file())

for family,spec in patch['profiles'].items():
    asset=u.load_asset(spec['path']);check(family+' profile loads',asset)
    if not asset:continue
    check(family+' R3 metadata',u.EditorAssetLibrary.get_metadata_tag(asset,'M870QuickMeleeSource').startswith(patch['revision']))
    rows=clips(asset);actions=[c for c in rows if c['base']==patch['melee_path']]
    check(family+' exactly one shared quick-melee entry',len(actions)==1)
    if len(actions)==1:
        c=actions[0]
        check(family+' shared base, duration and no old retained override',abs(c['duration']-.9)<1.e-6 and c['retained'] is None)
        target=spec['clip']['tracks'];valid=len(target)==len(c['tracks'])
        for actual,wanted in zip(c['tracks'],target):
            valid &= actual['bone']==wanted['bone'] and len(actual['values'])==len(wanted['values']) and len(actual['times'])==len(wanted['times'])
            if valid:
                valid &= all(abs(x-y)<1.e-5 for x,y in zip(actual['values'],wanted['values']))
                valid &= all(abs(x-y)<1.e-6 for x,y in zip(actual['times'],wanted['times']))
        check(family+' saved pose deltas match R3',valid)
    old=[c for c in source['profiles'][family]['clips'] if c['base']!=patch['melee_path']]
    new=[c for c in rows if c['base']!=patch['melee_path']]
    check(family+' other actions unchanged',old==new)

report=dict(checks=len(checks),failures=sum(not c['passed'] for c in checks),results=checks,material_slots=material_slots,
    mode='Read-only installed animation/profile audit; no game, rendering or network sockets',runtime_tested=False)
(O/'asset-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M870_R3_ASSET_AUDIT',report['checks'],'checks',report['failures'],'failures')
for c in checks:
    if not c['passed']:print('M870_R3_ASSET_FAIL',c['case'])
