"""Author a continuous thick receiver cover and bake the Saiga WS1.1 atlas."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KRefine20261017'
S=P/'SourceAssets/Saiga12K20261017/Authoring'
g=json.loads((S/'source_geometry.json').read_text());islands=json.loads((S/'source_islands.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
def pos(v):return (-v[2]*1.25+.08,-v[0]*1.25-11.52,v[1]*1.25-1.23)
def source_normal(v):return (-v[2],-v[0],v[1])
def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
materials={}
def material(name):
 if name not in materials:
  m=bpy.data.materials.new('Saiga12K_'+name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF')
  poly=name in ('Stock','RearGrip','Handguard','Magazine','ShellPlastic')
  bs.inputs['Base Color'].default_value=(.019,.019,.018,1) if poly else (.034,.035,.037,1)
  bs.inputs['Metallic'].default_value=0 if poly or name=='ReceiverInterior' else 1
  bs.inputs['Roughness'].default_value=.55 if poly else .40;materials[name]=m
 return materials[name]
partfaces={}
for ii,island in enumerate(islands):
 if ii==19:continue
 b=island['bone'];part='Body'
 if b=='mag_02':part='Magazine'
 elif b=='bolt_01':part='Bolt'
 elif b=='safety_06':part='Safety'
 elif b=='magrelease_05':part='MagRelease'
 elif b in ('bullet_03','bullets_04'):part='ShellBrass' if any(m in (9,10,12,13) for m in island['materials']) else 'ShellPlastic'
 elif ii==21:part='Trigger'
 elif ii==1:part='Stock'
 elif ii==8:part='RearGrip'
 elif ii==4:part='Handguard'
 partfaces.setdefault(part,[]).extend(island['faces'])
objects=[]
for part,faces in partfaces.items():
 ids=sorted({v for fi in faces for v in g['triangles'][fi]});unique={};vertices=[];imap={}
 for vi in ids:
  p=pos(g['positions'][vi]);key=tuple(round(x,6) for x in p)
  if key not in unique:unique[key]=len(vertices);vertices.append(p)
  imap[vi]=unique[key]
 me=bpy.data.meshes.new(part);me.from_pydata(vertices,[],[[imap[v] for v in g['triangles'][fi]] for fi in faces]);me.update()
 ob=bpy.data.objects.new('Saiga12K_'+part,me);scene.collection.objects.link(ob);objects.append(ob)
 me.materials.append(material(part))
 for f in me.polygons:f.use_smooth=True
 me.normals_split_custom_set([source_normal(g['normals'][v]) for fi in faces for v in g['triangles'][fi]])

# Reconstruct the roof from the intact half, retaining the original profile.
left=[fi for fi in islands[19]['faces'] if max(g['positions'][v][2] for v in g['triangles'][fi])<=.00001]
ids=sorted({v for fi in left for v in g['triangles'][fi]});imap={v:i for i,v in enumerate(ids)}
verts=[pos(g['positions'][i]) for i in ids];n=len(verts)
verts+= [( .16-x,y,z) for x,y,z in verts]
faces=[[imap[v] for v in g['triangles'][fi]] for fi in left]
faces +=[[v+n for v in reversed(f)] for f in faces.copy()]
me=bpy.data.meshes.new('ReceiverCover');me.from_pydata(verts,[],faces);me.update()
cover=bpy.data.objects.new('Saiga12K_ReceiverCover',me);scene.collection.objects.link(cover)
me.materials.append(material('ReceiverCover'));me.materials.append(material('ReceiverInterior'))
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
select(cover)
solid=cover.modifiers.new('0.7 mm receiver-cover wall','SOLIDIFY');solid.thickness=.07;solid.offset=-1;solid.use_even_offset=True;solid.material_offset=1;solid.material_offset_rim=1
bpy.ops.object.modifier_apply(modifier=solid.name)
# Side-only ejection slot. Its top is below the continuous roof and shoulder.
lo=Vector(pos((3.38,4.30,1.55)));hi=Vector(pos((-8.85,6.27,.52)))
bpy.ops.mesh.primitive_cube_add(size=1,location=(lo+hi)/2);cut=bpy.context.object;cut.name='Side ejection window tool';cut.dimensions=hi-lo
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
select(cover);mod=cover.modifiers.new('Recessed side ejection port','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
bevel=cover.modifiers.new('Machined edge 0.18 mm','BEVEL');bevel.width=.018;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(40)
bpy.ops.object.modifier_apply(modifier=bevel.name)
for f in cover.data.polygons:f.use_smooth=True
weighted=cover.modifiers.new('Area-weighted cover normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=35
bpy.ops.object.modifier_apply(modifier=weighted.name)
objects.append(cover)
cover['repair']='Continuous mirrored original roof, real 0.7 mm wall, lower side ejection port; original outer profile retained'
select(cover)
for ob in objects:ob.select_set(True)
bpy.ops.object.join();main=bpy.context.object;main.name='Saiga12K_Refined_Gun'
tri=main.modifiers.new('Runtime triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
me=main.data
while me.uv_layers:me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name='UV0');me.uv_layers.active_index=0;select(main)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.0015,area_weight=0,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers.new(name='UV1');uv0=me.uv_layers['UV0'];uv1=me.uv_layers['UV1']
for i in range(len(me.loops)):uv1.data[i].uv=uv0.data[i].uv
for i,m in enumerate(me.materials):
 if m is None:me.materials[i]=material('ReceiverInterior')
names=[m.name.removeprefix('Saiga12K_') for m in me.materials]
payload={'positions':[[v.co.x,-v.co.y,v.co.z] for v in me.vertices],'triangles':[],'normals':[],'uv':[],'parts':[],'slot_names':names,'seated_root_cm':True}
area={};uvarea={}
for face in me.polygons:
 order=list(face.loop_indices)[::-1]
 payload['triangles'].append([me.loops[i].vertex_index for i in order]);payload['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in order])
 uv=[[float(uv0.data[i].uv.x),1-float(uv0.data[i].uv.y)] for i in order];payload['uv'].append(uv);part=names[face.material_index];payload['parts'].append(part)
 area[part]=area.get(part,0)+face.area
 a,b,c=np.array(uv);uvarea[part]=uvarea.get(part,0)+abs(float(np.cross(b-a,c-a)))/2
payload['uv_per_cm']={k:math.sqrt(uvarea[k]/a) for k,a in area.items()}
(O/'Authoring/gun.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_Refined.blend'),compress=True)
bpy.ops.export_scene.fbx(filepath=str(O/'Authoring/Saiga12K_Refined.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,global_scale=.01)
print('SAIGA_COVER_AND_UV_AUTHORED',len(me.polygons),flush=True)

# Production bake only: no camera, screenshot or acceptance rendering.
sys.path.insert(0,str(P/'SourceAssets/WeaponSurface20260930/A762'))
import bake_a762 as bake
bake.EDGE_RADIUS=.05;bake.RAYS=24;bake.setup_cycles()
copy=main.copy();copy.data=main.data.copy();copy.name='Saiga12K_WS11_BAKE';scene.collection.objects.link(copy);main.hide_render=True;main.hide_set(True)
select(copy);bm=bmesh.new();bm.from_mesh(copy.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bm.to_mesh(copy.data);bm.free()
bake.densify(copy,max_edge=.35,rounds=5)
bm=bmesh.new();bm.from_mesh(copy.data)
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(copy.data);bm.free();bake.vertex_masks(copy)
image=bpy.data.images.new('Saiga12K_WS11_SurfaceMask',2048,2048,alpha=True,float_buffer=True);image.colorspace_settings.name='Non-Color'
bake.bake(copy,image,'UV1');result=bake.finish(image,O/'Textures/T_Saiga12K_WS11_Mask.png')
(O/'Receipts/authoring.json').write_text(json.dumps({'complete':True,'triangles':len(me.polygons),'cover_thickness_cm':.07,'edge_radius_cm':.018,'uv_per_cm':payload['uv_per_cm'],'mask':result,'runtime_tested':False},indent=2),encoding='utf-8')
print('SAIGA_WS11_BAKE_SAVED',flush=True)
