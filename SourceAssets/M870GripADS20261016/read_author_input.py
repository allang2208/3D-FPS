"""Read the current author bind and support-hand surfaces for the repair."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M870UrbanAnimations20261015/M870_Urban_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_M870_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
pose={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones}
G=rest['WPN_root']@pose['WPN_root'].inverted()
def vec(v):return [round(x,6) for x in v]
def under(n,root):
    while n:
        if n==root:return True
        b=r.data.bones.get(n);n=b.parent.name if b and b.parent else None
    return False
report={'bones':{},'surfaces':{},'actions':{a.name:list(a.frame_range) for a in bpy.data.actions if a.name.startswith('A_M870_')}}
for n,m in pose.items():
    if n.endswith('_l') or n in ('WPN_root','WPN_bolt','WPN_RearSight','WPN_FrontSight'):
        p=r.data.bones[n].parent;name=p.name if p else None
        local=pose[name].inverted()@m if p else m;lr=rest[name].inverted()@rest[n] if p else rest[n]
        report['bones'][n]=dict(position=vec((G@m).translation),rest_position=vec(rest[n].translation),pose=[list(v) for v in m],rest=[list(v) for v in rest[n]],local_rest_delta=vec((lr.inverted()@local).to_euler()))
deps=bpy.context.evaluated_depsgraph_get()
for ob in s.objects:
    if ob.type!='MESH':continue
    ev=ob.evaluated_get(deps);me=ev.to_mesh();names={g.index:g.name for g in ob.vertex_groups}
    keep=[i for i,v in enumerate(ob.data.vertices) if 'pump' in ob.name or any(g.weight>.4 and under(names[g.group],'hand_l') for g in v.groups)]
    if keep:
        vs=[G@r.matrix_world.inverted()@ev.matrix_world@me.vertices[i].co for i in keep]
        report['surfaces'][ob.name]=dict(count=len(vs),minimum=vec(Vector([min(v[a] for v in vs) for a in range(3)])),maximum=vec(Vector([max(v[a] for v in vs) for a in range(3)])),centre=vec(sum(vs,Vector())/len(vs)))
    ev.to_mesh_clear()
(O/'author_input.json').write_text(json.dumps(report,indent=2))
for n,d in report['bones'].items():
    if n.startswith(('upperarm','lowerarm','hand_','WPN_')) or '01_l' in n or 'metacarpal' in n:print(n,d['position'],'rest',d['rest_position'],'localDeltaDeg',[round(math.degrees(x),1) for x in d['local_rest_delta']])
print('SURFACES',json.dumps(report['surfaces']))
