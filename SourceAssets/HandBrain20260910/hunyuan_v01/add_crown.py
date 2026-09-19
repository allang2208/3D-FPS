import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'handbrain_rig_prepared.blend'))
rig=bpy.data.objects['SK_HandBrain'];old=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(root.parent/'hunyuan_attack_source_v01/handbrain_hunyuan_attack_source_v01_clean.glb'))
fan=next(o for o in bpy.data.objects if o not in old and o.type=='MESH');fan.name='HandBrain_CrownHands'
bpy.context.view_layer.objects.active=fan;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(fan.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,1.61),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-1.61)<.0001 for v in e.verts)]
if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(fan.data);bm.free()
for v in fan.data.vertices:v.co.z+=.23
dec=fan.modifiers.new('Crown reduction','DECIMATE');dec.ratio=min(1,24000/len(fan.data.polygons));bpy.ops.object.modifier_apply(modifier=dec.name)
fan.data.normals_split_custom_set([(0,0,0)]*len(fan.data.loops))
fan.data.validate(verbose=True,clean_customdata=False)
for p in fan.data.polygons:p.use_smooth=True
for mat in fan.data.materials:
    nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    old=bs.inputs['Base Color'].links[0].from_socket
    mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(.67,.76,.56,1)
    nt.links.new(old,mul.inputs[1]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
    for link in list(bs.inputs['Metallic'].links):nt.links.remove(link)
    bs.inputs['Metallic'].default_value=0
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
b=rig.data.edit_bones.new('fan_mount');b.head=(0,0,1.6);b.tail=(0,0,1.8);b.parent=rig.data.edit_bones['cranium']
for j in range(8):
    a=j*math.tau/8;b=rig.data.edit_bones.new(f'fan_{j:02}')
    b.head=(.32*math.cos(a),.28*math.sin(a),1.78);b.tail=(.55*math.cos(a),.48*math.sin(a),2.12);b.parent=rig.data.edit_bones['fan_mount']
bpy.ops.object.mode_set(mode='OBJECT')
groups=[fan.vertex_groups.new(name=f'fan_{j:02}') for j in range(8)]
for v in fan.data.vertices:
    a=(math.atan2(v.co.y,v.co.x)%math.tau)*8/math.tau;j=int(a);t=a-j
    groups[j].add([v.index],1-t,'REPLACE');groups[(j+1)%8].add([v.index],t,'REPLACE')
fan.parent=rig;mod=fan.modifiers.new('Crown skin','ARMATURE');mod.object=rig
report=json.loads((root/'build_report.json').read_text());report.update({'crown_triangles':len(fan.data.polygons),'bone_count':len(rig.data.bones),'crown_method':'Raised hands reconstructed from Hunyuan attack reference; independently skinned fan'})
(root/'build_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'handbrain_rig_complete.blend'))
