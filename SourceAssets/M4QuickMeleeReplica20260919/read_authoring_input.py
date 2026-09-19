import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
source=P.parent/'M4ContactImpact20260910/M4_Hand_MAT_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_idle']
r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
pose={b.name:[list(row) for row in b.matrix] for b in r.pose.bones}
root=r.pose.bones['WPN_root'].matrix
meshes=[]
for ob in bpy.data.objects:
    if ob.type!='MESH' or not any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers):continue
    dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);mesh=ev.to_mesh()
    points=[r.matrix_world.inverted()@ev.matrix_world@v.co for v in mesh.vertices]
    weighted={}
    for v,co in zip(ob.data.vertices,points):
        if not v.groups:continue
        group=ob.vertex_groups[max(v.groups,key=lambda x:x.weight).group].name
        if group.startswith('WPN_'):
            weighted.setdefault(group,[]).append(list(root.inverted()@co))
    meshes.append({'name':ob.name,'vertices':len(points),'materials':[m.name if m else None for m in ob.data.materials],
                   'bounds':[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)],
                   'weapon_groups':{n:{'count':len(v),'bounds':[[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)]} for n,v in weighted.items()}})
    ev.to_mesh_clear()
data={'source':str(source),'pose':pose,'rig_world':[list(row) for row in r.matrix_world],'meshes':meshes}
(P/'authoring_input.json').write_text(json.dumps(data,indent=2))
print(json.dumps({'WPN_root':pose['WPN_root'],'hands':{n:list((root.inverted()@r.pose.bones[n].matrix).translation) for n in ['hand_r','hand_l','WPN_SOCKET_Muzzle']},'meshes':meshes},indent=2),flush=True)
