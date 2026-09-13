"""Add coating projection UVs without changing geometry, UV0 or split normals."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
sources=json.loads((O/'sources.json').read_text())
keys={'M4':['drum','holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','prism'],
      'AKM':['drum','suppressor','brake','titanium_brake','vertical','canted','prism']}
report={}
for ident,info in sources.items():
 family,key=info['family'],info['key']
 if key not in keys.get(family,[]):continue
 before=set(bpy.context.scene.objects)
 bpy.ops.import_scene.fbx(filepath=info['fbx'])
 obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
 if len(obs)>1:bpy.ops.object.join()
 ob=bpy.context.object;ob.name=family+'_'+key
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 me=ob.data
 uv_index=len(me.uv_layers);uv=me.uv_layers.new(name='ReceiverFinishPhysicalUV')
 tile=(.12,.05) if family=='M4' else (.12,.025)
 for f in me.polygons:
  axis=max(range(3),key=lambda i:abs(f.normal[i]));axes=([1,2] if axis==0 else [0,2] if axis==1 else [0,1])
  for li in f.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co
   uv.data[li].uv=(v[axes[0]]/tile[0]+.5,v[axes[1]]/tile[1]+.5)
 interior=family=='M4' and key in ['prism_scope_2x','lpvo_1_6x','lpvo_ring']
 if interior:
  col=me.color_attributes.new(name='ReceiverFinishMetalRegion',type='BYTE_COLOR',domain='CORNER');me.color_attributes.active_color=col
  for f in me.polygons:
   radial=Vector((0,f.center.y,f.center.z-.04))
   weight=0. if abs(f.normal.x)<.8 and f.normal.dot(radial)<-.0001 else 1.
   for li in f.loop_indices:col.data[li].color=(weight,weight,weight,1)
 me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
 folder=O/'FBX'/family;folder.mkdir(parents=True,exist_ok=True)
 path=folder/(key+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 me.calc_loop_triangles()
 report[ident]={'file':str(path),'uv_index':uv_index,'physical_tile_m':tile,'interior_vertex_mask':interior,'export_slots':[m.name for m in me.materials],
                'vertices':len(me.vertices),'triangles':len(me.loop_triangles),'preserved_uv_channels':uv_index}
 ob.hide_set(True);ob.hide_render=True
 (O/'authoring.json').write_text(json.dumps(report,indent=2))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'WeaponAttachmentFinish_Editable.blend'))
print('WEAPON_FINISH_UV_AUTHORED',len(report),flush=True)
