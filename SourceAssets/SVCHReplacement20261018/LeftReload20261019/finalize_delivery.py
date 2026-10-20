import json,gzip,hashlib,datetime
from pathlib import Path
import numpy as np
O=Path(__file__).parent;P=O.parents[2];runs=P/'Saved/SVCHPoseAudit'
before=runs/'svch-left-reload-20261019-before';after=runs/'svch-left-reload-20261019-after-final'
completion=json.loads((after/'completion.json').read_text());assert completion['completed']
installed=json.loads((O/'install_receipt.json').read_text());assert installed['complete']
assetfile=P/'Content'/(installed['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
assert hashlib.sha256(assetfile.read_bytes()).hexdigest()==installed['after_sha256']
a=json.load(gzip.open(O/'Inputs/arms.json.gz','rt'));b=json.load(gzip.open(O/'InputsAfter/arms.json.gz','rt'))
native={k:a[k]==b[k] for k in ('positions','triangles','weights','reference','weight_bones','materials')};assert all(native.values())
rows_a=[json.loads(x) for x in (before/'frames.jsonl').read_text().splitlines()];rows_b=[json.loads(x) for x in (after/'frames.jsonl').read_text().splitlines()]
runtime={}
for stage in ('reload_normal','reload_empty'):
 aa=[r for r in rows_a if r['stage']==stage and r['action_alpha']>.99];bb=[r for r in rows_b if r['stage']==stage and r['action_alpha']>.99]
 maximum={k:0. for k in ['lowerarm_l','hand_l','hand_r','WPN_SOCKET_Magazine','WPN_bolt']};matches=0;length_error=0.
 for row in aa:
  other=min(bb,key=lambda r:abs(r['action_time']-row['action_time']))
  if abs(row['action_time']-other['action_time'])>1e-5:continue
  matches+=1
  for name in maximum:maximum[name]=max(maximum[name],float(np.linalg.norm(np.asarray(row['root_space_bones_cm'][name])-other['root_space_bones_cm'][name])))
  for start,end in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
   def length(r):return np.linalg.norm(np.asarray(r['root_space_bones_cm'][end])-r['root_space_bones_cm'][start])
   length_error=max(length_error,float(abs(length(row)-length(other))))
 runtime[stage]={'matched_source_time_samples':matches,'maximum_bone_position_difference_cm':maximum,'maximum_arm_bone_length_difference_cm':length_error}
report={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved':True,'asset':installed['asset'],'native_geometry_weights_rest_equal':native,'native_file_sha_changed_during_task':a['sha256']!=b['sha256'],'native_morph_counts_before_after':[len(a['morph_names']),len(b['morph_names'])],'this_task_wrote_native_asset':False,'source_animation_assets_changed_by_this_task':False,'cpp_changes':False,'runtime':runtime,'completion':completion,'visual_review':'Reviewed actual ordinary/empty reload frames: withdrawal, insert, hand release, support return and empty bolt operation. No source hand redesign.','scope':'Native bare V9, factory SVCh, 1600x900, measured FOV approx 107.5; not gloves/sleeves/attachments/multiplayer.','candidate_history':'First after capture exposed a missed curved armpit boundary; final author uses the true welded-for-analysis opening contour.'}
(O/'delivery_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps({'saved':True,'runtime':runtime,'native_geometry_weights_rest_equal':native},indent=2))
