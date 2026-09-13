import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
# Keep the existing hand pose; use its glove surface for a rigid contact offset.
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend')
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['A_M4_Foregrip_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
hand=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in hand.vertex_groups}
ids={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_l') and any(groups[g.group].startswith(x) for x in ['hand','index','middle','ring','pinky','thumb']))>.5}
ev=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();me.calc_loop_triangles()
pose_to_bind=r.matrix_world@r.data.bones['WPN_root'].matrix_local@(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()
hv=[pose_to_bind@ev.matrix_world@v.co for v in me.vertices];hf=[tuple(t.vertices) for t in me.loop_triangles if all(i in ids for i in t.vertices)];ev.to_mesh_clear()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Selected_Meshy_Source.fbx'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.data.transform(high.matrix_world);high.matrix_world=Matrix.Identity(4);high.data.transform(Matrix.Rotation(math.pi/2 if high.dimensions.x>high.dimensions.y else 0,4,'Z'));high.name='Resonance_Meshy_Master'
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
# Retain the selected Meshy topology; reduction is outside this replacement.
canonical=low.data.copy();high.hide_set(True);high.hide_render=True

def bounds(points):return Vector([min(v[i] for v in points) for i in range(3)]),Vector([max(v[i] for v in points) for i in range(3)])
sl,sh=bounds([v.co for v in canonical.vertices]);report={};m4bounds=None
for family in ['M4','AKM','QBZ191']:
 before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=str(P/(family+'_reference.fbx')))
 obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH'];points=[o.matrix_world@v.co for o in obs for v in o.data.vertices];tl,th=bounds(points)
 if family=='M4':m4bounds=(tl.copy(),th.copy())
 # Preserve target mounting crown and authored grip reach in the existing asset frame.
 target_top=[v for v in points if v.z>th.z-(th.z-tl.z)*.07]
 source_top=[v.co for v in canonical.vertices if v.co.z>sh.z-(sh.z-sl.z)*.07]
 tc=(bounds(target_top)[0]+bounds(target_top)[1])/2;sc=(bounds(source_top)[0]+bounds(source_top)[1])/2
 sb=[v.co.y for v in canonical.vertices if v.co.z<sl.z+(sh.z-sl.z)*.25];tb=[v.y for v in points if v.z<tl.z+(th.z-tl.z)*.25]
 sign=1 if (sum(sb)/len(sb)-sc.y)*(sum(tb)/len(tb)-tc.y)>=0 else -1
 scale=Vector([(th[i]-tl[i])/(sh[i]-sl[i]) for i in range(3)])
 transform=Matrix.Translation(Vector((tc.x,tc.y,th.z)))@Matrix.Diagonal((*scale,1))@Matrix.Rotation(0 if sign==1 else math.pi,4,'Z')@Matrix.Translation(Vector((-sc.x,-sc.y,-sh.z)))
 low.data=canonical.copy();low.data.transform(transform);low.name='SM_ResonanceGrip'
 # Map the accepted M4 glove contact into each already-fitted attachment frame.
 ml,mh=m4bounds
 map_point=lambda p:Vector([tl[i]+(p[i]-ml[i])*(th[i]-tl[i])/(mh[i]-ml[i]) for i in range(3)])
 hh=[map_point(p) for p in hv];tree=BVHTree.FromPolygons(hh,hf,all_triangles=True)
 # Rigid contact adjustment only; no local displacement of selected mesh.
 samples=[]
 for v in list(low.data.vertices)[::12]:
  if v.co.z>th.z-.012:continue
  hit=tree.find_nearest(v.co)
  if hit and hit[0] is not None and hit[3]<.005:samples.append(v.co.copy())
 def score(dx,dy):
  total=(dx*dx+dy*dy)*len(samples)*.1
  for v in samples:
   h=tree.find_nearest(v+Vector((dx,dy,0)))
   if h and h[0] is not None:
    signed=(v+Vector((dx,dy,0))-h[0]).dot(h[1]);total+=max(0,.0003-signed)**2+.03*h[3]**2
  return total
 dx,dy=min([(x,y) for x in [-.001,0,.001] for y in [-.001,0,.001]],key=lambda t:score(*t)) if samples else (0,0)
 low.data.transform(Matrix.Translation((dx,dy,0)));moved=0
 # Transfer semantic metal/polymer regions from the previous fitted per-gun mesh.
 from mathutils.kdtree import KDTree
 oldpath=P.parent/'Repaired91871/Game'/family/'ResonanceGrip_Surface_Editable.blend'
 with bpy.data.libraries.load(str(oldpath),link=False) as (src,dst):dst.objects=['SM_ResonanceGrip']
 old=dst.objects[0];kd=KDTree(len(old.data.polygons));labels={}
 for f in old.data.polygons:
  center=sum((old.data.vertices[i].co for i in f.vertices),Vector())/len(f.vertices);kd.insert(center,f.index);labels[f.index]='Polymer' in old.data.materials[f.material_index].name
 kd.balance();low.data.materials.clear()
 for name in ['Resonance_Metal_'+family,'Resonance_Polymer']:
  m=bpy.data.materials.new(name);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.014,.016,.018,1);bs.inputs['Metallic'].default_value=0 if 'Polymer' in name else .8;bs.inputs['Roughness'].default_value=.64 if 'Polymer' in name else .38;low.data.materials.append(m)
 for f in low.data.polygons:
  center=sum((low.data.vertices[i].co for i in f.vertices),Vector())/len(f.vertices);near=kd.find_n(center,5);f.material_index=1 if sum(labels[i] for _,i,_ in near)>=3 else 0
 bpy.data.objects.remove(old,do_unlink=True)
 low.data.uv_layers.new(name='SurfaceUV')
 uv=low.data.uv_layers.new(name='ReceiverCoatUV');tile={'M4':(.12,.05),'AKM':(.12,.025),'QBZ191':(.1,.1)}[family]
 for f in low.data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
  for li in f.loop_indices:
   co=low.data.vertices[low.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/tile[0],co[axes[1]]/tile[1])
 for i in range(len(uv.data)):low.data.uv_layers[0].data[i].uv=uv.data[i].uv
 low.data.uv_layers.active_index=0;low.data.uv_layers[0].active_render=True
 bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
 folder=P/family;folder.mkdir(exist_ok=True)
 bpy.ops.export_scene.fbx(filepath=str(folder/'SM_ResonanceGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)

 for image in bpy.data.images:
  if image.source=='FILE' and not image.packed_file and not Path(bpy.path.abspath(image.filepath)).exists():
   candidate=Path('D:/FPS3D/FPSGAME/SourceAssets/AKMArmSupport20260911/Metal')/Path(image.filepath).name
   if candidate.exists():image.filepath=str(candidate)
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'ResonanceGrip_Surface_Editable.blend'))
 report[family]={'transform':[list(row) for row in transform],'contact_relief_vertices':moved,'rigid_contact_shift_m':[dx,dy,0],'contact_samples':len(samples),'max_relief_m':0,'contact_method':'M4 idle glove; normalized contact transfer for AKM/QBZ; rigid XY shift at most1mm per axis; no local geometry displacement or animation change','target_bounds':[list(tl),list(th)]}
 for ob in obs:bpy.data.objects.remove(ob,do_unlink=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2))
