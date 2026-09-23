"""Targeted readback for the user's report that the saved hand looked unchanged."""
import unreal as u,json,math
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDReloadHandRepair20260923')
auth=json.loads((O/'authoring.json').read_text())
before=json.loads((O/'runtime_before.json').read_text())['clips']['base/reload']['poses']['SOURCE']['220']
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
names=[n for n in before if n.startswith(('hand','thumb','index','middle','ring','pinky'))]
def qvalues(q):return [getattr(q,k) for k in 'xyzw']
def angle(a,b):
 d=abs(sum(x*y for x,y in zip(a,b)))/math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
 return math.degrees(2*math.acos(min(1.,max(0.,d))))
rows={}
for key,info in auth.items():
 a=u.load_asset(info['path']);poses={}
 for mode in ['SOURCE','COMPRESSED']:
  opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=getattr(u.AnimDataEvalType,mode)
  p=u.AnimPoseExtensions.get_anim_pose_at_time(a,220/120,opt)
  poses[mode]={n:qvalues(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL).rotation) for n in names}
 row={'asset':a.get_path_name(),'source':a.get_editor_property('asset_import_data').get_first_filename(),
      'source_compressed_max_rotation_error_deg':max(angle(poses['SOURCE'][n],poses['COMPRESSED'][n]) for n in names)}
 if key=='base/reload':
  row['changed_finger_tracks']={n:angle(before[n]['q'],poses['COMPRESSED'][n]) for n in names if n!='hand_l' and angle(before[n]['q'],poses['COMPRESSED'][n])>.1}
 rows[key]=row
(O/'saved_hand_readback.json').write_text(json.dumps({'clips':rows,'game_tested':False},indent=2))
print('SVD_HAND_SAVED_READBACK',len(rows),'MAX_COMPRESSED_ERROR_DEG',max(r['source_compressed_max_rotation_error_deg'] for r in rows.values()),
      'CHANGED_BASE_FINGER_TRACKS',len(rows['base/reload']['changed_finger_tracks']))
