import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
def scene_info():
    out={'fps':bpy.context.scene.render.fps,'objects':[],'actions':[]}
    for o in bpy.context.scene.objects:
        info={'name':o.name,'type':o.type,'matrix':[list(x) for x in o.matrix_world]}
        if o.type=='MESH':
            points=[o.matrix_world@v.co for v in o.data.vertices]
            info.update(vertices=len(points),faces=len(o.data.polygons),lo=[min(v[i] for v in points) for i in range(3)],hi=[max(v[i] for v in points) for i in range(3)],materials=[m.name for m in o.data.materials if m])
        if o.type=='ARMATURE':
            info['bones']={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in o.data.bones}
        out['objects'].append(info)
    for a in bpy.data.actions:out['actions'].append({'name':a.name,'frames':list(a.frame_range)})
    return out
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Reference/Arms.fbx'))
out={'donor':scene_info()}
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
out['donor']['poses']={}
for a in bpy.data.actions:
    rig.animation_data_create();rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    samples=[]
    for f in [a.frame_range[0],(a.frame_range[0]+a.frame_range[1])/2,a.frame_range[1]]:
        bpy.context.scene.frame_set(int(f),subframe=f%1)
        samples.append({'frame':f,'bones':{b.name:[list(row) for row in rig.matrix_world@b.matrix] for b in rig.pose.bones if any(s in b.name.lower() for s in ['hand','weapon','sword','forearm','upperarm'])}})
    out['donor']['poses'][a.name]=samples
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((P/'Original').rglob('*.fbx'))))
out['sword']=scene_info()
source=P.parent/'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
out['target']=scene_info();out['target']['source']=str(source)
(P/'source_geometry.json').write_text(json.dumps(out,indent=2))
print('SOURCE_DATA_WRITTEN',flush=True)
