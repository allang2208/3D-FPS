import sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import *
R=P/'SourceAssets/GarmentFoundation20260929';receipts={}
for name,row in read(R/'edits.json').items():
 source=u.load_asset(row['source']);dm,data=source_snapshot(source);_,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
 for edit in row['weights']:
  _,ok=B.set_vertex_bone_weights(dm,edit['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in edit['weights'].items()])
  if not ok:raise RuntimeError('Weights')
 for i in row['delete_triangles']:
  _,ok=u.GeometryScript_MeshEdits.delete_triangle_from_mesh(dm,i,True)
  if not ok:raise RuntimeError('Closure removal')
 receipt=save_candidate(dm,source,'/Game/Characters/ModularOutfit20260924/GarmentFoundation20260929/EdgeLockedV3/SK_M4_'+name.removeprefix('ue_'),R/name)
 receipts[name]=receipt;write(R/'saved.json',receipts)
 print('FOUNDATION_SAVED',name,flush=True)
