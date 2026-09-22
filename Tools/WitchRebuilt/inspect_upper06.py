import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from render_polish_review import setup,ROOT
OUT=ROOT/'Revision06';OUT.mkdir(exist_ok=True)
report={}
for role,times in [('Idle',[0]),('ThrowPoisonBottle',[.4,.75,.95])]:
    s,c,aim=setup(role);rig=next(o for o in s.objects if o.type=='ARMATURE')
    for t in times:
        s.frame_set(round(t*s.render.fps)+1)
        bones={b.name:{'parent':b.parent.name if b.parent else None,'position':list((rig.matrix_world@b.matrix).translation),'local_q':list(b.rotation_quaternion),'location':list(b.location)} for b in rig.pose.bones if any(k in b.name for k in ('upperarm_r','lowerarm_r','hand_r','twist'))}
        report[f'{role}_{t}']=bones
        if t not in (0,.75):continue
        for o in s.objects:
            if o.type=='MESH':o.hide_render=o.name not in ('WitchRebuilt_CompleteBody','WitchRebuilt_Lining')
        target=(rig.matrix_world@rig.pose.bones['lowerarm_r'].matrix).translation
        c.location=target+Vector((-1.3,-1.5,.5));aim(c,target);c.data.ortho_scale=.82
        s.render.resolution_x=900;s.render.resolution_y=750;s.cycles.samples=16
        s.render.filepath=str(OUT/f'before_{role}_arm.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
report['objects']={o.name:{'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'custom_normals':o.data.has_custom_normals,'uv_layers':[x.name for x in o.data.uv_layers],'modifiers':[(x.name,x.type) for x in o.modifiers]} for o in bpy.context.scene.objects if o.type=='MESH'}
(OUT/'source_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['objects']))
