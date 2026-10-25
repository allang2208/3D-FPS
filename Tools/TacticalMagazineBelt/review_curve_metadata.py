"""Read curve names for isolated uncooked peers; never save production packages."""
import json,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TacticalMagazineBelt20261024/Review20261024'
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
paths=set()
def gather(value):
    if isinstance(value,str) and value.startswith('/Game/'):paths.add(value)
    elif isinstance(value,dict):
        for v in value.values():gather(v)
    elif isinstance(value,list):
        for v in value:gather(v)
gather(cfg['clips']);gather(cfg['body_variants']['kaitlin']['clips'])
rows={};count=0
for path in sorted(paths):
    clip=u.load_asset(path)
    if not isinstance(clip,u.AnimSequence):continue
    skeleton=clip.get_editor_property('skeleton')
    if skeleton:
        names=[str(x) for x in u.AnimationLibrary.get_animation_curve_names(clip,u.RawCurveTrackTypes.RCT_FLOAT)]
        rows.setdefault(skeleton.get_path_name(),set()).update(names)
    count+=1
    if count%30==0:print('BELT_REVIEW_CURVES_READ',count,flush=True)
data={k:sorted(v) for k,v in rows.items()}
(R/'uncooked-curve-metadata.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('BELT_REVIEW_CURVE_METADATA',count,'clips',len(data),'skeletons',sum(len(v) for v in data.values()),'names; no packages saved',flush=True)
