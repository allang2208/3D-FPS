"""Capture the editable one-piece head in the original assembled idle shot with a locked camera."""
from pathlib import Path
import json,gzip
import bpy
import numpy as np
from mathutils import Vector
root=Path(__file__).resolve().parents[4]/'SourceAssets/VillageBlacksmithNPC20261118'
out=root/'FinishR2/HeadHair'
bpy.ops.wm.open_mainfile(filepath=str(root/'VillageBlacksmith_R4.blend'))
s=bpy.context.scene;ob=bpy.data.objects['SK_Smith_Head']
cam=s.camera
evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
bounds=[evaluated.matrix_world@Vector(v) for v in evaluated.bound_box]
target=Vector(tuple((min(v[i] for v in bounds)+max(v[i] for v in bounds))*.5 for i in range(3)))
target.z+=.004
cam.location=target+Vector((.38,2.50,.06));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=.49
s.render.resolution_x=860;s.render.resolution_y=820;s.render.resolution_percentage=100
s.render.filepath=str(out/'head_close_before.png');bpy.ops.render.render(write_still=True)
d=json.loads(gzip.decompress((out/'face.json.gz').read_bytes()))
ob.data.vertices.foreach_set('co',(np.asarray(d['p'])*.01).ravel())
ob.data.normals_split_custom_set_from_vertices(d['n']);ob.data.update()
for node in ob.data.materials[0].node_tree.nodes:
    if node.type=='TEX_IMAGE':
        name=Path(bpy.path.abspath(node.image.filepath)).name
        new=out/'Textures'/name
        if new.is_file():
            colorspace=node.image.colorspace_settings.name
            node.image=bpy.data.images.load(str(new),check_existing=False)
            node.image.colorspace_settings.name=colorspace
            if name.endswith('_BC.png'):
                node.image.alpha_mode='CHANNEL_PACKED'
s.render.filepath=str(out/'head_close_after.png');bpy.ops.render.render(write_still=True)
import subprocess
subprocess.run(['python',str(Path(__file__).with_name('compare_head.py'))],check=True)
