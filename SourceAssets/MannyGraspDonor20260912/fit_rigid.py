"""Align the whole authored fist to the grip; never refit individual fingers."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;OLD=O.parent/'VerticalGripFront20260911';sys.path.insert(0,str(OLD))
CASE=Path(sys.argv[sys.argv.index('--case')+1]) if '--case' in sys.argv else O
from front_pose import solve_arm,apply
import inspect_pose
bpy.ops.wm.open_mainfile(filepath=str(CASE/'M4_Donor_Preview.blend'))
r=bpy.data.objects['SK_M4_Infima'];fit=json.loads((CASE/'donor_fit.json').read_text())
G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);Gi=G.inverted()
centers=[];report={}
for digit in ['index','middle','ring','pinky']:
    points=[Gi@r.pose.bones[f'{digit}_{j:02}_l'].head for j in [1,2,3]]
    a,b,c=points
    # Circle through the three articulated knuckles, in the grip radial plane.
    M=Matrix(((2*(b.x-a.x),2*(b.y-a.y)),(2*(c.x-a.x),2*(c.y-a.y))))
    rhs=Vector((b.x*b.x+b.y*b.y-a.x*a.x-a.y*a.y,c.x*c.x+c.y*c.y-a.x*a.x-a.y*a.y))
    xy=M.inverted()@rhs;center=Vector((xy.x,xy.y,sum(p.z for p in points)/3))
    centers.append(center);report[digit]={'points':[list(p) for p in points],'center':list(center),'radius':(Vector((a.x,a.y))-xy).length}
axis=(centers[0]-centers[-1]).normalized();q=axis.rotation_difference(Vector((0,0,1)))
center=sum(centers,Vector())/len(centers)
report['axis']=list(axis);report['correction_angle']=math.degrees(q.angle);report['center']=list(center)
# The whole donor fist moves as one unit. Center the grip's 11 cm usable shaft
# within the index-to-pinky stack; the attachment dimensions remain unchanged.
dest=Vector((0,0,-.060))
correction=G@Matrix.Translation(dest)@q.to_matrix().to_4x4()@Matrix.Translation(-center)@Gi
H=correction@r.pose.bones['hand_l'].matrix
p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones}
report['arm']=solve_arm(p,rest,H,G)
for b in r.pose.bones:
    if b.name in fit['basis']:
        lr=rest[b.parent.name].inverted()@rest[b.name];p[b.name]=p[b.parent.name]@lr@Matrix(fit['basis'][b.name])
apply(r,p,rest)
fit['hand_in_root']=[list(x) for x in (r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix)]
(CASE/'rigid_alignment.json').write_text(json.dumps(report,indent=2));(CASE/'aligned_fit.json').write_text(json.dumps(fit,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(CASE/'M4_Donor_Aligned.blend'))
inspect_pose.O=CASE;inspect_pose.render(r,fit,'aligned')
print('RIGID_ALIGNMENT',json.dumps(report),flush=True)
