"""Blender background production: WS1 unique gun UV1 and masks, original mesh kept on disk."""
import json,sys
from pathlib import Path
import bpy,numpy as np
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/'A762'))
import bake_a762 as B
B.GEO=HERE/'Input'
plan=json.loads((HERE/'slot_plan.json').read_text())
OUT=HERE/'Bake'
REPORT=OUT/'bake_receipt.json'
report=json.loads(REPORT.read_text()) if REPORT.exists() else {'assets':{},'tested':False}
def record():REPORT.write_text(json.dumps(report,indent=1),encoding='utf-8')
def remove_slots(ob,indices):
 B.select_only(ob)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
 ids=np.empty(len(ob.data.polygons),np.int32);ob.data.polygons.foreach_get('material_index',ids)
 ob.data.polygons.foreach_set('select',np.isin(ids,indices))
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.delete(type='FACE');bpy.ops.object.mode_set(mode='OBJECT')

def seat(ob,order):
 bones=json.loads((HERE/'Input'/'SVD_bones.json').read_text())
 pose=json.loads((OUT/'seated_pose.json').read_text())
 names=bones['bones'];dom=np.array(bones['dominant'])
 me=ob.data;v=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3)
 n=np.array([tuple(x.vector) for x in me.corner_normals])
 vi=np.array([x.vertex_index for x in me.loops]);bind=v.copy();norm=n.copy()
 for name,d in pose['bones'].items():
  if name not in names:continue
  matrix=np.array(d);sel=dom==names.index(name)
  # Geometry loader mirrors UE Y; resulting Blender geometry units are cm.
  v[sel]=v[sel]@matrix[:3,:3].T+matrix[:3,3]*100
  mask=sel[vi];n[mask]=n[mask]@np.linalg.inv(matrix[:3,:3])
 me.vertices.foreach_set('co',v.ravel());me.update()
 me.normals_split_custom_set(n.tolist())
 return int((np.linalg.norm(bind-v,axis=1)>1e-3).sum())

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=B.setup_cycles()
for key,entry in plan.items():
 specs={k:s for k,s in entry['slots'].items() if s['action']=='preset' and s['mask']=='bake'}
 if not specs:continue
 names=set(s['mask_name'] for s in specs.values())
 if all(name in report['assets'] and (OUT/(name+'.png')).exists() for name in names):continue
 ob,h,order=B.build_object(key,np.zeros(3))
 for other in scene.objects:other.hide_render=other is not ob
 if key=='SVD':
  B.make_uv1(ob,h)
  uv=np.empty(len(ob.data.loops)*2,np.float32);ob.data.uv_layers['UV1'].data.foreach_get('uv',uv)
  uv=uv.reshape(-1,3,2)[:,np.argsort(order)];uv[...,1]=1-uv[...,1]
  header={'triangles':len(ob.data.polygons),'position_checksum':B.report['inputs'][key]['position_checksum']}
  with open(OUT/'SVD_uv1.bin','wb') as f:f.write((json.dumps(header)+'\n').encode());f.write(uv.astype(np.float32).tobytes())
  report['seated_vertices']=seat(ob,order)
  remove_slots(ob,list(B.arm_slots(h))+[i for i,n in enumerate(h['slots']) if 'ScopeLens' in n])
  uv_name='UV1'
 else:uv_name='UV0'
 dens=B.densify(ob)
 vp=B.vertex_masks(ob)
 print('SVD_WS_VERTEX',key,dens,vp,flush=True)
 # Each material samples its own mask; all gun slots share the unique UV1 body mask.
 images={name:bpy.data.images.new(name+'_bake',spec['resolution'],spec['resolution'],alpha=True,float_buffer=True)
         for name,spec in {s['mask_name']:s for s in specs.values()}.items()}
 dummy=bpy.data.images.new(key+'_unused_bake',32,32,alpha=True,float_buffer=True)
 for image in [*images.values(),dummy]:image.colorspace_settings.name='Non-Color'
 ob.data.uv_layers.active=ob.data.uv_layers[uv_name]
 for i,m in enumerate(ob.data.materials):
  target,_=B.bake_material(m)
  spec=specs.get(h['slots'][i])
  target.image=images[spec['mask_name']] if spec else dummy
  m.node_tree.nodes.active=target
 B.select_only(ob)
 bpy.ops.object.bake(type='EMIT',margin=8,margin_type='EXTEND',use_clear=True)
 for name,image in images.items():
  report['assets'][name]={'mesh':key,'uv':uv_name,'source':'A762 WS1 bevel + dihedral + offset rays',
      'densified':dens,'vertex_pass':vp,'texture':B.finish(image,OUT/(name+'.png'))}
  print('SVD_WS_BAKED',name,flush=True)
 if key=='SVD':
  bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'SVD_SurfaceBake.blend'),compress=True)
 record()
 bpy.data.objects.remove(ob,do_unlink=True)
 for image in [*images.values(),dummy]:bpy.data.images.remove(image)
print('SVD_WS_BAKE_COMPLETE',len(report['assets']),flush=True)
