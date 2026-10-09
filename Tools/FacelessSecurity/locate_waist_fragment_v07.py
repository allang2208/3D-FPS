"""Locate the reported floating piece in the current V06 geometry and poses."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');OUT=BASE/'V07'
(OUT/'Logs').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V06/Authoring/FacelessSecurity_V06.blend'))
rig=bpy.data.objects['root'];scene=bpy.context.scene;rig.animation_data_create();rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
objects=[o for o in scene.objects if o.type=='MESH' and o.name!='Security_CompleteBody']
components={};report={'mesh_components':{},'poses':{}}
for o in objects:
    parent=list(range(len(o.data.vertices)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for edge in o.data.edges:
        a,b=map(root,edge.vertices)
        if a!=b:parent[a]=b
    groups={}
    for v in o.data.vertices:groups.setdefault(root(v.index),[]).append(v.index)
    groups=sorted(groups.values(),key=len,reverse=True);lookup={v:i for i,ids in enumerate(groups) for v in ids}
    polys=[[] for _ in groups]
    o.data.calc_loop_triangles()
    for tri in o.data.loop_triangles:polys[lookup[tri.vertices[0]]].append(tuple(tri.vertices))
    components[o.name]=(groups,polys)
    rows=[]
    for i,ids in enumerate(groups):
        p=np.array([o.matrix_world@o.data.vertices[j].co for j in ids]);weights={}
        for j in ids:
            for g in o.data.vertices[j].groups:
                n=o.vertex_groups[g.group].name;weights[n]=weights.get(n,0)+g.weight/len(ids)
        rows.append({'id':i,'vertices':len(ids),'triangles':len(polys[i]),'vertex_indices':ids if len(ids)<1000 else [],
            'bound_center':p.mean(0).tolist(),'bound_size':(p.max(0)-p.min(0)).tolist(),
            'weights':{n:w for n,w in weights.items() if w>.001}})
    report['mesh_components'][o.name]=rows
with bpy.data.libraries.load(str(BASE/'V06/Motion/FacelessSecurity_MaleMotion_V06.blend'),link=False) as (src,dst):
    dst.actions=['Security_MaleV06_idle','Security_MaleV06_attack']
actions=dict(zip(['idle','attack'],dst.actions))
for role,fr in [('idle',1),('attack',40),('attack',80)]:
    action=actions[role];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(fr)
    dg=bpy.context.evaluated_depsgraph_get();points={};vertices=[];faces=[]
    for o in objects:
        ev=o.evaluated_get(dg);me=ev.to_mesh();p=[ev.matrix_world@v.co for v in me.vertices];points[o.name]=p;ev.to_mesh_clear()
        if not o.name.startswith(('Security_Shirt_Continuous','Security_Trousers_Continuous','Security_Cuff_','Security_Boot_','Security_BootSole_')):continue
        groups,polys=components[o.name];start=len(vertices);vertices.extend(p)
        for i,ids in enumerate(groups):
            if len(ids)>=max(100,len(groups[0])*.02):faces.extend([tuple(start+j for j in tri) for tri in polys[i]])
    surface=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
    pelvis=(rig.matrix_world@rig.pose.bones['pelvis'].matrix).translation;rows=[]
    for o in objects:
        if o.name=='Security_OutfitBody':continue
        groups,polys=components[o.name]
        for i,ids in enumerate(groups):
            if not polys[i] or len(ids)>1600:continue
            pts=[points[o.name][j] for j in ids];center=sum(pts,Vector())/len(pts)
            if abs(center.z-pelvis.z)>.40 or (Vector((center.x,center.y,0))-Vector((pelvis.x,pelvis.y,0))).length>.65:continue
            distances=[surface.find_nearest(p)[3] for p in pts]
            if min(distances)>.008:
                rows.append({'object':o.name,'component':i,'vertices':len(ids),'triangles':len(polys[i]),'center':list(center),
                    'size':(np.max(np.array(pts),0)-np.min(np.array(pts),0)).tolist(),
                    'min_gap_cm':min(distances)*100,'max_gap_cm':max(distances)*100,
                    'materials':[m.name for m in o.data.materials]})
    report['poses'][role+'_'+str(fr)]=sorted(rows,key=lambda r:-r['min_gap_cm'])
(OUT/'fragment_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'disconnected_main_surfaces':{n:[{k:r[k] for k in ['id','vertices','triangles','bound_center','bound_size','weights']} for r in rows] for n,rows in report['mesh_components'].items() if n.startswith(('Security_Shirt_Continuous','Security_Trousers_Continuous')) and len(rows)>1},'floating_waist_parts':report['poses']},indent=2),flush=True)
