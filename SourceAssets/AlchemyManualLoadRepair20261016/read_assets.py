"""Read only the manual dependencies and leaf initialization inputs."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualLoadRepair20261016')
BASE='/Game/Building/PotionWorkbench20261015/'
paths=[
 'ManualV10/Meshes/SM_AlchemyManualBinding',
 'ManualV5/Meshes/SM_AlchemyManualClosed',
 'ManualV6/Meshes/SM_AlchemyManualBookmarks',
 'ManualV8/Materials/M_ManualRibbonInteractive',
 'ManualV8/Materials/M_ManualClaspInteractive',
 'ManualV9/Meshes/SK_BookLeafTemplate',
 'ManualV9/Materials/M_BookLeafPaper',
 'ManualV9/Materials/M_BookLeafEdge',
]
report={}
for relative in paths:
    obj=u.load_asset(BASE+relative)
    report[relative]=dict(loaded=bool(obj),type=obj.get_class().get_name() if obj else None)
    if isinstance(obj,u.SkeletalMesh):
        report[relative]['materials']=[dict(slot=str(s.get_editor_property('material_slot_name')),material=s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None) for s in obj.materials]
        component=u.PoseableMeshComponent()
        component.set_skinned_asset_and_update(obj)
        report[relative]['bones']=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
(ROOT/'asset-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('MANUAL_LOAD_DIAGNOSIS '+json.dumps(report))
