import bpy, math, json
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'foreman-skin-v05-20260906/foreman-skin-v05.blend'))
a=bpy.data.objects['ForemanRig'];body=bpy.data.objects['ForemanBody'];s=bpy.context.scene
a.animation_data.action=None
for tr in a.animation_data.nla_tracks:tr.mute=True
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
s.render.engine='CYCLES';s.cycles.samples=12;s.render.resolution_x=700;s.render.resolution_y=700;s.render.resolution_percentage=100
bpy.data.objects['Whip'].hide_render=True
cam=s.camera;cam.data.ortho_scale=.52
for name,location in [('front',(-.85,-3,1.2)),('side',(-3,-.03,1.2)),('palm',(.5,-.05,1.12))]:
 cam.location=location;cam.rotation_euler=(Vector((-.83,-.025,1.13))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/('hand-'+name+'.png'));bpy.ops.render.render(write_still=True)
verts=[{'co':list(v.co),'weights':{body.vertex_groups[g.group].name:g.weight for g in v.groups}} for v in body.data.vertices if v.co.x<-.6 and .95<v.co.z<1.3]
(R/'hand-vertices.json').write_text(json.dumps(verts))
