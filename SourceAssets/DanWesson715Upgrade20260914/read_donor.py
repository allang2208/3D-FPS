"""Read the licensed reference motion into hand/arm-space authoring data."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;result={}
for path in sorted((O/'Reference/Converted').glob('*.fbx')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    r=max(rigs,key=lambda o:len(o.data.bones));a=r.animation_data.action
    s=bpy.context.scene;fps=s.render.fps/s.render.fps_base;lo,hi=a.frame_range
    data={'fps':fps,'frames':[lo,hi],'duration':(hi-lo)/fps,'bones':[b.name for b in r.data.bones],'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'rest':{b.name:[list(row) for row in b.matrix_local] for b in r.data.bones},'poses':[]}
    for i in range(round(data['duration']*60)+1):
        f=min(hi,lo+i*fps/60);s.frame_set(int(f),subframe=f%1)
        data['poses'].append({b.name:[list(row) for row in b.matrix] for b in r.pose.bones})
    result[path.stem]=data
    print(path.stem,'duration',data['duration'],'fps',fps,'bones',data['bones'],flush=True)
(O/'Reference/donor-poses.json').write_text(json.dumps(result),encoding='utf-8')
print('DW715_REFERENCE_SAMPLED',flush=True)
