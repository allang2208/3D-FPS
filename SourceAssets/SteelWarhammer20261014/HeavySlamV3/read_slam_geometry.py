"""Read the requested hammer orientation and shoulder openings; no rendering."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Warhammer_HeavySlam_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];skin=bpy.data.objects['Warhammer_BareArmsV7']
a=bpy.data.actions['A_Warhammer_HeavyRelease'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
points=[rig.matrix_world.inverted()@skin.matrix_world@v.co for v in skin.data.vertices]
groups={g.index:g.name for g in skin.vertex_groups};rings=[]
for ring in json.loads((P.parent/'RhythmClearanceV2/source_geometry.json').read_text())['rings']:
    ids=ring['vertices'];p=np.array([[*points[i],1.] for i in ids]);influences={}
    for n in {groups[g.group] for i in ids for g in skin.data.vertices[i].groups if g.weight>1e-6}:
        weights=np.array([sum(g.weight for g in skin.data.vertices[i].groups if groups[g.group]==n) for i in ids])
        influences[n]=(p@np.array(rest[n].inverted()).T,weights)
    rings.append(influences)
def smooth(a,b,t):
    u=max(0,min(1,(t-a)/(b-a)));return u*u*(3-2*u)
samples=[]
for f in (0,8,16,24,36,55,84,150,372,420,480,540,600,612):
    bpy.context.scene.frame_set(f);t=f/480;pose={b.name:b.matrix.copy() for b in rig.pose.bones}
    u=max(0,min(1,(t-.775)/.5));anchor=1-u*u*u*(10-15*u+6*u*u);w=smooth(0,.075,t)*anchor
    eye=Vector((0,.20*w,-.52*w));to=Vector((0,.69,-1.60))-eye
    theta=math.atan2(-to.z,to.y)*smooth(.025,.175,t)*anchor
    forward=Vector((0,math.cos(theta),-math.sin(theta)));up=Vector((0,math.sin(theta),math.cos(theta)))
    # Match the runtime's recovery from the fixed release anchor to the eye.
    origin=eye*(1-anchor)
    opening=[]
    for ring in rings:
        p=sum((local@np.array(pose[n]).T)[:,:3]*weight[:,None] for n,(local,weight) in ring.items())+np.array(origin-eye)
        x=p[:,0];d=p@np.array(forward);z=p@np.array(up);tv=math.tan(math.radians(41));th=tv*16/9
        opening.append(min(float(np.max(v))+.02 for v in (d,th*d-x,th*d+x,tv*d-z,tv*d+z)))
    wrists={}
    for s in ('l','r'):
        hand=pose['hand_'+s];fore=(hand.translation-pose['lowerarm_'+s].translation).normalized()
        neutral=hand.to_quaternion()@rest['hand_'+s].to_quaternion().inverted()@(rest['hand_'+s].translation-rest['lowerarm_'+s].translation).normalized()
        wrists[s]={'fold_degrees':math.degrees(neutral.angle(fore)),'shoulder':list(pose['upperarm_'+s].translation),'hand':list(hand.translation)}
    samples.append({'seconds':t,'opening_plane_error_cm':[100*x for x in opening],'wrists':wrists})
(P/'geometry_readback.json').write_text(json.dumps(samples,indent=2))
print(json.dumps(samples))
