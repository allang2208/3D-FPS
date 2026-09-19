import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SourceMatched/AKM_Fab_SourceMatched_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
o=bpy.data.objects['AKMR_Body_Native'];me=o.data
inv=r.data.bones['WPN_root'].matrix_local.inverted()
polys=[p for p in me.polygons if me.materials[p.material_index].name=='M_AKMR_Walnut']
ids=set(v for p in polys for v in p.vertices);points={i:inv@me.vertices[i].co for i in ids}
ys=sorted(set(p.y for p in points.values()));gap=max(range(len(ys)-1),key=lambda i:ys[i+1]-ys[i]);split=(ys[gap]+ys[gap+1])/2
groups={k:[v for v,p in points.items() if (p.y<split)==k] for k in [False,True]}
before=hashlib.sha256(b''.join(bytes(str(tuple(v.co)),'ascii') for v in me.vertices)).hexdigest()
report={'split':split,'groups':{}}
for k,vs in groups.items():
 center=sum((points[i] for i in vs),Vector())/len(vs)
 lo=Vector(tuple(min(points[i][j] for i in vs) for j in range(3)));hi=Vector(tuple(max(points[i][j] for i in vs) for j in range(3)))
 # Cylindrical unwrap follows the longitudinal wood axis, with seam underneath.
 # Separate centers and texture offsets prevent repeated stock/handguard patches.
 rx=max((hi.x-lo.x)/2,.001);rz=max((hi.z-lo.z)/2,.001)
 offset=.56 if k else .17
 for p in polys:
  if p.vertices[0] not in vs:continue
  angles=[math.atan2((points[me.loops[l].vertex_index].x-center.x)/rx,(points[me.loops[l].vertex_index].z-center.z)/rz) for l in p.loop_indices]
  if max(angles)-min(angles)>math.pi:angles=[x+2*math.pi if x<0 else x for x in angles]
  for l,angle in zip(p.loop_indices,angles):
   pos=points[me.loops[l].vertex_index]
   me.uv_layers.active.data[l].uv=(offset+angle/(2*math.pi)*.38,.25+(pos.y-lo.y)*1.25)
 report['groups'][str(k)]={'vertices':len(vs),'min':list(lo),'max':list(hi),'texture_offset':offset}
assert before==hashlib.sha256(b''.join(bytes(str(tuple(v.co)),'ascii') for v in me.vertices)).hexdigest()
m=bpy.data.materials['M_AKMR_Walnut'];m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs['Surface'])
base=O/'Source/walnut_veneer_tfdoebqc_4_extracted'
tex={}
for kind in ['BaseColor','Roughness','Normal']:
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(base/f'Walnut_Veneer_tfdoebqc_4K_{kind}.jpg'));tex[kind]=t
 if kind!='BaseColor':t.image.colorspace_settings.name='Non-Color'
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(.8,.38,.25,1);l.new(tex['BaseColor'].outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],bs.inputs['Base Color'])
rough=n.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=.12;rough.inputs[2].default_value=.30;l.new(tex['Roughness'].outputs[0],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.06;l.new(tex['Normal'].outputs[0],normal.inputs[1]);l.new(normal.outputs[0],bs.inputs['Normal'])
bs.inputs['Coat Weight'].default_value=0
bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
for ob in s.objects:
 if ob.type=='MESH' and (ob.name.startswith('AKMR_') or ob.name=='SK_Manny_Arms_Export'):ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_AKM_MannyNative.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_WalnutFab_Editable.blend'))
report['geometry_sha256']=before;report['source']='https://www.fab.com/listings/67d7d60c-e92a-4fd9-8994-787f121aeaf9'
(O/'uv_report.json').write_text(json.dumps(report,indent=2));print('AKM_WALNUT_BUILD_PASS')
