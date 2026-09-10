import bpy,json
from pathlib import Path
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'akm_replacement_imported.blend'))
o=bpy.data.objects['high part akm'];m=o.data
neighbors=[[]for v in m.vertices]
for e in m.edges:
    a,b=e.vertices;neighbors[a].append(b);neighbors[b].append(a)
todo=set(range(len(m.vertices)));components=[]
while todo:
    stack=[todo.pop()];ids=[]
    while stack:
        i=stack.pop();ids.append(i)
        for n in neighbors[i]:
            if n in todo:todo.remove(n);stack.append(n)
    pts=[o.matrix_world@m.vertices[i].co for i in ids]
    components.append({'index':len(components),'count':len(ids),'bounds':[[min(p[a]for p in pts),max(p[a]for p in pts)]for a in range(3)],'ids':ids})
(OUT/'akm_replacement_components.json').write_text(json.dumps(components),encoding='utf-8')
print('COMPONENTS='+json.dumps([{k:v for k,v in c.items()if k!='ids'}for c in components]))
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend')
rig=bpy.data.objects['SK_AKM_Viewmodel'];rows=[]
for clip in ['idle','aim','fire','aim_fire']:
    act=bpy.data.actions['AKM_'+clip];rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0]
    for f in range(1,3 if clip in ['idle','aim'] else 27):
        bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
        rows.append({'clip':clip,'frame':f,'bones':{n:{'loc':list(rig.pose.bones[n].location),'rot':list(rig.pose.bones[n].rotation_quaternion)}for n in ['WPN_root','WPN_bolt','WPN_magazine']}})
(OUT/'akm_replacement_fire_contract.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('FIRE='+json.dumps(rows))
