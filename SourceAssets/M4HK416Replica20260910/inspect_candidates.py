import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
out=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909/M4_EmptyReload_BoltRelease.blend')
r=bpy.data.objects['SK_M4_Infima'];r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();body=bpy.data.objects['M4_M4 Body_Export']
parts=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909/body_parts.json').read_text())
colors=[(.4,.4,.4,1),(1,.15,.1,1),(1,.8,.1,1),(.1,.6,1,1),(.1,1,.2,1)]
body.data.materials.clear()
for color in colors:
 m=bpy.data.materials.new('Diagnostic');m.diffuse_color=color;m.use_nodes=True;next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=color;body.data.materials.append(m)
partmap={v:color for ident,color in [(13,1),(15,2),(16,3),(17,4)] for v in parts[ident]['vertices']}
for p in body.data.polygons:p.material_index=partmap.get(p.vertices[0],0)
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.hide_render=o!=body
 if o.type=='LIGHT':o.hide_render=True
s=bpy.context.scene;root=r.pose.bones['WPN_root'].matrix
target=root@Vector((0,-.07,.07))
d=bpy.data.cameras.new('Handle');c=bpy.data.objects.new('Handle',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.42
for x in [-1,1]:
 ld=bpy.data.lights.new('Light','AREA');ld.energy=60;ld.size=.6;l=bpy.data.objects.new('Light',ld);s.collection.objects.link(l);l.location=target+Vector((x*.4,-.3,.5));l.rotation_euler=(target-l.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
for label,offset in [('rear',(.16,-.25,.17)),('side',(.3,0,.05))]:
 c.location=root@Vector((0,-.07,.07))+root.to_3x3()@Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(out/f'handle_candidates_{label}.png');bpy.ops.render.render(write_still=True)
print('HANDLE_GEOMETRY_REFERENCE_COMPLETE')

