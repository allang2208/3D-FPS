import sys,json,math,bpy
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from pose_geometry import *
rig,D,prof,meta=load();p=source_pose(rig,D,prof);set_pose(rig,p)
ra=rig.data.bones['WPN_root'].matrix_local@Matrix(meta['alignment'])
root=p['WPN_root']@rig.data.bones['WPN_root'].matrix_local.inverted()@ra
raw=json.loads((B/'canonical_parts.json').read_text())
for part in raw:
 vv=[Vector(v) for v in part['verts']]
 print('PART',part['name'],'min',[round(min(v[a] for v in vv),4) for a in range(3)],'max',[round(max(v[a] for v in vv),4) for a in range(3)])
for n in ['hand_r','hand_l','thumb_01_r','thumb_03_r','index_03_r','middle_03_r']:
 print('BONE_CANONICAL',n,list(root.inverted()@p[n].translation))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
for mat in bpy.data.materials:mat.diffuse_color=(.66,.4,.24,1) if 'Manny' in mat.name else (.3,.33,.36,1)
data=bpy.data.cameras.new('Contact');camera=bpy.data.objects.new('Contact',data);bpy.context.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO';data.ortho_scale=.3
center=root@Vector((0,.14,-.015));camera.location=root@Vector((-.4,.14,-.015));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/'before_contact_side.png');bpy.ops.render.render(write_still=True)
