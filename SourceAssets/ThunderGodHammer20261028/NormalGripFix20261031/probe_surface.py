import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(R/'SourceAssets/SteelWarhammer20261014/NormalComboRhythmV7/Warhammer_Combo_Rhythm_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
rest=rig.data.bones['WPN_root'].matrix_local
hammer=bpy.data.objects['SM_SteelWarhammer'];native=[rest.inverted()@rig.matrix_world.inverted()@hammer.matrix_world@v.co for v in hammer.data.vertices]
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as (src,dst):dst.objects=['SM_ThunderGodHammer_grip_factory']
factory=dst.objects[0];bpy.context.collection.objects.link(factory);bpy.context.view_layer.update()
factorypts=[factory.matrix_world@v.co for v in factory.data.vertices]
out={'geometry':{},'skin':{}}
for label,points in [('SteelSource',native),('ThorFactory',factorypts)]:
    out['geometry'][label]={}
    for z in (.079,.18,.298):
        rs=[math.hypot(v.x+.00045,v.y+.00105)*1000 for v in points if abs(v.z-z)<.025]
        rs.sort();out['geometry'][label][str(z)]={'r_mm':[rs[0],rs[len(rs)//2],rs[-1]],'verts':len(rs)} if rs else None
skin=bpy.data.objects['Warhammer_BareArmsV7']
group={g.index:g.name for g in skin.vertex_groups}
ids={s:[v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if group[g.group].endswith('_'+s) and group[g.group].startswith(('hand','thumb','index','middle','ring','pinky')))>.8] for s in 'lr'}
for name in ('A_Warhammer_Slash1','A_Warhammer_Slash2','A_Warhammer_Slash3'):
    a=bpy.data.actions[name];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    rows=[]
    for t in (0,.3,.5,.84,.97,1.05,1.4,1.75):
        f=t*300;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
        ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
        inv=(rig.matrix_world@rig.pose.bones['WPN_root'].matrix).inverted()@ev.matrix_world
        row={'t':t,'hands':{}}
        for s in 'lr':
            ps=[inv@me.vertices[i].co for i in ids[s]]
            rs=sorted(math.hypot(v.x+.00045,v.y+.00105)*1000 for v in ps)
            row['hands'][s]={'closest_skin_mm':rs[0],'p01_skin_mm':rs[len(rs)//100]}
        ev.to_mesh_clear();rows.append(row)
    out['skin'][name]=rows
(P/'surface_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('GRIP_SURFACE '+json.dumps(out))
