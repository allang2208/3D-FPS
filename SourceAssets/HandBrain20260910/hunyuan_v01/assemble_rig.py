import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'handbrain_body_prepared.blend'))
rig=bpy.data.objects['SK_HandBrain'];body=bpy.data.objects['HandBrain_Body']
old=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(root.parent/'hunyuan_attack_source_v01/handbrain_hunyuan_attack_source_v01_clean.glb'))
arm=next(o for o in bpy.data.objects if o not in old and o.type=='MESH')
arm.name='HandBrain_AttackArm'
bpy.context.view_layer.objects.active=arm
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(arm.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
# At y=-.70 the observed source cross section contains only the large arm.
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,-.70,0),plane_no=(0,1,0),clear_outer=True,clear_inner=False)
boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y+.70)<.0001 for v in e.verts)]
if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(arm.data);bm.free()
# Rotate one source arm toward +X; discard generated mirrored second arm.
source_anchor=Vector((.035,-.70,1.22));anchor=Vector((.00,-.17,1.62))
rotation=Matrix.Rotation(math.radians(77),3,'Z');scale=1.60
for v in arm.data.vertices:v.co=anchor+rotation@(v.co-source_anchor)*scale
dec=arm.modifiers.new('Arm reduction','DECIMATE');dec.ratio=min(1,18000/len(arm.data.polygons))
bpy.ops.object.modifier_apply(modifier=dec.name)
arm.data.normals_split_custom_set([(0,0,0)]*len(arm.data.loops))
for p in arm.data.polygons:p.use_smooth=True
for mat in arm.data.materials:
    if not mat.use_nodes:continue
    nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    if bs.inputs['Base Color'].is_linked:
        old=bs.inputs['Base Color'].links[0].from_socket
        mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
        mul.inputs[2].default_value=(.67,.76,.56,1)
        nt.links.new(old,mul.inputs[1]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
    for link in list(bs.inputs['Metallic'].links):nt.links.remove(link)
    bs.inputs['Metallic'].default_value=0
def trans(p):return anchor+rotation@(Vector(p)-source_anchor)*scale
elbow=trans((.13,-1.04,1.07));wrist=trans((.28,-1.34,.80));tip=trans((.40,-1.67,.57))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
def bone(n,h,t,parent):
    b=rig.data.edit_bones.new(n);b.head=h;b.tail=t;b.parent=rig.data.edit_bones[parent]
bone('arm_mount',anchor,anchor+Vector((0,0,.2)),'cranium')
bone('attack_upper',anchor,elbow,'arm_mount')
bone('attack_forearm',elbow,wrist,'attack_upper')
bone('attack_fist',wrist,tip,'attack_forearm')
bpy.ops.object.mode_set(mode='OBJECT')
groups={n:arm.vertex_groups.new(name=n) for n in ['attack_upper','attack_forearm','attack_fist']}
for v in arm.data.vertices:
    p=rotation.inverted()@(v.co-anchor)/scale+source_anchor
    t=-p.y
    if t<1.04:
        f=max(0,min(1,(t-.92)/.24));weights={'attack_upper':1-f,'attack_forearm':f}
    else:
        f=max(0,min(1,(t-1.22)/.24));weights={'attack_forearm':1-f,'attack_fist':f}
    for n,w in weights.items():
        if w>0:groups[n].add([v.index],w,'REPLACE')
mod=arm.modifiers.new('Attack skin','ARMATURE');mod.object=rig;arm.parent=rig
report=json.loads((root/'build_report.json').read_text())
report.update({'attack_arm_pending':False,'attack_arm_triangles':len(arm.data.polygons),'bone_count':len(rig.data.bones),'source_arm_cut_plane_y':-.70,'arm_anchor':list(anchor),'elbow':list(elbow),'wrist':list(wrist),'fist_tip':list(tip),'rig_prepared':True,'rig_visual_verified':False})
(root/'build_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(root/'handbrain_rig_prepared.blend'))
