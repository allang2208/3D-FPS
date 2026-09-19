"""Reuse the import/export scaffold, replacing the previous wrist-only solve.
All targets are computed in world space before reconstructing local transforms.
"""
from pathlib import Path
import sys
O=Path(__file__).parent
code=(O/'build_native_arms.py').read_text()
code=code.replace("baseline='--baseline' in sys.argv;D=O/('NativeBaseline' if baseline else 'Native')", "baseline=True;D=O/'SourceMatched'")
code=code.replace("srcidle=sample(r,1)", "srcidle=sample(r,1)\nsrcrest={b.name:rigid(r.matrix_world@b.matrix_local) for b in r.data.bones}")
code=code.replace("base=sample(r,0)", "base=sample(r,0)\ntargetrest={b.name:rigid(r.matrix_world@b.matrix_local) for b in r.data.bones}")
code=code.replace("def arm_maps(src,side,hand_override=None):", """def palm_frame(poses,side):
 h=poses['hand_'+side].translation
 forward=(poses['middle_01_'+side].translation-h).normalized()
 across=(poses['index_01_'+side].translation-poses['pinky_01_'+side].translation).normalized()
 normal=across.cross(forward).normalized(); across=forward.cross(normal).normalized()
 return Matrix((across,forward,normal)).transposed().to_4x4()

# Calibrate anatomical palm frames, not incompatible bone roll axes.
palm_correction={side:palm_frame(srcrest,side).inverted()@srcrest['hand_'+side] for side in ['l','r']}
target_palm={side:targetrest['hand_'+side].inverted()@palm_frame(targetrest,side) for side in ['l','r']}
def matched_hand(src,side):
 q=(C@palm_frame(src,side)@target_palm[side].inverted()).to_quaternion()
 h='hand_'+side
 # Palm size differs between the source hands and Manny. Align the knuckle
 # contact row, not just the wrist origin, without scaling the native mesh.
 tips=['index_01_'+side,'middle_01_'+side,'ring_01_'+side,'pinky_01_'+side]
 src_anchor=sum((src[n].translation for n in tips),Vector())/4
 dst_anchor=sum((targetrest[n].translation for n in tips),Vector())/4
 local_anchor=targetrest[h].inverted()@dst_anchor
 wrist=C@src_anchor-q@local_anchor
 return Matrix.LocRotScale(wrist,q,Vector((1,1,1)))

def arm_maps(src,side,hand_override=None):""")
code=code.replace("m,e=arm_maps(src,side,hand_override if side=='l' else None)","m,e=arm_maps(src,side,matched_hand(src,side))")
start=code.index('  # Reuse the accepted M4 wrap grasp')
end=code.index('  for n in names:\n   local=',start)
code=code[:start]+"""  # Preserve native lengths and transfer finger segment orientation relative
  # to the palm. Source animations drive every finger rather than frozen M4 idle.
  for side in ['l','r']:
   sh='hand_'+side
   source_palm=palm_frame(src,side)
   source_bind_palm=palm_frame(srcrest,side)
   native_bind_palm=palm_frame(targetrest,side)
   world_palm=r.matrix_world@p[sh]@target_palm[side]
   for n in names:
    if not (n.endswith('_'+side) and n.startswith(('thumb_','index_','middle_','ring_','pinky_')) and n in src):continue
    par=parent[n]
    # The rest-axis correction removes bone-roll differences while retaining
    # native finger length, base attachment and the source finger articulation.
    correction=(source_bind_palm.inverted()@srcrest[n]).to_quaternion().inverted()@(native_bind_palm.inverted()@targetrest[n]).to_quaternion()
    q=world_palm.to_quaternion()@(source_palm.inverted()@src[n]).to_quaternion()@correction
    location=(p[par]@lr[n]).translation
    p[n]=Matrix.LocRotScale(location,r.matrix_world.to_quaternion().inverted()@q,Vector((1,1,1)))
"""+code[end:]
if '--idle-only' in sys.argv:
 code=code.replace('for name,frames in clips.items():',"for name,frames in clips.items():\n if name!='idle':continue")
exec(compile(code,str(O/'build_native_arms.py'),'exec'))
