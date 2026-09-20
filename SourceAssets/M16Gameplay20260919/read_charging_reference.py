"""Read the actual handle geometry and accepted M4 charging poses for authoring."""
import bpy, json
from pathlib import Path
from mathutils import Vector

out=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(out.parent/'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
action=bpy.data.actions['M4_MAT_equip_charge']
rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
report={'source_action':action.name,'frames':list(action.frame_range),'fps':scene.render.fps,'poses':{}}
for frame in [0,7,12,15,18,19,20,22,27,38]:
    scene.frame_set(frame);bpy.context.view_layer.update()
    root=rig.pose.bones['WPN_root'].matrix.inverted()
    report['poses'][frame]={name:list((root@rig.pose.bones[name].matrix).translation)
        for name in ['WPN_ChargingHandle','WPN_bolt','hand_r','hand_l']}
    if frame==12:
        points=[]
        for obj in scene.objects:
            group=obj.vertex_groups.get('WPN_ChargingHandle') if obj.type=='MESH' else None
            if not group:continue
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            transform=root@rig.matrix_world.inverted()@evaluated.matrix_world
            for vertex in obj.data.vertices:
                if any(g.group==group.index and g.weight>.5 for g in vertex.groups):
                    points.append(transform@mesh.vertices[vertex.index].co)
            evaluated.to_mesh_clear()
        report['m4_handle_bounds_m']=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
        rear=max(p.y for p in points)
        report['m4_handle_rear_vertices_m']=[list(p) for p in points if p.y>=rear-.012]
with bpy.data.libraries.load(str(out.parent/'M16A2Migration20260919/M16A2_Mechanical_Editable.blend'),link=False) as (src,dst):
    dst.objects=['M16A2_ChargingHandle','M16A2_ChargingHandleLatch']
for obj in dst.objects:
    points=[v.co for v in obj.data.vertices]
    rear=min(p.x for p in points)
    report[obj.name]={'bounds_cm':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],
        'rear_vertices_cm':[list(p) for p in points if p.x<=rear+1.2]}
(out/'charging_reference.json').write_text(json.dumps(report,indent=2))
print('M16_CHARGING_REFERENCE_SAVED')
