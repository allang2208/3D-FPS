"""Replace polar joins with sewn boundary loops; retain the horizontal stock."""
from pathlib import Path
import sys,json,math
import bpy,bmesh,numpy as np
from mathutils import Matrix
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from joint_geometry import ATTR,receiver_only,cut_ring,restore,transition
from native_front import restore_front
bpy.ops.wm.read_factory_settings(use_empty=True)
CUT=-.941;FRONT=0.;BACK=-.025;SCALE=.3185991175/1.90327501
ROT=np.array([[0,1,0],[-1,0,0],[0,0,1]])
ORIGIN=np.array([CUT,.00039667,.17187572]);SEAT=np.array([.000055,BACK,.0917])
bpy.ops.import_scene.gltf(filepath=str(O.parent/'M24Meshy1105135808Replacement/Input/Meshy_AI_Carbon_Stock_1105135808_texture.glb'))
template=next(o for o in bpy.context.scene.objects if o.type=='MESH');template.data.materials[0].name='CS_Meshy'
br=cut_ring(template,0,CUT)
metal_faces=[p.index for p in template.data.polygons if sum(template.data.vertices[v].co.x for v in p.vertices)/len(p.vertices)<-.8448]
me=template.data;ps=np.empty((len(me.vertices),3),np.float32);me.vertices.foreach_get('co',ps.ravel());ps=(ps-ORIGIN)@ROT.T*SCALE+SEAT;me.vertices.foreach_set('co',ps.astype(np.float32).ravel())
ns=np.empty((len(me.loops),3),np.float32);me.attributes[ATTR].data.foreach_get('vector',ns.ravel());me.attributes[ATTR].data.foreach_set('vector',(ns@ROT.T).astype(np.float32).ravel());me.update()
br['point']=(br['point']-ORIGIN)@ROT.T*SCALE+SEAT;br['edge_normals']=br['edge_normals']@ROT.T
records={}
for kind in ('Native','Advanced'):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(kind+'.fbx')),use_custom_normals=True)
    rec=next(o for o in set(bpy.data.objects)-before if o.type=='MESH');rec.data.transform(rec.matrix_world);rec.matrix_world=Matrix.Identity(4)
    mi=next(i for i,m in enumerate(rec.data.materials) if 'MI_M24_metal_' in m.name)
    receiver_only(rec,mi)
    mat=bpy.data.materials.get('CS_Receiver') or bpy.data.materials.new('CS_Receiver');rec.data.materials.clear();rec.data.materials.append(mat)
    extra=[];front_info={}
    if kind=='Native':extra,front_info=restore_front(rec,mat)
    rr=cut_ring(rec,1,FRONT)
    body=template.copy();body.data=template.data.copy();bpy.context.collection.objects.link(body);body.data.materials.append(mat)
    for i in metal_faces:body.data.polygons[i].material_index=1
    neck=transition(rr,br,kind+' sewn transition',mat)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rec,body,neck]+extra:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=rec;bpy.ops.object.join();rec.name='SM_M24_CarbonSpine_'+kind
    bm=bmesh.new();bm.from_mesh(rec.data)
    for y in ([FRONT,BACK,.050,.100] if kind=='Native' else [FRONT,BACK]):
        bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co.y-y)<2e-7],dist=3e-7)
    bm.to_mesh(rec.data);bm.free();rec.data.update();restore(rec)
    rec.data.uv_layers.active_index=0;rec.data.uv_layers[0].active_render=True
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(rec.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',use_tspace=True,add_leaf_bones=False,bake_anim=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    records[kind]={'receiver_source':'current installed ReceiverStock_'+kind,'pitch_deg':0,'stock_body_deformed':False,'nose_center_m':SEAT.tolist(),'receiver_cut_y_m':FRONT,'transition_mm':25,'receiver_boundary_vertices':len(rr['phase']),'stock_boundary_vertices':len(br['phase']),'ordering':'actual edge graph, top-centre anchor, normalized perimeter','connections':'welded original boundary vertices, zipper strips','primary_uv':'UVMap','original_carbon_textures_retained':True}
    records[kind]['front_repair']=front_info
    if kind=='Advanced':rec.hide_set(True);rec.hide_render=True
bpy.data.objects.remove(template,do_unlink=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_HorizontalJointClean.blend'),compress=True)
(O/'stock_construction.json').write_text(json.dumps(records,indent=2));print('M24_CLEAN_JOINT_AUTHORED',records)
