import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O));from retarget_pose import anatomical_frame
source=json.loads((O/'vre_pose.json').read_text())['bones'];sr={n:Matrix(b['rest']) for n,b in source.items()};sp={n:Matrix(b['pose']) for n,b in source.items()}
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Donor_Aligned.blend'));r=bpy.data.objects['SK_M4_Infima'];tr={b.name:b.matrix_local.copy() for b in r.data.bones};tp={b.name:b.matrix.copy() for b in r.pose.bones}
A=anatomical_frame(tr,'l')@Matrix.Diagonal((1,1,-1))@anatomical_frame(sr,'r').transposed()
td=tp['hand_l'].to_3x3()@tr['hand_l'].to_3x3().inverted();sd=sp['hand_r'].to_3x3()@sr['hand_r'].to_3x3().inverted();out={}
for digit in ['thumb','index','middle','ring','pinky']:
 for i in [1,2]:
  s=f'{digit}_{i:02}_r';sc=f'{digit}_{i+1:02}_r';t=s[:-1]+'l';tc=sc[:-1]+'l'
  rest1=A@(sr[sc].translation-sr[s].translation);rest2=tr[tc].translation-tr[t].translation
  p1=td@A@sd.inverted()@(sp[sc].translation-sp[s].translation);p2=tp[tc].translation-tp[t].translation
  out[t]={'rest_angle':math.degrees(rest1.angle(rest2)),'pose_angle':math.degrees(p1.angle(p2)),'source_length':rest1.length,'target_length':rest2.length}
(O/'retarget_direction_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
