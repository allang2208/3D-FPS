import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent
report={}
for key,path in [('m4',P.parent/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'),('akm',P.parent/'AKMAttachments20260911/AKM_Attachments_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
 a=bpy.data.actions['AKM_Native_idle' if key=='akm' else 'M4_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
 root=r.matrix_world@r.pose.bones['WPN_root'].matrix;copies=[]
 if key=='akm':
  gun=bpy.data.objects['AKM_Soviet_Native'];adj=[[] for v in gun.data.vertices]
  for e in gun.data.edges:i,j=e.vertices;adj[i].append(j);adj[j].append(i)
  groups=[];seen=set()
  for v in range(len(adj)):
   if v in seen:continue
   stack=[v];seen.add(v);ids=[]
   while stack:
    n=stack.pop();ids.append(n)
    for j in adj[n]:
     if j not in seen:seen.add(j);stack.append(j)
   groups.append(ids)
  stock_ids={i for group in [1,45,46,47,48] for i in groups[group]}
  magazine_group=gun.vertex_groups['WPN_SOCKET_Magazine'].index
  magazine_ids={v.index for v in gun.data.vertices if any(g.group==magazine_group and g.weight>.99 for g in v.groups)}
  magazine_slot=next(i for i,m in enumerate(gun.data.materials) if 'Magazine' in m.name)
  for f in gun.data.polygons:
   if all(i in magazine_ids for i in f.vertices):f.material_index=magazine_slot
  print('STOCK_MAGAZINE_SECTION',len(magazine_ids),sum(f.material_index==magazine_slot for f in gun.data.polygons),[m.name for m in gun.data.materials],flush=True)
  before=hashlib.sha256(repr([(tuple(v.co),[(g.group,g.weight) for g in v.groups]) for v in gun.data.vertices]).encode()).hexdigest()
  m=gun.data.materials[0].copy();m.name='M_AKM_FactoryStock';gun.data.materials.append(m);slot=len(gun.data.materials)-1
  faces=0
  ev=gun.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated=bpy.data.meshes.new_from_object(ev)
  pts=[root.inverted()@ev.matrix_world@v.co for v in evaluated.vertices]
  # Receiver tang belongs to component 0. Its faces beyond the receiver end are
  # part of the removable furniture interface, not the visible receiver shell.
  tang_faces=[f.index for f in gun.data.polygons if all(pts[i].y>.084 for i in f.vertices) and any(pts[i].y>.10 for i in f.vertices) and not all(i in stock_ids for i in f.vertices)]
  bpy.data.meshes.remove(evaluated)
  for f in gun.data.polygons:
   if all(i in stock_ids for i in f.vertices) or f.index in tang_faces:f.material_index=slot;faces+=1
  assert faces>300
  after=hashlib.sha256(repr([(tuple(v.co),[(g.group,g.weight) for g in v.groups]) for v in gun.data.vertices]).encode()).hexdigest();assert before==after
  bpy.ops.object.select_all(action='DESELECT')
  magazine=bpy.data.objects['AKM_FactoryMagazine_Preview'];magazine.hide_set(False)
  for o in [r,gun,magazine,bpy.data.objects['SK_Manny_Arms_Export']]:o.select_set(True)
  bpy.context.view_layer.objects.active=r
  bpy.ops.export_scene.fbx(filepath=str(P/'SK_AKM_StockReady.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
  bpy.ops.wm.save_as_mainfile(filepath=str(P/'AKM_StockSections_Editable.blend'))
  report['akm_split']={'source':str(path),'components':[1,45,46,47,48],'tang_polygon_whitelist':tang_faces,'stock_vertices':len(stock_ids),'stock_polygons':faces,'unchanged_geometry_weights_sha256':after}
 for o in list(s.objects):
  if o.type!='MESH' or not ((key=='m4' and o.name.startswith('M4_') and o.name.endswith('_Export')) or o.name in ['AKM_Soviet_Native','AKM_FactoryMagazine_Preview']):continue
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev);me.transform(root.inverted()@ev.matrix_world);me.transform(Matrix.Scale(100,4))
  ob=bpy.data.objects.new('FIT_'+o.name,me);s.collection.objects.link(ob);copies.append(ob)
  if key=='m4' and 'Stock Classic' in o.name:ob.hide_render=True
  if key=='akm' and o.name=='AKM_Soviet_Native':
   import bmesh
   bm=bmesh.new();bm.from_mesh(me);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==slot],context='FACES');bm.to_mesh(me);bm.free()
 # Standalone evaluated surfaces in gun-root centimeters for repeatable assembly inspection.
 for o in list(s.objects):
  if o not in copies:bpy.data.objects.remove(o,do_unlink=True)
 for col in list(s.collection.children):s.collection.children.unlink(col)
 bpy.ops.wm.save_as_mainfile(filepath=str(P/(key+'_fit_reference.blend')))
report['mounts']={'m4':{'origin_m':[0,.0385,.0725],'rotation_z_deg':90},'akm':{'origin_m':[.0008,.091,.035],'rotation_z_deg':90}}
(P/'fit_preparation.json').write_text(json.dumps(report,indent=2));print('STOCK_FIT_PREPARED',json.dumps(report))
