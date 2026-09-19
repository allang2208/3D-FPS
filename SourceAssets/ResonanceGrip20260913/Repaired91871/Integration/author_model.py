import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
# Keep the accepted hand pose; use its glove surface to author local relief only.
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend')
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['A_M4_Foregrip_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
hand=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in hand.vertex_groups}
ids={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_l') and any(groups[g.group].startswith(x) for x in ['hand','index','middle','ring','pinky','thumb']))>.5}
ev=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();me.calc_loop_triangles()
pose_to_bind=r.matrix_world@r.data.bones['WPN_root'].matrix_local@(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()
hv=[pose_to_bind@ev.matrix_world@v.co for v in me.vertices];hf=[tuple(t.vertices) for t in me.loop_triangles if all(i in ids for i in t.vertices)];ev.to_mesh_clear()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P.parent/'RepairedMaster.glb'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.data.transform(high.matrix_world);high.matrix_world=Matrix.Identity(4);high.data.transform(Matrix.Rotation(math.pi/2 if high.dimensions.x>high.dimensions.y else 0,4,'Z'));high.name='Resonance_Selected91871_Master'
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
# Retain repaired master topology; defer reduction until a dedicated retopology pass.
mat=low.data.materials[0];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');base=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links));packed=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image!=base)
for key,img in [('BaseColor',base),('MetalRough',packed)]:img.filepath_raw=str(P/('T_Resonance_'+key+'.png'));img.file_format='PNG';img.save()
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
 moved=0
 for v in low.data.vertices:
  if v.co.z>th.z-.012:continue
  hit=tree.find_nearest(v.co)
  if hit and hit[0] is not None:
   p,n,_,dist=hit;signed=(v.co-p).dot(n)
   if dist<.004 and signed<.0007:
    v.co+=n*min(.003,.0007-signed);moved+=1
 uv=low.data.uv_layers.new(name='ReceiverCoatUV');tile={'M4':(.12,.05),'AKM':(.12,.025),'QBZ191':(.1,.1)}[family]
 for f in low.data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
  for li in f.loop_indices:
   co=low.data.vertices[low.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/tile[0],co[axes[1]]/tile[1])
 low.data.uv_layers.active_index=0;low.data.uv_layers[0].active_render=True
 bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
 folder=P/family;folder.mkdir(exist_ok=True)
 bpy.ops.export_scene.fbx(filepath=str(folder/'SM_ResonanceGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 
 for image in bpy.data.images:
  if image.source=='FILE' and not image.packed_file and not Path(bpy.path.abspath(image.filepath)).exists():
   candidate=Path('D:/FPS3D/FPSGAME/SourceAssets/AKMArmSupport20260911/Metal')/Path(image.filepath).name
   if candidate.exists():image.filepath=str(candidate)
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'ResonanceGrip_Editable.blend'))
 report[family]={'transform':[list(row) for row in transform],'contact_relief_vertices':moved,'max_relief_m':.003,'contact_method':'M4 accepted idle glove; normalized transfer to existing fitted AKM/QBZ attachment frames; no animation change','target_bounds':[list(tl),list(th)]}
 for ob in obs:bpy.data.objects.remove(ob,do_unlink=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2))

