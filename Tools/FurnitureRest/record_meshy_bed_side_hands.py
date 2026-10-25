"""Record the side-hand edit, unchanged body channels and saved contact checks."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBedSideHands20261024'
BASE=OUT.parent/'MeshyBed20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
old,new=read(BASE/'authored.json'),read(OUT/'authored.json')
changed=[i for i,n in enumerate(new['names']) if n.startswith(('upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_'))]
fixed=[i for i in range(len(new['names'])) if i not in changed]
for role,take in new['clips'].items():
    a,b=np.asarray(old['clips'][role]['frames']),np.asarray(take['frames'])
    if not np.array_equal(a[:,fixed],b[:,fixed]) or not np.array_equal(a[...,[0,1,2,7,8,9]],b[...,[0,1,2,7,8,9]]):
        raise RuntimeError('Unexpected body/translation/scale edit: '+role)
    if role.endswith('.Idle') and not np.array_equal(a,b):raise RuntimeError('Idle changed.')
saved=read(OUT/'ReviewSaved/saved_poses.json');samples=np.asarray(saved['clips']['Rest.Bed.Enter']['frames']);arms={}
for name in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r'):
    q=R.from_quat(samples[:,new['names'].index(name),3:7]);v=np.degrees((q[1:]*q[:-1].inv()).magnitude())
    arms[name]={'maximum_local_step_degrees':float(v.max()),'time_seconds':float((v.argmax()+1)/30)}
publication=read(OUT/'publication.json')
delivery={
    'saved_assets':read(OUT/'assets_saved.json'),
    'runtime_published':publication['runtime_published'],
    'changed_roles':new['changed_roles'],
    'authoring_body_head_legs_translations_scales_idle_unchanged':True,
    'saved_arm_continuity':arms,'stage_joins':read(OUT/'native_stage_review.json'),
    'geometry':read(OUT/'geometry_audit_saved.json'),
    'hand_body':read(OUT/'hand_body_contact_saved.json'),
    'contact_scope':'Jason base body/head and two ordinary Queen bed meshes; Kaitlin native skeleton and stage joins only',
    'preview':str(OUT/'ReviewSaved/bed_entry.gif'),
    'game_tested':False,'clothing_combinations_tested':False,'interactive_editor_started':False,
    'git_commit':None,'git_push':None,
}
(OUT/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print('MESHY_BED_SIDE_HANDS_RECORDED',len(arms))
