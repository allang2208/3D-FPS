"""Scoped offline port review: green = calibrated, red = actual fire marker."""
import bpy,json
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
G=json.loads((O/'geometry_report.json').read_text());C=json.loads((O/'calibration.json').read_text())
(O/'AfterViews').mkdir(exist_ok=True)
for key,row in C.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 data=np.load(O/'Geometry'/f'{key}.npz',allow_pickle=True);basis=np.array(G[key]['basis_rows'])
 me=bpy.data.meshes.new(key);me.from_pydata(data['vertices']@basis.T,[],data['faces']);me.update()
 ob=bpy.data.objects.new(key,me);bpy.context.collection.objects.link(ob);ob.color=(.45,.48,.51,1)
 for p in me.polygons:p.use_smooth=True
 for label,pos,col in [('old',row['old_semantic_cm'],(1,.04,.02,1)),('new',row['semantic_cm'],(.03,1,.16,1))]:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.22,location=pos)
  marker=bpy.context.object;marker.name=label;marker.color=col;marker.show_in_front=label=='old'
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
 scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
 scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
 scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('World');scene.world.color=(.07,.07,.07)
 scene.render.resolution_x=1000;scene.render.resolution_y=620;scene.render.resolution_percentage=100
 camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
 camdata.type='ORTHO';camdata.ortho_scale=19 if row['anchor']=='WPN_Slide' else 36;camdata.clip_end=2000
 target=Vector(row['semantic_cm']);target.y=0;sign=row['outward_side']
 for suffix,offset in [('side',(0,sign*100,12)),('top',(0,sign*28,100))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  scene.render.filepath=str(O/'AfterViews'/f'{key}_{suffix}.png');bpy.ops.render.render(write_still=True)
 print('CALIBRATED_PORT_VIEW',key,flush=True)
