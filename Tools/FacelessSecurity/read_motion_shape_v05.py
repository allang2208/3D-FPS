"""Read the reported sleeve stretch and sole clearance from the current source."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
OUT=ROOT/'V05';(OUT/'Logs').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'V04/Authoring/FacelessSecurity_V04.blend'))
rig=bpy.data.objects['root'];scene=bpy.context.scene
for tr in rig.animation_data.nla_tracks:tr.mute=True
rig.animation_data.action=None;scene.frame_set(0)
objects=[o for o in scene.objects if o.type=='MESH' and o.name!='Security_CompleteBody']
base={};edges={}
for o in objects:
    e=np.array([tuple(e.vertices) for e in o.data.edges]);edges[o.name]=e
    p=np.array([o.matrix_world@v.co for v in o.data.vertices]);base[o.name]=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)
act=next(a for a in bpy.data.actions if a.name.startswith('Security_MaleV03_walk'));rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0]
report={}
for frame in [1,61,121,181]:
    scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get();rows={};floor={}
    for o in objects:
        ev=o.evaluated_get(dg);me=ev.to_mesh();p=np.array([ev.matrix_world@v.co for v in me.vertices]);e=edges[o.name]
        length=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1);ratio=length/np.maximum(base[o.name],.0005)
        bad=(length>.075)&(ratio>2.5)
        if bad.any():
            worst=np.flatnonzero(bad)[np.argsort(length[bad])[-3:]]
            rows[o.name]={'count':int(bad.sum()),'max_length':float(length[bad].max()),'edges':[]}
            for i in worst:
                rows[o.name]['edges'].append({'length':float(length[i]),'ratio':float(ratio[i]),'points':p[e[i]].tolist(),'rest_points':[(o.matrix_world@o.data.vertices[int(vi)].co)[:] for vi in e[i]],'weights':[{o.vertex_groups[g.group].name:g.weight for g in o.data.vertices[int(vi)].groups} for vi in e[i]]})
        if o.name.startswith(('Security_Boot_','Security_BootSole_')):
            i=int(np.argmin(p[:,2]));floor[o.name]={'min_z':float(p[i,2]),'point':p[i].tolist(),'weights':{o.vertex_groups[g.group].name:g.weight for g in o.data.vertices[i].groups}}
        ev.to_mesh_clear()
    report[str(frame)]={'stretch':rows,'ground':floor}
(OUT/'shape_motion_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({f:{'stretch':{n:{'count':v['count'],'max':v['max_length']} for n,v in r['stretch'].items()},'ground':{n:v['min_z'] for n,v in r['ground'].items()}} for f,r in report.items()}),flush=True)
