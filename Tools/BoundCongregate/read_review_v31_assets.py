from pathlib import Path
import json
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/ReviewV31')
bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
cdo=u.get_default_object(bp.generated_class())
result={}
for key in ['visual_mesh','idle_clip','move_clip','turn_left_clip','turn_right_clip','bite_clip','flurry_clip','hit_clip','death_clip']:
    asset=cdo.get_editor_property(key)
    if not asset:
        result[key]=None
        continue
    skeleton=asset.get_editor_property('skeleton')
    result[key]={'asset':asset.get_path_name(),'skeleton':skeleton.get_path_name() if skeleton else None}
    if skeleton:
        result[key]['compatible_skeletons']=[str(s) for s in skeleton.get_editor_property('compatible_skeletons')]
(out/'asset-detail.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('M88_ASSET_DETAIL '+json.dumps(result,ensure_ascii=False))
