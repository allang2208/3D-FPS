import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'PrismHandstop_Raw.blend'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=o;o.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(o.data)
left=min(v.co.x for v in bm.verts);right=max(v.co.x for v in bm.verts)
# The service interpreted the concept sheet as three separated objects.
# Retain its left object without replacing it by a hand-authored mesh.
threshold=left+(right-left)*.43
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x>threshold],context='VERTS')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(o.data);bm.free();o.data.update()
before=len(o.data.polygons)
points=[v.co for v in o.data.vertices];lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
scale=.065/(hi.z-lo.z);center=(lo+hi)/2
for v in o.data.vertices:
 # Generated side view points toward screen left; use +X as game-forward.
 v.co=Vector((-(v.co.x-center.x)*scale,-(v.co.y-center.y)*scale,(v.co.z-hi.z)*scale))
o.name='SM_PrismHandstop';o.data.update()
dec=o.modifiers.new('Game mesh reduction','DECIMATE');dec.ratio=min(1,16000/before);dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
for p in o.data.polygons:p.use_smooth=True
# Preserve generated UVs and normal texture. Calibrate a graphite finish;
# the returned PBR base color is pale compared with the reference.
mat=o.data.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
for l in list(bs.inputs['Base Color'].links):links.remove(l)
bs.inputs['Base Color'].default_value=(.065,.072,.081,1)
for socket in ['Roughness','Metallic']:
 for l in list(bs.inputs[socket].links):links.remove(l)
bs.inputs['Roughness'].default_value=.52;bs.inputs['Metallic'].default_value=.25
normal=next((n.image for n in nodes if n.type=='TEX_IMAGE' and n.image and 'normal' in n.image.name.lower()),None)
if normal:normal.filepath_raw=str(P/'T_Prism_Normal.png');normal.file_format='PNG';normal.save()
# Use explicit surface materials: some service GLBs route a second shader to
# the output, so editing a named Principled node alone is not authoritative.
o.data.materials.clear()
for name,color,metallic,rough in [('Prism_Polymer',(.028,.032,.039,1),.05,.68),('Prism_Saddle',(.09,.10,.115,1),.65,.45)]:
 m=bpy.data.materials.new(name);m.use_nodes=True
 shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 shader.inputs['Base Color'].default_value=color;shader.inputs['Metallic'].default_value=metallic;shader.inputs['Roughness'].default_value=rough
 o.data.materials.append(m)
for face in o.data.polygons:face.material_index=1 if face.center.z>-.014 else 0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'PrismHandstop_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'SM_PrismHandstop.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
bpy.ops.export_scene.gltf(filepath=str(P/'PrismHandstop.glb'),use_selection=True,export_apply=True)
(P/'mesh_report.json').write_text(json.dumps({'source':'Hunyuan3D 3.1 prism_handstop_v01 left reconstructed object','source_faces':before,'final_faces':len(o.data.polygons),'dimensions_m':list(o.dimensions),'selection_threshold':threshold,'method':'Separate left reconstruction, uniform scale, orientation, decimation; preserve generated UV and normal, graphite material calibration'},indent=2))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.2,.2,.2,1)
center=Vector((0,0,-.0325));span=.08
def aim(a):a.rotation_euler=(center-a.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=.095;s.camera=cam
for loc,power in [((1,-2,3),500),((-2,-1,1),350),((0,2,2),600)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(loc)*span);a=bpy.context.object;a.data.energy=power*span*span;a.data.size=span*2;aim(a)
for name,loc in [('side',(0,3,0)),('front',(3,0,0)),('beauty',(2,3,1)),('back',(0,-3,0))]:
 cam.location=center+Vector(loc)*span;aim(cam);s.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
print('PRISM_PREPARE_PASS')
