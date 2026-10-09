"""Locate the user's V08 sleeve defect in the authoring/bind data, without renders."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/rebuild_arms_v05.py').read_text(encoding='utf-8')
prefix=src.split("for o in list(scene.objects):\n    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)")[0]
prefix=prefix.replace("ROOT=BASE/'V05'","ROOT=BASE/'V09'").replace("BASE/'V04/Authoring/FacelessSecurity_V04.blend'","BASE/'V08/Authoring/FacelessSecurity_V08.blend'")
exec(compile(prefix,'bind_source','exec'))
report={'source':'V08','rig_world':list(map(list,rig.matrix_world)),'objects':{},'poses':{}}
names=['Security_Shirt_Armholes_V08','Security_OutfitBody','Security_Cuff_l','Security_Cuff_r']
objects=[bpy.data.objects[n] for n in names]
sources={};edges={};weights={}
for o in objects:
    ws=read_weights(o);weights[o.name]=ws
    p=np.array([fit(w)@v.co for w,v in zip(ws,o.data.vertices)])
    native=np.array([o.matrix_world@v.co for v in o.data.vertices]);sources[o.name]=p
    e=np.array([tuple(x.vertices) for x in o.data.edges]);edges[o.name]=e
    before=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1);after=np.linalg.norm(native[e[:,0]]-native[e[:,1]],axis=1)
    arm=(abs(p[:,0])>.12)&(p[:,2]>1.30)&(p[:,2]<1.66)
    ids=np.flatnonzero((arm[e[:,0]]|arm[e[:,1]])&(after>.025)&(after>before*3))
    worst=ids[np.argsort(after[ids])[-8:]]
    report['objects'][o.name]={'vertices':len(p),'local_to_world':list(map(list,o.matrix_world)),
      'bind_long_edges':len(ids),'worst':[{'ids':e[i].tolist(),'source':p[e[i]].tolist(),'native':native[e[i]].tolist(),
       'source_length':float(before[i]),'native_length':float(after[i]),'weights':[ws[j] for j in e[i]]} for i in worst]}
    if 'Shirt' in o.name:
        report['cap_profiles']={}
        for side,start in [('l',4774),('r',8662)]:
            report['cap_profiles'][side]=[{'row':k,'source_center':p[start+k*72:start+(k+1)*72].mean(axis=0).tolist(),
               'native_center':native[start+k*72:start+(k+1)*72].mean(axis=0).tolist(),
               'native_extent':np.ptp(native[start+k*72:start+(k+1)*72],axis=0).tolist()} for k in range(16)]
with bpy.data.libraries.load(str(BASE/'V06/Motion/FacelessSecurity_MaleMotion_V06.blend'),link=False) as (a,b):
    b.actions=['Security_MaleV06_idle','Security_MaleV06_walk','Security_MaleV06_attack']
actions=dict(zip(['idle','walk','attack'],b.actions));rig.animation_data_create()
for role,fr in [('idle',1),('walk',61),('attack',40)]:
    action=actions[role];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(fr)
    dg=bpy.context.evaluated_depsgraph_get();posed={};result={}
    for o in objects:
        ev=o.evaluated_get(dg);me=ev.to_mesh();p=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear();posed[o.name]=p
        s=sources[o.name];e=edges[o.name];old=np.linalg.norm(s[e[:,0]]-s[e[:,1]],axis=1);new=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)
        mask=(abs(s[:,0])>.12)&(s[:,2]>1.30)&(s[:,2]<1.66)
        ids=np.flatnonzero((new>.025)&(new>old*3)&(mask[e[:,0]]|mask[e[:,1]]))
        result[o.name]={'long_arm_edges':len(ids),'max_edge_cm':float(new.max()*100),'bad_indices':e[ids[:20]].tolist()}
    result['hands']={}
    for side,sign in [('l',1),('r',-1)]:
        p=posed['Security_OutfitBody'];s=sources['Security_OutfitBody'];mask=(s[:,0]*sign>.31)&(s[:,2]<1.09)&(s[:,2]>.70)
        wrist=rig.matrix_world@rig.pose.bones['hand_'+side].head
        result['hands'][side]={'vertex_count':int(mask.sum()),'bounds':[p[mask].min(axis=0).tolist(),p[mask].max(axis=0).tolist()],
          'wrist':list(wrist),'max_wrist_distance':float(np.linalg.norm(p[mask]-np.array(wrist),axis=1).max()),
          'cuff_center':posed['Security_Cuff_'+side].mean(axis=0).tolist()}
    report['poses'][role+'_'+str(fr)]=result
(ROOT/'bind_defect_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
