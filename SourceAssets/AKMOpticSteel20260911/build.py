import bpy,json,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent
sources={'panoramic_red_dot':S/'PanoramicRedDot20260911/GameIntegration/SM_PanoramicRedDot.fbx','prism_scope_2x':S/'PrismScope2X20260911/MachinedControls/SM_PrismScope2X.fbx','lpvo_1_6x':S/'LPVO1to6X20260911/SM_LPVO1to6X.fbx','ring':S/'LPVO1to6X20260911/SM_LPVORing.fbx','holographic':S/'AKMArmSupport20260911/SM_AKM_optic.fbx'}
r={}
for k,path in sources.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];before=[]
 for o in obs:
  me=o.data
  if len(me.uv_layers)==0:me.uv_layers.new(name="UVMap")
  before.append(([tuple(v.co) for v in me.vertices],[tuple(x.uv) for x in me.uv_layers[0].data]));uv=me.uv_layers.new(name='AKMSteelPhysicalUV')
  for f in me.polygons:
   axis=max(range(3),key=lambda i:abs(f.normal[i]));axes=([1,2] if axis==0 else [0,2] if axis==1 else [0,1])
   for li in f.loop_indices:
    v=o.matrix_world@me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.12+.5,v[axes[1]]/.025+.5)
  if k in ('prism_scope_2x','lpvo_1_6x'):
   from mathutils import Vector
   col=me.color_attributes.new(name='AKMMetalRegion',type='BYTE_COLOR',domain='CORNER');me.color_attributes.active_color=col
   for face in me.polygons:
    c=o.matrix_world@face.center;n=(o.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized();rad=Vector((0,c.y,c.z-.04));weight=0. if abs(n.x)<.8 and n.dot(rad)<-.0001 else 1.
    for li in face.loop_indices:col.data[li].color=(weight,weight,weight,1)
  assert before[-1][0]==[tuple(v.co) for v in me.vertices];assert before[-1][1]==[tuple(x.uv) for x in me.uv_layers[0].data]
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.wm.save_as_mainfile(filepath=str(O/(path.stem+'.blend')));bpy.ops.export_scene.fbx(filepath=str(O/path.name),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
 r[k]={'source':str(path),'fbx':path.name,'vertices_unchanged':True,'original_uv_unchanged':True,'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs)}
(O/'geometry.json').write_text(json.dumps(r,indent=2));print('AKM_STEEL_UV_PASS')
