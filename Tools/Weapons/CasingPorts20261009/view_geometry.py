"""Render a saved current-mesh capture in its physical gun frame, offline."""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
report=json.loads((O/'geometry_report.json').read_text())
args=sys.argv[sys.argv.index('--')+1:]
key=args[0];width=float(args[1]);target=Vector(tuple(map(float,args[2:5])))
data=np.load(O/'Geometry'/f'{key}.npz',allow_pickle=True)
basis=np.array(report[key]['basis_rows'])
bpy.ops.wm.read_factory_settings(use_empty=True)
me=bpy.data.meshes.new(key);me.from_pydata(data['vertices']@basis.T,[],data['faces']);me.update()
ob=bpy.data.objects.new(key,me);bpy.context.collection.objects.link(ob);ob.color=(.45,.48,.51,1)
for p in me.polygons:p.use_smooth=True
port=report[key]['port_semantic_cm']
bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.28,location=port)
mark=bpy.context.object;mark.show_in_front=True;mark.color=(1,.02,.02,1)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('World');scene.world.color=(.07,.07,.07)
scene.render.resolution_x=1100;scene.render.resolution_y=700;scene.render.resolution_percentage=100
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';camdata.ortho_scale=width;camdata.clip_end=2000
for suffix,offset in [('detail_p',(0,100,8)),('detail_n',(0,-100,8)),('detail_top',(0,8,100)),('detail_bottom',(0,-8,-100))]:
 cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(O/'Views'/f'{key}_{suffix}.png');bpy.ops.render.render(write_still=True)
