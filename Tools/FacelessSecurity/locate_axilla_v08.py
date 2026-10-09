"""Read the reported upper-arm defects in the current mesh and donor poses."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/rebuild_arms_v05.py').read_text(encoding='utf-8')
prefix=src.split("for o in list(scene.objects):\n    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)")[0]
prefix=prefix.replace("ROOT=BASE/'V05'","ROOT=BASE/'V08'").replace("BASE/'V04/Authoring/FacelessSecurity_V04.blend'","BASE/'V07/Authoring/FacelessSecurity_V07.blend'")
exec(compile(prefix,'axilla_source','exec'))
objects=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('Security_Shirt_Continuous','Security_Epaulette','Security_RankBar'))]
source_points={};weights={};edges={};report={'source':'V07','objects':{},'poses':{}}
for o in objects:
    weights[o.name]=read_weights(o);points=np.array([fit(w)@v.co for w,v in zip(weights[o.name],o.data.vertices)])
    source_points[o.name]=points;e=np.array([tuple(edge.vertices) for edge in o.data.edges]);edges[o.name]=e
    arm=(np.abs(points[:,0])>.12)&(points[:,2]>1.22)&(points[:,2]<1.68)
    length=np.linalg.norm(points[e[:,0]]-points[e[:,1]],axis=1)
    report['objects'][o.name]={'vertices':len(points),'source_long_edges':int(np.sum((length>.05)&(arm[e[:,0]]|arm[e[:,1]]))),
        'max_source_edge_cm':float(length.max()*100)}
with bpy.data.libraries.load(str(BASE/'V06/Motion/FacelessSecurity_MaleMotion_V06.blend'),link=False) as (a,b):
    b.actions=['Security_MaleV06_idle','Security_MaleV06_walk','Security_MaleV06_attack']
actions=dict(zip(['idle','walk','attack'],b.actions));rig.animation_data_create()
for role,fr in [('idle',1),('walk',61),('walk',121),('attack',40),('attack',80)]:
    action=actions[role];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(fr)
    dg=bpy.context.evaluated_depsgraph_get();rows={}
    for o in objects:
        ev=o.evaluated_get(dg);me=ev.to_mesh();p=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear()
        e=edges[o.name];s=source_points[o.name]
        old=np.linalg.norm(s[e[:,0]]-s[e[:,1]],axis=1);new=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1);ratio=new/np.maximum(old,.0003)
        mask=(np.abs(s[:,0])>.12)&(s[:,2]>1.22)&(s[:,2]<1.68)
        bad=(new>.05)&(ratio>2.5)&(mask[e[:,0]]|mask[e[:,1]])
        selected=np.flatnonzero(bad);worst=selected[np.argsort(new[selected])[-8:]]
        rows[o.name]={'stretched_edges':int(bad.sum()),'max_edge_cm':float(new.max()*100),'worst':[]}
        for i in worst:
            rows[o.name]['worst'].append({'vertices':e[i].tolist(),'source_cm':float(old[i]*100),'posed_cm':float(new[i]*100),'ratio':float(ratio[i]),
                'source_points':s[e[i]].tolist(),'posed_points':p[e[i]].tolist(),'weights':[weights[o.name][int(j)] for j in e[i]]})
    report['poses'][role+'_'+str(fr)]=rows
(ROOT/'axilla_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'source':report['objects'],'poses':{p:{n:{'stretched':r['stretched_edges'],'max_cm':r['max_edge_cm'],'worst':r['worst'][-2:]} for n,r in objs.items() if r['stretched_edges']} for p,objs in report['poses'].items()}},indent=2),flush=True)
