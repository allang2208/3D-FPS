import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'RefinementR4';O=R/'Authored'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
bpy.ops.wm.open_mainfile(filepath=str(O/'Nun_InterfacesR4.blend'))
# Always rebuild delivered interfaces from the latest JSON, not older blend snapshots.
for file,name in [('head.json','SK_NunHead'),('trim.json','SK_Nun_CollarCross'),('boots.json','SK_Nun_Boots')]:
 data=read(O/file);bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
 me=bpy.data.meshes.new(name);me.from_pydata(data['positions'],[],[t[::-1] for t in data['triangles']]);me.update();me.uv_layers.new(name='UVMap')
 for f,uv in zip(me.polygons,data['uv']):
  f.use_smooth=True
  for li,xy in zip(f.loop_indices,uv[::-1]):me.uv_layers.active.data[li].uv=(xy[0],1-xy[1])
 me.normals_split_custom_set([n for ns in data['normals'] for n in ns[::-1]])
 ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob)
 for bone in data['bones']:ob.vertex_groups.new(name=bone['name'])
 for i,weights in enumerate(data['weights']):
  for bi,w in weights:ob.vertex_groups[int(bi)].add([i],w,'REPLACE')
with bpy.data.libraries.load(str(O/'Nun_RefinementR4.blend'),link=False) as (src,dst):dst.objects=[name for name in src.objects if name.startswith('Nun_LowBun_')]
for ob in dst.objects:bpy.context.scene.collection.objects.link(ob)
with bpy.data.libraries.load(str(N/'ProductionR1/Authored/ChapelNun_Complete_Source.blend'),link=False) as (src,dst):dst.objects=[name for name in src.objects if name in ('Nun_Robe_Reference','Kaitlin_Nun_Rig')]
for ob in dst.objects:bpy.context.scene.collection.objects.link(ob)
rig=bpy.data.objects['Kaitlin_Nun_Rig']
for name in ('SK_NunHead','SK_Nun_CollarCross','SK_Nun_Boots'):
 ob=bpy.data.objects[name];mod=ob.modifiers.new('NativeFemaleBinding','ARMATURE');mod.object=rig;ob.parent=rig
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb'))
source=next(ob for ob in bpy.data.objects if ob not in before and ob.type=='MESH');face_mat=source.data.materials[0]
def plain(name,rgb,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();b=nt.nodes.new('ShaderNodeBsdfPrincipled');b.name='Principled BSDF';output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(b.outputs['BSDF'],output.inputs['Surface']);b.inputs['Base Color'].default_value=(*rgb,1);b.inputs['Roughness'].default_value=rough;return m
neck=plain('Nun_MeshyMatchedNeck',(.4,.23,.13),.55);nt=neck.node_tree;bs=nt.nodes.get('Principled BSDF')
tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'Textures/Neck_base_color.png'));nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
mr=nt.nodes.new('ShaderNodeTexImage');mr.image=bpy.data.images.load(str(O/'Textures/Neck_metallic_roughness.png'));mr.image.colorspace_settings.name='Non-Color'
sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(mr.outputs['Color'],sep.inputs['Color']);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
d=read(O/'head.json');me=bpy.data.objects['SK_NunHead'].data
for m in (face_mat,face_mat,face_mat):me.materials.append(m)
for f,mi in zip(me.polygons,d['triangle_materials']):f.material_index=mi
for ob in list(bpy.data.objects):
 if ob not in before:bpy.data.objects.remove(ob,do_unlink=True)
ivory=plain('Nun_LinenPreview',(.68,.65,.58),.84);black=plain('Nun_BlackWoolPreview',(.015,.016,.018),.84);metal=plain('Nun_IronPreview',(.12,.12,.12),.46)
metal.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.8
trim=read(O/'trim.json');me=bpy.data.objects['SK_Nun_CollarCross'].data
for m in (ivory,black,metal):me.materials.append(m)
for f,mi in zip(me.polygons,trim['triangle_materials']):f.material_index=mi
boots=read(O/'boots.json');me=bpy.data.objects['SK_Nun_Boots'].data
for i in range(7):me.materials.append(plain('NativeBootPreview_'+str(i),(.055,.031,.018),.52))
me.materials.append(black)
for f,mi in zip(me.polygons,boots['triangle_materials']):f.material_index=mi
hair=bpy.data.materials.new('NativeBlackHairPreview');hair.use_nodes=True;nt=hair.node_tree;nt.nodes.clear();output=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfHairPrincipled');bs.parametrization='MELANIN';bs.inputs['Melanin'].default_value=.76;bs.inputs['Melanin Redness'].default_value=.025;bs.inputs['Roughness'].default_value=.37;nt.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
for ob in bpy.data.objects:
 if ob.name.startswith('Nun_LowBun_'):ob.data.materials.append(hair);ob['ue_material']='/Game/Characters/ChapelNun20261115/RefinementR4/Materials/MI_Nun_Hair'
for im in bpy.data.images:
 if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ChapelNun_Final_R4.blend'))
# Report broad-phase contacts separately from the final exact intersection check.
head=read(O/'head.json');robe=read(N/'ProductionR1/Inputs/native_robe.json')
def tree(d,keep):return BVHTree.FromPolygons([Vector(p) for p in d['positions']],[t[::-1] for t,m in zip(d['triangles'],d['triangle_materials']) if keep(m)],all_triangles=True)
collar=tree(trim,lambda m:m==0);h=tree(head,lambda m:True);r=tree(robe,lambda m:m!=9)
report={'collar_neck_triangle_overlaps':len(collar.overlap(h)),'collar_outer_robe_triangle_overlaps':len(collar.overlap(r)),'scope':'Static authored LOD0 surfaces; no cloth motion assertion','source_blend':str(O/'ChapelNun_Final_R4.blend')}
(R/'collar_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
