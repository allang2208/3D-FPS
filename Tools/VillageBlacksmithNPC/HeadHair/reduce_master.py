"""Retain the full Meshy textured master and create a game surface using UV-aware edge collapse."""
from pathlib import Path
import bpy
import json
import numpy as np
BASE=Path(__file__).resolve().parents[3]/'SourceAssets/VillageBlacksmithNPC20261118'
OUT=BASE/'HeadHair'
SOURCE=BASE/'Meshy/CombinedR1/head.glb'
if not SOURCE.exists():SOURCE=BASE/'Meshy/head.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE),import_pack_images=False,merge_vertices=False)
obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
if len(obs)!=1:raise ValueError('Unexpected Meshy master mesh count')
ob=obs[0]
source_tri=len(ob.data.polygons)
budget=115000
if source_tri>budget:
    mod=ob.modifiers.new('Meshy game LOD0 surface','DECIMATE')
    mod.ratio=budget/source_tri;mod.use_collapse_triangulate=True
    bpy.context.view_layer.update()
    graph_obj=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
else:graph_obj=ob
me=graph_obj.to_mesh()
me.calc_loop_triangles()
if source_tri>budget*2 and len(me.loop_triangles)>budget*1.5:raise RuntimeError('The source mesh was not reduced to the game budget.')
p=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',p);p=p.reshape(-1,3)
matrix=np.array(ob.matrix_world)
p=p@matrix[:3,:3].T+matrix[:3,3];p[:,1]*=-1
vind=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',vind)
uv=np.empty(len(me.loops)*2,np.float32);me.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,2);uv[:,1]=1-uv[:,1]
norm=np.empty(len(me.corner_normals)*3,np.float32);me.corner_normals.foreach_get('vector',norm);norm=norm.reshape(-1,3)@np.linalg.inv(matrix[:3,:3]);norm[:,1]*=-1
loops=np.empty(len(me.loop_triangles)*3,np.int32);me.loop_triangles.foreach_get('loops',loops)
corners=np.column_stack((vind,np.round(uv,7),np.round(norm,6)))
uniq,back=np.unique(corners,axis=0,return_inverse=True);tri=back[loops].reshape(-1,3)
np.savez_compressed(OUT/'game_surface.npz',p=p[uniq[:,0].astype(int)],n=uniq[:,3:6],uv=uniq[:,1:3],tri=tri)
(OUT/'reduction.json').write_text(json.dumps({'source':SOURCE.relative_to(BASE).as_posix(),'master_triangles':source_tri,'game_triangles_before_neck_fit':len(tri),'method':'Blender collapse preserving per-corner UV, normals and all source texture maps'},indent=2))
print('SMITH_REDUCED_MASTER',source_tri,len(tri),flush=True)
