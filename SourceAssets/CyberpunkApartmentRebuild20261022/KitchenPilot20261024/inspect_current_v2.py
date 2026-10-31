"""Read-only current kitchen interfaces for the requested overlap repair.
No actor/asset mutation, no map save, no PIE and no screenshots.
"""
from pathlib import Path
import json,traceback
import unreal as u
R=Path(__file__).resolve().parent
MAP='/Game/GameMaps/L_CyberpunkApartment'
report=dict(stage='reading',map=MAP,game_run=False,map_save=False)
def v(p):return list(p.to_tuple())
def tr(t):
    return dict(location=v(t.translation),rotation=dict(pitch=t.rotation.rotator().pitch,yaw=t.rotation.rotator().yaw,roll=t.rotation.rotator().roll),scale=v(t.scale3d))
def component(c):
    mesh=c.static_mesh
    t=c.get_world_transform()
    row=dict(component=c.get_path_name(),mesh=mesh.get_path_name() if mesh else None,
             relative=tr(c.get_relative_transform()),world=tr(t),
             location=v(c.relative_location),scale=v(c.relative_scale3d),
             parent=c.get_attach_parent().get_path_name() if c.get_attach_parent() else None,
             materials=[m.get_path_name() if m else None for m in c.get_materials()])
    if mesh:
        b=mesh.get_bounding_box();row['bounds']=[v(b.min),v(b.max)]
        points=dict(origin=(0,0,0),front=(.355,-.0325,.553),trim_face=(.355,-.0345,.553),handle=(.623,-.095,.553),table_top=(0,0,.7825))
        row['interface_world']={k:v(t.transform_location(u.Vector(*p))) for k,p in points.items()}
    return row
try:
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed and ed.get_game_world():raise RuntimeError('Preserve running game; this read-only batch does not stop PIE')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve dirty maps; no load/save submitted')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        label=a.get_actor_label()
        owned='KitchenDetail20261024' in [str(t) for t in a.tags]
        native=isinstance(a,u.ColdSteelSceneContainer) and (str(a.get_editor_property('container_id')).startswith(('Apartment.Kitchen_','Apartment.Fridge_')))
        keep=owned or native or label in ['AP_Kitchen_Dining','AP_Kitchen_Coffee','AP_Kitchen_Kettle','AP_Dining_Chair0','AP_Dining_Chair1','AP_Dining_Chair2','AP_Dining_Chair3','AP_Kitchen_Run','AP_Light_Kitchen']
        if not keep:continue
        row=dict(label=label,class_name=a.get_class().get_name(),path=a.get_path_name(),location=v(a.get_actor_location()),transform=tr(a.get_actor_transform()),components=[component(c) for c in a.get_components_by_class(u.StaticMeshComponent)])
        if native:
            row['container_id']=str(a.get_editor_property('container_id'))
            row['hinge']=tr(a.door_hinge.get_relative_transform())
            row['hinge_parent']=a.door_hinge.get_attach_parent().get_path_name() if a.door_hinge.get_attach_parent() else None
            row['body_parent']=a.body.get_attach_parent().get_path_name() if a.body.get_attach_parent() else None
            row['door_parent']=a.door.get_attach_parent().get_path_name() if a.door.get_attach_parent() else None
        report.setdefault('targets',{})[label]=row
    report['stage']='read_complete'
except Exception:
    report['stage']='failed';report['error']=traceback.format_exc()
finally:
    (R/'current-interfaces-v2.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if report['stage']!='read_complete':raise RuntimeError('Kitchen interface read failed; inspect current-interfaces-v2.json')
print('KITCHEN_CURRENT_INTERFACES_READ',len(report['targets']))
