import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspect.blend'))
src=bpy.data.objects['AK'];me=src.data
groups=json.loads((O/'components.json').read_text());bone_for={}
for i,g in enumerate(groups):
 bone='WPN_SOCKET_Magazine' if i in [0,44,83,92] else 'WPN_bolt' if i==19 else 'WPN_Trigger' if i==33 else 'WPN_root'
 for v in g['ids']:bone_for[v]=bone
verts=[src.matrix_world@v.co for v in me.vertices];faces=[list(p.vertices) for p in me.polygons];uv=[tuple(x.uv) for x in me.uv_layers.active.data]
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AKMIntegration20260910/EquipCharge/AKM_EquipCharge_Editable.blend')
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
hands=bpy.data.objects['SK_Manny_Arms_Export'];handhash=hashlib.sha256(b''.join(str(tuple(v.co)).encode() for v in hands.data.vertices)).hexdigest()
for o in list(s.objects):
 if o.name.startswith('AKMR_'):bpy.data.objects.remove(o,do_unlink=True)
m=bpy.data.materials.new('M_AKM_Soviet_PBR');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
for kind,pin in [('Base_color','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Normal_OpenGL','Normal')]:
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O/'Source/ak47fbx_extracted/textures'/f'AK_{kind}.png'))
 if kind!='Base_color':t.image.colorspace_settings.name='Non-Color'
 if kind=='Normal_OpenGL':nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs[pin])
 else:l.new(t.outputs['Color'],bs.inputs[pin])
root=r.pose.bones['WPN_root'].matrix.copy();rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
xf=Matrix.Translation((.0008,-.066,.014))@Matrix.Scale(.985,4)
newverts=[rest[bone_for[i]]@pose[bone_for[i]].inverted()@root@xf@v for i,v in enumerate(verts)]
mesh=bpy.data.meshes.new('AKM_Soviet');mesh.from_pydata(newverts,[],faces);mesh.update();mesh.materials.append(m);layer=mesh.uv_layers.new(name='UVMap')
for dst,srcuv in zip(layer.data,uv):dst.uv=srcuv
for p in mesh.polygons:p.use_smooth=True
o=bpy.data.objects.new('AKM_Soviet_Native',mesh);s.collection.objects.link(o);o.parent=r;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
for bone in sorted(set(bone_for.values())):o.vertex_groups.new(name=bone).add([i for i,b in bone_for.items() if b==bone],1,'REPLACE')
mod=o.modifiers.new('NativeArmature','ARMATURE');mod.object=r
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);hands.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_AKM_MannyNative.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
for action in bpy.data.actions:action.use_fake_user=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_Soviet_Editable.blend'))
assert handhash==hashlib.sha256(b''.join(str(tuple(v.co)).encode() for v in hands.data.vertices)).hexdigest()
(O/'build.json').write_text(json.dumps({'source':'https://www.fab.com/listings/d14e05e8-553a-409a-8df0-7c9a8d2c69f4','hand_geometry_sha256':handhash,'vertices':len(verts),'scale':.985,'translation':[.0008,-.066,.014],'components':{'magazine':[0,44,83,92],'bolt':[19],'trigger':[33]},'actions_preserved':[a.name for a in bpy.data.actions],'source_hashes':{str(p.relative_to(O/'Source')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (O/'Source').rglob('*') if p.is_file()}},indent=2))
print('SOVIET_BUILD_PASS')

