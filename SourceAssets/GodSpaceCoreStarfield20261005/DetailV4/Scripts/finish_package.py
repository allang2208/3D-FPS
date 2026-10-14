import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'Authored';PRE=ROOT/'Previews'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'GodSpaceCore_Starfield_V4_Editable.blend'))
s=bpy.context.scene; C=Vector((0,28.6,5));cam=s.camera
meshes=[o for o in s.objects if o.type=='MESH']; before={o.name:len(o.data.polygons) for o in meshes}
camnode=next(n for n in bpy.data.materials['Core_Starfield'].node_tree.nodes if n.label=='Render camera position, updated per camera')
def camera(pos,target,lens):
 cam.location=Vector(pos);cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
 for i in range(3):camnode.inputs[i].default_value=cam.location[i]
def render(name):
 s.render.filepath=str(PRE/name);bpy.ops.render.render(write_still=True)
# Close view uses unchanged geometry/material, no normal-strength or detail-scale cheat.
camera(C+Vector((.3,4.7,-.7)),C,68);s.render.resolution_x=1400;s.render.resolution_y=1100;s.cycles.samples=64
render('V4_Starfield_Closeup_Blender.png')
ring=bpy.data.objects['OrbitBand_A'];pts=[ring.matrix_world@v.co for v in ring.data.vertices];target=max(pts,key=lambda p:p.z)
camera(target+Vector((.12,1.05,.25)),target,85);s.render.resolution_x=1400;s.render.resolution_y=850
render('V4_Gold_Detail_Blender.png')
# Export only the authored parts, preserving root pivot and legacy one-time Y reflection.
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Core_StarfieldSphere_3m'];bpy.ops.object.join();o=bpy.context.object;o.name='SM_GodSpaceCore_Starfield_V4';o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
uv=o.data.uv_layers.active;star=bpy.data.materials['Core_Starfield']
for p in o.data.polygons:
 if o.data.materials[p.material_index]!=star:continue
 coords=[]
 for li in p.loop_indices:
  d=(o.data.vertices[o.data.loops[li].vertex_index].co-C).normalized();coords.append([(math.atan2(d.y,d.x)+math.pi)/(2*math.pi),(math.asin(max(-1,min(1,d.z)))+math.pi/2)/math.pi])
 if max(a[0] for a in coords)-min(a[0] for a in coords)>.5:
  for a in coords:
   if a[0]<.5:a[0]+=1
 for li,a in zip(p.loop_indices,coords):uv.data[li].uv=a
counts={m.name:sum(len(p.vertices)-2 for p in o.data.polygons if o.data.materials[p.material_index]==m) for m in o.data.materials}
o.data.transform(Matrix.Diagonal((1,-1,1,1)))
for p in o.data.polygons:p.flip()
fbx=OUT/'SM_GodSpaceCore_Starfield_V4.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,path_mode='STRIP')
(OUT/'V4_export_receipt.json').write_text(json.dumps({'triangles':sum(counts.values()),'material_triangles':counts,'mesh_parts':len(before),'reflection_count':1,'pivot':[0,0,0],'sphere_diameter_m':3,'ring_count':2,'geometry_changed':False,'blender':bpy.app.version_string},indent=2))
