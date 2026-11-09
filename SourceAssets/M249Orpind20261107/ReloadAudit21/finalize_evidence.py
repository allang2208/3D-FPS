"""Read-only delivery checks for the user-requested reload inspection."""
from pathlib import Path
import hashlib,json,pickle,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;project=r.parents[2]
install=json.loads((r/'install_receipt.json').read_text());assets={}
for path,expected in install['saved'].items():
    actual=hashlib.sha256((project/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
    assets[path]=dict(sha256=actual,matches_saved_receipt=actual==expected)
    if actual!=expected:raise RuntimeError('Asset changed after import: '+path)
names=pickle.load(open(r.parent/'Repair20/native.pkl','rb'))['names'];handoff={};cameras={}
folders={p.name:p for p in (r/'release').iterdir() if (p/'review.json').exists()}
folders.update({p.name:p for p in (r/'delivery_final').iterdir() if (p/'review.json').exists()})
for name,folder in folders.items():
    review=json.loads((folder/'review.json').read_text());count=review['bone_count']
    raw=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+count*7);pose=raw[:,4:].reshape(-1,count,7)
    records={};duration=review['duration'];time=raw[:-1,0]
    for bone in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']:
        q=R.from_quat(pose[:,names.index(bone),3:]);step=np.degrees((q[:-1].inv()*q[1:]).magnitude())
        records[bone]=dict(tail_max_deg=float(step[(time>=duration-.12)&(time<duration)].max()),
                           idle_max_deg=float(step[time>=duration].max()))
    handoff[name]=records
    frames=review['frames'];cameras[name]=dict(rotation_deg=float(np.degrees(R.from_quat([f['camera'][3:7] for f in frames]).magnitude()).max()),
        translation_cm=float(np.linalg.norm([f['camera'][:3] for f in frames],axis=1).max()))
(r/'handoff_metrics.json').write_text(json.dumps(handoff,indent=2))
receipt=dict(saved_asset_count=len(assets),assets=assets,full_editor_build=json.loads((r/'build_receipt.json').read_text()),
    full_review=json.loads((r/'release/receipt.json').read_text()),focused_review=json.loads((r/'delivery_final/receipt.json').read_text()),
    camera_peaks=cameras,editor_gui_started=False,pie_or_level_test=False,audio_test=False)
receipt['max_tail_step_deg']=max(v['tail_max_deg'] for row in handoff.values() for v in row.values())
receipt['max_idle_step_deg']=max(v['idle_max_deg'] for row in handoff.values() for v in row.values())
(r/'delivery_receipt.json').write_text(json.dumps(receipt,indent=2))
print('Saved assets',len(assets),'review combinations',len(folders),'tail max',receipt['max_tail_step_deg'],'idle seam max',receipt['max_idle_step_deg'])
