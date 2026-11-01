import unreal as u, json, gzip, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
Q=u.GeometryScript_MeshQueries; G=u.GeometryScript_AssetUtils; L=u.GeometryScript_List
HOSTS={
 'M24':'/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9',
 'SVD':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock',
 'SVCH':'/Game/Weapons/SVCH/Replacement20261018/RealSights20261019/SK_SVCH_RealFoldingSights'}
def xyz(v):return [v.x,v.y,v.z]
def matrix(t):
 p=xyz(t.transform_location(u.Vector()))
 cols=[xyz(t.transform_location(v)) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]
 return [[cols[c][r]-p[r] for c in range(3)]+[p[r]] for r in range(3)]+[[0,0,0,1]]
def read(path,static=False):
 asset=u.load_asset(path)
 if not asset:raise RuntimeError('Missing '+path)
 fn=G.copy_mesh_from_static_mesh if static else G.copy_mesh_from_skeletal_mesh
 lod=u.GeometryScriptMeshReadLOD()
 if static:lod.lod_type=u.GeometryScriptLODType.RENDER_DATA
 dm,status=fn(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),lod)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+path)
 _,vs,_=Q.get_all_vertex_positions(dm,False)
 _,ts,_=Q.get_all_triangle_indices(dm,False)
 _,ms,valid=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
 mats=asset.static_materials if static else asset.materials
 result={'path':path,'positions':[xyz(v) for v in L.convert_vector_list_to_array(vs)],
  'triangles':[[int(x) for x in xyz(t)] for t in L.convert_triangle_list_to_array(ts)],
  'material_ids':list(L.convert_index_list_to_array(ms)),
  'materials':[{'slot':str(m.material_slot_name),'asset':m.material_interface.get_path_name() if m.material_interface else None} for m in mats]}
 if not static:
  _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
  result['bones']={str(b.name):{'parent':b.parent_index,'world':matrix(b.world_transform)} for b in bones if str(b.name).startswith('WPN')}
 else:
  result['lod_count']=asset.get_num_lods()
 f=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
 result['sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
 return result
report={}
for key,path in HOSTS.items():
 report[key]={'host':read(path),'stock':read('/Game/Weapons/SkeletonSniperStock20261031/Meshes/SM_SniperSkeleton_'+key,True)}
 print('STOCK_READ',key,[(x,len(report[key][x]['triangles'])) for x in ('host','stock')],flush=True)
with gzip.open(O/'saved_geometry.json.gz','wt',encoding='utf8') as f:json.dump(report,f,separators=(',',':'))
(O/'read_receipt.json').write_text(json.dumps({k:{n:{x:v for x,v in a.items() if x not in ('positions','triangles','material_ids')} for n,a in r.items()} for k,r in report.items()},indent=2))
print('STOCK_REVIEW_READ_COMPLETE',flush=True)
