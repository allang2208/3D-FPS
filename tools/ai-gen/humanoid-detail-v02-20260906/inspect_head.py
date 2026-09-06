import bpy,json
from pathlib import Path
from mathutils import Matrix
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'modern-zombie-v01-20260906/modern-zombie-v01.blend'))
a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
a.animation_data.action=None
for track in a.animation_data.nla_tracks:track.mute=True
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
body=bpy.data.objects['ModernZombie']
points=[list(body.matrix_world@v.co*100) for v in body.data.vertices if (body.matrix_world@v.co).z>1.44]
(R/'head-points.json').write_text(json.dumps(points))
print('HEAD_POINTS',len(points))
