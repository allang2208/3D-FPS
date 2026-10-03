import sys,json,bpy,math
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from pose_geometry import *
kind=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'idle'
rig,D,profile,meta=load();p=source_pose(rig,D,profile,kind);old={n:m.copy() for n,m in p.items()};contract=json.loads((O/('hand_contact_single_'+kind+'.json')).read_text());registration=Matrix(contract['registration'])
ra=rig.data.bones['WPN_root'].matrix_local@Matrix(meta['alignment']);root=p['WPN_root']@rig.data.bones['WPN_root'].matrix_local.inverted()@ra
delta=root@registration@root.inverted()
for n in p:
 if n.startswith('WPN_'):p[n]=delta@old[n]
for side,hand in contract['hands'].items():
 d=Matrix.Translation(root.to_quaternion()@Vector(hand['offset_canonical']));chain=[n for n in p if n=='hand_'+side or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
 for n in chain:p[n]=d@old[n]
 for n,v in hand['local_rotation_delta'].items():
  par=rig.data.bones[n].parent.name;local=old[par].inverted()@old[n];pos,q,scale=local.decompose();dq=Quaternion((v[6],*v[3:6]));p[n]=p[par]@Matrix.LocRotScale(pos,dq@q,scale)
set_pose(rig,p)
# For the diagnostic front and rear markers, the original geometry is transported with the root.
render(rig,p,meta,'after_'+kind,'hip' if kind=='idle' else 'aim')
# Side contact view uses only the evaluated assembly generated above.
for o in bpy.data.objects:
 if o.name.startswith('Diagnostic_'):o.matrix_world=Matrix.Identity(4)
camera=bpy.context.scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.3
center=root@Vector((0,.16,-.015));camera.location=root@Vector((-.4,.16,-.015));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.context.scene.render.filepath=str(O/('after_'+kind+'_side.png'));bpy.ops.render.render(write_still=True)
