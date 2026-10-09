"""Requested sleeve diagnosis only: same-side shell containment, native actions."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');ROOT=BASE/'V13'
report={'scope':'displayed skin under sleeve/cuff; nine samples per active native action', 'versions':{}}
for version in ['V11','V13']:
    bpy.ops.wm.open_mainfile(filepath=str(BASE/version/('Authoring/FacelessSecurity_'+version+'.blend')))
    scene=bpy.context.scene;rig=bpy.data.objects['root'];rig.animation_data_clear();rig.animation_data_create()
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    scene.frame_set(0);bpy.context.view_layer.update()
    display=bpy.data.objects['Security_OutfitBody'];shirt=bpy.data.objects['Security_Uniform_SewnNeck_V11']
    head={n:rig.matrix_world@rig.data.bones[n].head_local for n in ['upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r']}
    def arm(p):
        side='l' if p.x>0 else 'r';e=head['lowerarm_'+side];w=head['hand_'+side]
        return side,(p-w).dot((w-e).normalized())
    skin_rest=[display.matrix_world@v.co for v in display.data.vertices]
    ids={s:[] for s in ['l','r']}
    for i,p in enumerate(skin_rest):
        side,q=arm(p)
        if abs(p.x)>.29 and p.z>.6 and q<-.006:ids[side].append(i)
    objs=[shirt]+[bpy.data.objects['Security_Cuff_'+s] for s in ['l','r']]
    shells={}
    for o in objs:
        p=[o.matrix_world@v.co for v in o.data.vertices];count=len(p)//2;o.data.calc_loop_triangles();tri={s:[] for s in ['l','r']}
        for t in o.data.loop_triangles:
            if max(t.vertices)>=count:continue
            indices=tuple(t.vertices);a,b,c=[p[i] for i in indices];center=(a+b+c)/3
            if abs(center.x)<.29:continue
            side,q=arm(center);s=head['upperarm_'+side];e=head['lowerarm_'+side];w=head['hand_'+side]
            centers=[]
            for start,end in [(s,e),(e,w)]:
                alpha=max(0.,min(1.,(center-start).dot(end-start)/(end-start).length_squared));centers.append(start.lerp(end,alpha))
            origin=min(centers,key=lambda x:(center-x).length_squared)
            if (b-a).cross(c-a).dot(center-origin)<0:indices=tuple(reversed(indices))
            tri[side].append(indices)
        shells[o.name]=tri
    def eval_points(o):
        ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=[ev.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear();return p
    actions={}
    for role,file,name in [('idle','V06/Motion/FacelessSecurity_MaleMotion_V06.blend','Security_MaleV06_idle'),
                           ('walk','V06/Motion/FacelessSecurity_MaleMotion_V06.blend','Security_MaleV06_walk'),
                           ('attack','V10/Motion/FacelessSecurity_Recovery_V10.blend','Security_MaleV10_attack')]:
        with bpy.data.libraries.load(str(BASE/file),link=False) as (a,b):b.actions=[name]
        actions[role]=b.actions[0]
    with bpy.data.libraries.load(str(BASE/'V12/Authoring/FacelessSecurity_States_V12.blend'),link=False) as (a,b):
        b.actions=['Security_V12_'+r for r in ['hit','fall','get_up','prone_get_up','dizzy']]
    actions.update(zip(['hit','fall','get_up','prone_get_up','dizzy'],b.actions))
    results={}
    for role,act in actions.items():
        rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0];lo,hi=act.frame_range
        for frame in sorted(set(round(lo+(hi-lo)*i/8) for i in range(9))):
            scene.frame_set(frame);bpy.context.view_layer.update();skin=eval_points(display)
            trees={s:[] for s in ['l','r']}
            for o in objs:
                p=eval_points(o)
                for s in trees:
                    if shells[o.name][s]:trees[s].append((o.name,BVHTree.FromPolygons(p,shells[o.name][s],all_triangles=True)))
            exposed=[];seam_outside=0
            for s in ids:
                for i in ids[s]:
                    signed=[]
                    q=arm(skin_rest[i])[1]
                    for name,tree in trees[s]:
                        if 'Cuff' in name and q<-.066:continue
                        h=tree.find_nearest(skin[i]);signed.append((skin[i]-h[0]).dot(h[1]))
                    depth=min(signed)
                    if depth>.0008:exposed.append((depth,i))
            exposed.sort(reverse=True)
            results[role+'_'+str(frame)]={'outside_vertices':len(exposed),'max_outside_mm':1000*exposed[0][0] if exposed else 0,
                'worst':[{'id':i,'mm':d*1000,'wrist_q_mm':arm(skin_rest[i])[1]*1000,'rest':list(skin_rest[i]),
                          'posed':list(skin[i]),'weights':{display.vertex_groups[g.group].name:g.weight for g in display.data.vertices[i].groups},
                          'hand_basis':list(rig.pose.bones['hand_'+arm(skin_rest[i])[0]].rotation_quaternion)} for d,i in exposed[:3]]}
    report['versions'][version]={'under_sleeve_vertices':sum(map(len,ids.values())),'sampled_poses':len(results),'poses':results}
    print('SLEEVE_CONTAINMENT',version,json.dumps({r:max(v['outside_vertices'] for k,v in results.items() if k.startswith(r+'_')) for r in actions}),flush=True)
(ROOT/'Diagnosis/sleeve_overlap.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
