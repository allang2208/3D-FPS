"""Read current security sleeve/body overlap in the actual native animation poses."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
ROOT=BASE/'V13'
for d in ['Diagnosis','Authoring','Delivery','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V12/Authoring/FacelessSecurity_States_V12.blend'))
rig=bpy.data.objects['root'];scene=bpy.context.scene
rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(0);bpy.context.view_layer.update()
display=bpy.data.objects['Security_OutfitBody'];shirt=bpy.data.objects['Security_Uniform_SewnNeck_V11']
head={n:rig.matrix_world@rig.data.bones[n].head_local for n in ['upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r']}
report={'rig_scale':list(rig.matrix_world.to_scale()),'bones':{n:list(p) for n,p in head.items()},'meshes':{},'poses':{}}
for o in [display,shirt,bpy.data.objects['Security_Cuff_l'],bpy.data.objects['Security_Cuff_r']]:
    p=[o.matrix_world@v.co for v in o.data.vertices]
    report['meshes'][o.name]={'vertices':len(p),'faces':len(o.data.polygons),'matrix':[list(r) for r in o.matrix_world],
      'bounds':[[min(v[k] for v in p),max(v[k] for v in p)] for k in range(3)],
      'modifiers':[(m.name,m.type) for m in o.modifiers]}
points=[display.matrix_world@v.co for v in display.data.vertices]
ids=[];restq={}
for i,p in enumerate(points):
    if abs(p.x)<.30 or p.z<.6:continue
    side='l' if p.x>0 else 'r';e=head['lowerarm_'+side];w=head['hand_'+side];axis=(w-e).normalized();q=(p-w).dot(axis)
    if q<-.016:
        ids.append(i);restq[i]=q
report['covered_forearm_candidates']=len(ids)
def evaluated(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    p=[ev.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear();return p
# The baked Solidify shell is paired outer then inner; exclude inward wall.
outer=len(shirt.data.vertices)//2
shirt.data.calc_loop_triangles();tris=[tuple(t.vertices) for t in shirt.data.loop_triangles if max(t.vertices)<outer]
rest_shirt=[shirt.matrix_world@v.co for v in shirt.data.vertices]
flips=0
for j,tri in enumerate(tris):
    a,b,c=[rest_shirt[i] for i in tri];p=(a+b+c)/3
    if abs(p.x)<.30:continue
    side='l' if p.x>0 else 'r';s=head['upperarm_'+side];e=head['lowerarm_'+side];w=head['hand_'+side]
    centers=[]
    for start,end in [(s,e),(e,w)]:
        t=max(0.,min(1.,(p-start).dot(end-start)/(end-start).length_squared));centers.append(start.lerp(end,t))
    center=min(centers,key=lambda x:(p-x).length_squared)
    if (b-a).cross(c-a).dot(p-center)<0:tris[j]=tuple(reversed(tri));flips+=1
report['sleeve_face_winding_reversed_for_query']=flips
report['outer_vertices']=outer;report['outer_triangles']=len(tris)
with bpy.data.libraries.load(str(BASE/'V06/Motion/FacelessSecurity_MaleMotion_V06.blend'),link=False) as (a,b):
    b.actions=['Security_MaleV06_idle','Security_MaleV06_walk']
actions={'idle':b.actions[0],'walk':b.actions[1]}
with bpy.data.libraries.load(str(BASE/'V10/Motion/FacelessSecurity_Recovery_V10.blend'),link=False) as (a,b):
    b.actions=['Security_MaleV10_attack']
report['attack_actions']=[a.name for a in b.actions]
actions['attack']=b.actions[-1]
for role in ['hit','fall','get_up','prone_get_up','dizzy']:actions[role]=bpy.data.actions['Security_V12_'+role]
for role,act in actions.items():
    rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0]
    lo,hi=act.frame_range
    for fr in sorted(set(round(lo+(hi-lo)*i/8) for i in range(9))):
        scene.frame_set(fr);bpy.context.view_layer.update();skin=evaluated(display);sp=evaluated(shirt)
        tree=BVHTree.FromPolygons(sp,tris,all_triangles=True);outside=[]
        for i in ids:
            h=tree.find_nearest(skin[i]);signed=(skin[i]-h[0]).dot(h[1])
            if signed>.0008:outside.append((signed,i))
        outside.sort(reverse=True)
        row={'exposed_vertices':len(outside),'max_depth_mm':outside[0][0]*1000 if outside else 0,
            'worst':[{'id':i,'depth_mm':v*1000,'rest':list(points[i]),'wrist_q_mm':restq[i]*1000,
                      'posed_skin':list(skin[i]),'cloth_nearest':list(tree.find_nearest(skin[i])[0]),'cloth_normal':list(tree.find_nearest(skin[i])[1]),
                      'weights':{display.vertex_groups[g.group].name:g.weight for g in display.data.vertices[i].groups}} for v,i in outside[:3]]}
        report['poses'][role+'_'+str(fr)]=row
    print('SLEEVE_SOURCE_ROLE',role,max(r['exposed_vertices'] for k,r in report['poses'].items() if k.startswith(role+'_')),flush=True)
(ROOT/'Diagnosis/sleeve_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SLEEVE_SOURCE_SUMMARY',json.dumps({k:v for k,v in report.items() if k!='poses'}),flush=True)
