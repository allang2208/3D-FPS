"""Use the shared continuous-death authoring algorithm for this mesh only."""
from pathlib import Path
import importlib.util, sys
root=Path('D:/FPS3D/FPSGAME')
spec=importlib.util.spec_from_file_location('bound_corpse_author',root/'Tools/MonsterSoftCorpse/author_cages.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
v3='--rig-v3' in sys.argv
v2='--tentacle-v2' in sys.argv
whip='--tentacle-v3' in sys.argv
v4='--tentacle-v4' in sys.argv
v6='--dynamics-v6' in sys.argv
v7='--cloth-v7' in sys.argv
v8='--cloth-v8' in sys.argv
v9='--cloth-v9' in sys.argv
v10='--full-whip-v10' in sys.argv
v12='--surface-fit-v12' in sys.argv
v14='--garment-v14' in sys.argv
v18='--garment-v18' in sys.argv
v19='--garment-v19' in sys.argv
module.ROOT=root/('SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4/SoftCorpse' if v4 else 'SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV3/SoftCorpse' if whip else 'SourceAssets/BoundCongregateMeshy20261006/TentacleRepairV2/SoftCorpse' if v2 else 'SourceAssets/BoundCongregateMeshy20261006/RigRepairV3/SoftCorpse' if v3 else 'SourceAssets/BoundCongregateMeshy20261006/SoftCorpse')
if v6:module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/TentacleDynamicsV6/SoftCorpse'
if v7:module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/ClothContactV7/SoftCorpse'
if v8:module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/ClothMotionV8/SoftCorpse'
if v9:module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/ClothContactV9/SoftCorpse'
if v10:module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/FullWhipV10/SoftCorpse'
if v19:
    module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/GarmentRebuildV19/SoftCorpse'
    module.author(dict(key='BoundCongregate',source='/Game/Monsters/BoundCongregate/GarmentRebuildV19/SK_BoundCongregate_GarmentRebuildV19'))
    sys.exit(0)
if v18:
    module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV18/SoftCorpse'
    module.author(dict(key='BoundCongregate',source='/Game/Monsters/BoundCongregate/GarmentDrapeV18/SK_BoundCongregate_GarmentDrapeV18'))
    sys.exit(0)
if v14:
    module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/GarmentContinuityV14/SoftCorpse'
    module.author(dict(key='BoundCongregate',source='/Game/Monsters/BoundCongregate/GarmentContinuityV14/SK_BoundCongregate_SurfaceFitV12_GarmentV14'))
    sys.exit(0)
if v12:
    module.ROOT=root/'SourceAssets/BoundCongregateMeshy20261006/SurfaceFitV12/SoftCorpse'
    module.author(dict(key='BoundCongregate',source='/Game/Monsters/BoundCongregate/SurfaceFitV12/SK_BoundCongregate_SurfaceFitV12'))
    sys.exit(0)
module.author(dict(key='BoundCongregate',source='/Game/Monsters/BoundCongregate/'+('FullWhipV10/SK_BoundCongregate_FullWhipV10' if v10 else 'ClothV9/SK_BoundCongregate_ClothV9' if v9 else 'ClothV8/SK_BoundCongregate_ClothV8' if v8 else 'ClothV7/SK_BoundCongregate_ClothV7' if v7 else 'DynamicsV6/SK_BoundCongregate_DynamicsV6' if v6 else 'TentacleV4/SK_BoundCongregate_TentacleV4' if v4 else 'TentacleV3/SK_BoundCongregate_TentacleV3' if whip else 'TentacleV2/SK_BoundCongregate_TentacleV2' if v2 else 'RigV3/SK_BoundCongregate_RigV3' if v3 else 'SK_BoundCongregate')))
