import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'V02/Motion/FacelessSecurity_MaleMotion_V02.blend'))
rig=bpy.data.objects['root'];report={}
for tr in rig.animation_data.nla_tracks:tr.mute=True
for role in ['idle','attack']:
    act=bpy.data.actions['Security_MaleV02_'+role];rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0]
    bpy.context.scene.frame_set(1 if role=='idle' else 37);dg=bpy.context.evaluated_depsgraph_get()
    trees=[]
    for name in ['Security_Shirt_Continuous','Security_Trousers_Continuous','Security_Cuff_l','Security_Cuff_r']:
        o=bpy.data.objects[name].evaluated_get(dg);me=o.to_mesh();me.calc_loop_triangles()
        trees.append((name,BVHTree.FromPolygons([o.matrix_world@v.co for v in me.vertices],[tuple(t.vertices) for t in me.loop_triangles],all_triangles=True)))
        o.to_mesh_clear()
    o=bpy.data.objects['Security_OutfitBody'];ev=o.evaluated_get(dg);me=ev.to_mesh();groups={g.index:g.name for g in o.vertex_groups}
    row={}
    for side in ['l','r']:
        ids=[v.index for v in o.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_'+side) and groups[g.group].startswith(('hand','thumb','index','middle','ring','pinky')))>.8]
        count={n:0 for n,_ in trees};sample_ids=ids[::7]
        for i in sample_ids:
            p=ev.matrix_world@me.vertices[i].co
            for name,tree in trees:
                # The front/back and left/right rays detect a surface enclosing
                # the hand, including the open cuff cavity.
                hits=0
                for d in [Vector((0,1,0)),Vector((0,-1,0)),Vector((1,0,0)),Vector((-1,0,0))]:
                    if tree.ray_cast(p,d,.10)[0] is not None:hits+=1
                if hits>=3:count[name]+=1
        row[side]={'sampled':len(sample_ids),'enclosed':count}
    report[role]=row;ev.to_mesh_clear()
(ROOT/'V03/Diagnosis/hand_occlusion_before.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
