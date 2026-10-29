"""Capture the unmodified source skeleton and FBX curve evidence."""
import bpy, json
from pathlib import Path
OUT=Path(__file__).resolve().parent
for stem in ('DualSword_Attack_Slash_01','DualSword_Attack_Cross_Slash'):
    bpy.ops.wm.open_mainfile(filepath=str(OUT/(stem+'.blend')))
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    action=arm.animation_data.action
    first,last=action.frame_range
    bones=list(arm.data.bones);names=[b.name for b in bones]
    parents=[names.index(b.parent.name) if b.parent else -1 for b in bones]
    fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    frames=[];basis=[]
    for f in range(int(first),int(last)+1):
        bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
        frames.append([list(arm.matrix_world@arm.pose.bones[n].head) for n in names])
        basis.append([list(arm.pose.bones[n].matrix_basis.to_quaternion()) for n in names])
    payload=dict(names=names,parents=parents,fps=fps,first=first,last=last,frames=frames,basis=basis,
        reference=[list(arm.matrix_world@b.head_local) for b in bones])
    (OUT/(stem+'-sample.json')).write_text(json.dumps(payload))
    print(stem,'object',arm.matrix_world,'range',first,last,'fps',fps)

from io_scene_fbx import parse_fbx
def scalar(x):
    if isinstance(x,bytes):return x.decode('utf-8',errors='replace')
    if hasattr(x,'tolist'):return x.tolist()
    return x
raw={}
for path in sorted((OUT/'Original/Animations').glob('*Attack*.fbx')):
    tree,version=parse_fbx.parse(str(path))
    objects=next(e for e in tree.elems if e.id==b'Objects')
    rows=[]
    for e in objects.elems:
        if e.id in (b'AnimationStack',b'AnimationCurve',b'AnimationCurveNode'):
            props=[scalar(p) for p in e.props]
            sub={scalar(c.id):[scalar(v) for v in c.props] for c in e.elems}
            rows.append(dict(type=scalar(e.id),props=props,data=sub))
    raw[path.name]=rows
(OUT/'raw-fbx-curves.json').write_text(json.dumps(raw))
