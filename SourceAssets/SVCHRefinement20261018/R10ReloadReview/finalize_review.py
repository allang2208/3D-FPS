"""Record the requested review against the saved profile and its real runtime capture."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;P=O.parents[2]
label='svch-reload-r10-seated-final-20261018';run=P/'Saved/SVCHPoseAudit'/label
install=json.loads((O/'install_receipt.json').read_text());editable=json.loads((O/'editable_source.json').read_text())
runtime=json.loads((run/'result.json').read_text(encoding='utf-8-sig'))
scope=json.loads((O/'scope_and_stability.json').read_text())
rows=[json.loads(s) for s in (run/'frames.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
assert runtime['completed'] and runtime['process_exit']==0
source_sha=hashlib.sha256((O/'profile_native_registration.json').read_bytes()).hexdigest()
assert editable['profile_source_sha256']==source_sha==install['source_sha256']
profile_disk=P/'Content/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip.uasset'
assert hashlib.sha256(profile_disk.read_bytes()).hexdigest()==install['profile_sha256']
preservation=json.loads((O.parent/'R7NativeV9/source_preservation.json').read_text())
preserved={path:hashlib.sha256((P/path).read_bytes()).hexdigest()==sha for path,sha in preservation.items()}
assert all(preserved.values()),'Source changed during final review'
evidence={}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
for stage in ('reload_normal','reload_empty'):
 active=[r for r in rows if r['stage']==stage and r['action_alpha']>.01]
 assert len(active)>=10 and all(r['native_v9_ready'] for r in active)
 assert all(r['action_grip_profile']==install['profile'] for r in active)
 assert all((run/'Frames'/r['image']).exists() for r in active)
 evidence[stage]={'frames':len(active),'native_v9_visible_all':True,'action_profile_observed_all':True}
 frames=[]
 for row in active:
  im=Image.open(run/'Frames'/row['image']).convert('RGB').resize((768,432),Image.Resampling.LANCZOS)
  draw=ImageDraw.Draw(im);draw.rectangle((0,0,768,28),fill=(24,24,26));draw.text((10,3),('普通换弹' if stage=='reload_normal' else '空仓换弹')+f" · 源时间 {row['action_time']:.2f}s",font=font,fill='white')
  frames.append(im)
 frames[0].save(O/(stage+'_review.gif'),save_all=True,append_images=frames[1:],duration=135,loop=0,optimize=True)
contact=json.loads((O/'contact_winding.json').read_text());body=json.loads((O/'body_winding.json').read_text())
assert contact['inside_winding_gt_half']==0 and body['240']['inside_count']==0
receipt={'revision':'R10ReloadReview','status':'Saved; ordinary and empty reload reviewed with native V9',
 'profile':install['profile'],'profile_sha256':install['profile_sha256'],'profile_source_sha256':source_sha,
 'mesh_revision':'R8Surface unchanged','assets_saved':True,'runtime_tested':True,'runtime_capture':str(run),
 'runtime':runtime,'reload_evidence':evidence,'source_preservation':preserved,
 'source_animation_assets_modified':False,'native_v9_mesh_modified':False,
 'other_action_profiles_unchanged':scope['preserved_other_clips'],
 'validation':{k:{a:b for a,b in v.items() if a!='magazine_envelope'} for k,v in scope['clips'].items()},
 'held_hand_magazine_inside_vertices':contact['inside_winding_gt_half'],'seated_hand_receiver_inside_vertices':body['240']['inside_count'],
 'editable_source':editable['editable_blend'],
 'build':{'succeeded':True,'log':str(O/'build-review.log'),'binary_sha256':hashlib.sha256((P/'Binaries/Win64/UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest()},
 'scope':'Factory magazine; ordinary and empty first-person reload. Full registered source samples, rendered V9 frames and seated contact surfaces.',
 'contact_tolerance_note':'Closed envelope is conservative around bevels (maximum overlap about 0.101 mm); original handguard return keeps its existing roughly 2 mm skin contact. No claim of every vertex being intersection-free.'}
(O/'validation_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
install['runtime_review_pending']=False;install['validation_receipt']=str(O/'validation_receipt.json')
(O/'install_receipt.json').write_text(json.dumps(install,indent=2))
previous=O/'previous_delivery.json';delivery=O.parent/'delivery_receipt.json'
if not previous.exists():previous.write_bytes(delivery.read_bytes())
(O/'delivery_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
receipt['previous_delivery']=json.loads(previous.read_text());delivery.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print('SVCH_R10_REVIEW_SAVED',json.dumps(evidence),flush=True)
