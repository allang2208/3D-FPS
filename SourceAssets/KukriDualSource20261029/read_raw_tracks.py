"""Read arm rotation values directly from FBX, independent of Blender import."""
import json
from pathlib import Path
from io_scene_fbx import parse_fbx
OUT=Path(__file__).resolve().parent
report={}
for path in sorted((OUT/'Original/Animations').glob('*Attack*.fbx')):
    tree,_=parse_fbx.parse(str(path))
    objs=next(e for e in tree.elems if e.id==b'Objects')
    byid={e.props[0]:e for e in objs.elems if e.props}
    links=[e.props for e in next(e for e in tree.elems if e.id==b'Connections').elems]
    rows={}
    for mid,model in byid.items():
        if model.id!=b'Model':continue
        name=model.props[1].split(b'\x00')[0].decode()
        if name not in ['pelvis','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']:continue
        nodes=[p[1] for p in links if len(p)>3 and p[2]==mid and p[3]==b'Lcl Rotation']
        values={}
        for node in nodes:
            for p in links:
                if len(p)>3 and p[2]==node and p[1] in byid and byid[p[1]].id==b'AnimationCurve':
                    curve=byid[p[1]]
                    data=next(e.props[0] for e in curve.elems if e.id==b'KeyValueFloat')
                    values[p[3].decode()]={'keys':len(data),'minimum':min(data),'maximum':max(data)}
        rows[name]=values
    report[path.name]=rows
(OUT/'raw-arm-evidence.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
