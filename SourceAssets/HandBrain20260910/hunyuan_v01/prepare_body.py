"""Prepare a separate deforming candidate; preserve original high mesh and UVs."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root/'handbrain_hunyuan_v01_clean.glb'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
body.name='HandBrain_Body'
bpy.context.view_layer.objects.active=body
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
body.data.normals_split_custom_set([(0,0,0)]*len(body.data.loops))
before=len(body.data.polygons)
dec=body.modifiers.new('Animation mesh 120k','DECIMATE')
dec.ratio=min(1,120000/before)
bpy.ops.object.modifier_apply(modifier=dec.name)
for p in body.data.polygons:p.use_smooth=True
for mat in body.data.materials:
    if not mat.use_nodes:continue
    nt=mat.node_tree
    bs=next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if bs and bs.inputs['Base Color'].is_linked:
        old=bs.inputs['Base Color'].links[0].from_socket
        mul=nt.nodes.new('ShaderNodeMixRGB');mul.name='Olive skin art adjustment'
        mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
        mul.inputs[2].default_value=(0.67,0.76,0.56,1)
        nt.links.new(old,mul.inputs[1]);nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
    if bs:
        # Organic surface. Preserve roughness and normal maps.
        for link in list(bs.inputs['Metallic'].links):nt.links.remove(link)
        bs.inputs['Metallic'].default_value=0
armdata=bpy.data.armatures.new('HandBrain_FunctionalSkeleton')
rig=bpy.data.objects.new('SK_HandBrain',armdata)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig
body.select_set(False);rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
def bone(name,head,tail,parent=None):
    b=armdata.edit_bones.new(name);b.head=head;b.tail=tail
    if parent:b.parent=armdata.edit_bones[parent]
    return b
bone('root',(0,0,0),(0,0,.18))
bone('base',(0,0,.12),(0,0,.50),'root')
bone('neck',(0,0,.5),(0,0,1.05),'base')
bone('cranium',(0,0,1.05),(0,0,1.65),'neck')
for j in range(8):
    a=2*math.pi*j/8
    h=Vector((.34*math.cos(a),.32*math.sin(a),1.55))
    bone(f'crown_{j:02}',h,h+Vector((.15*math.cos(a),.14*math.sin(a),.32)),'cranium')
bpy.ops.object.mode_set(mode='OBJECT')
groups={b.name:body.vertex_groups.new(name=b.name) for b in armdata.bones}
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for v in body.data.vertices:
    z=v.co.z
    neck=smooth(.2,.65,z);head=smooth(.65,1.25,z)
    weights={'base':1-neck,'neck':neck*(1-head),'cranium':head}
    c=.68*smooth(1.45,1.86,z)
    if c:
        a=(math.atan2(v.co.y,v.co.x)%(2*math.pi))*8/(2*math.pi)
        j=int(a);t=a-j
        weights={k:w*(1-c) for k,w in weights.items()}
        weights[f'crown_{j:02}']=c*(1-t)
        weights[f'crown_{(j+1)%8:02}']=c*t
    weights={k:w for k,w in weights.items() if w>1e-5}
    # The bands overlap at most two body bones and two crown bones.
    weights=dict(sorted(weights.items(),key=lambda kv:kv[1],reverse=True)[:4])
    total=sum(weights.values())
    for name,w in weights.items():groups[name].add([v.index],w/total,'REPLACE')
mod=body.modifiers.new('Functional skin','ARMATURE');mod.object=rig
body.parent=rig
rig.show_in_front=True
report={'source_triangles':before,'body_triangles':len(body.data.polygons),'body_vertices':len(body.data.vertices),'method':'UV-preserving collapse reduction; not semantic quad retopology','max_weights':max(len(v.groups) for v in body.data.vertices),'unweighted_vertices':sum(not v.groups for v in body.data.vertices),'body_prepared':True,'attack_arm_pending':True,'animation_verified':False,'ue_runtime_verified':False}
(root/'build_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'handbrain_body_prepared.blend'))
