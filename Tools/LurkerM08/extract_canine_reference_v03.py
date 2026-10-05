"""Read local CC0 canine animation controls for M08 offline authoring. No render."""
import bpy, json, hashlib
from pathlib import Path
PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/Monsters/LurkerM08/CanineRigV03_20261004'
OUT.mkdir(parents=True,exist_ok=True)
SRC=PROJECT/'SourceAssets/InfectedDogMeshy20260924/GodotRunFitV2/Source/wolf_quaternius.gltf'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=60
bpy.ops.import_scene.gltf(filepath=str(SRC))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
def row(b,rest=False):
    m=rig.matrix_world@(b.matrix_local if rest else b.matrix)
    return {'matrix':[list(v) for v in m], 'head':list(rig.matrix_world@(b.head_local if rest else b.head)),
            'tail':list(rig.matrix_world@(b.tail_local if rest else b.tail))}
data={'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
      'license':'CC0-1.0','rest':{b.name:row(b,True) for b in rig.data.bones},'actions':{}}
for a in bpy.data.actions:
    rig.animation_data.action=a
    if hasattr(rig.animation_data,'action_slot'):rig.animation_data.action_slot=a.slots[0]
    start,end=a.frame_range
    duration=(end-start)/60
    count=max(2,round(duration*120))
    samples=[]
    for i in range(count+1):
        f=start+(end-start)*i/count
        bpy.context.scene.frame_set(int(f),subframe=f-int(f))
        samples.append({b.name:row(b) for b in rig.pose.bones})
    data['actions'][a.name]={'seconds':duration,'samples':samples}
(OUT/'canine_source.json').write_text(json.dumps(data),encoding='utf-8')
print('CANINE_SOURCE',[(a,d['seconds']) for a,d in data['actions'].items()],flush=True)
