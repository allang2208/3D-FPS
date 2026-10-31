"""Read the saved, scoped kitchen assembly; no map write or runtime simulation."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
w=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
out=dict(cables=[],materials={},game_run=False)
v2='KR_Cable_CoffeeCounter' in actors
for name in (['Coffee','Kettle','CoffeeCounter'] if v2 else ['Coffee','Kettle']):
    a=actors['KR_Cable_'+name];c=a.cable_component;t=c.get_attached_component()
    out['cables'].append(dict(name=name,target=t.get_owner().get_actor_label() if t else None,endpoint=list(t.get_world_transform().transform_location(c.end_location).to_tuple()) if t else None,start=list(c.get_world_location().to_tuple()),anchor_parent=a.get_attach_parent_actor().get_actor_label(),gravity=c.cable_gravity_scale,collision=c.enable_collision,segments=c.num_segments,length=c.cable_length))
for label in ['AP_ResidentialDetails','KP_Sink','KP_OvenFront','KR_PowerHardware']:
    c=actors[label].static_mesh_component
    out['materials'][label]=[m.get_path_name() if m else None for m in c.get_materials()]
    if any(m is None or 'DefaultMaterial' in m.get_path_name() for m in c.get_materials()):raise RuntimeError('Unassigned material '+label)
for row in out['cables']:
    target='KR_CoffeeEdgeBend' if v2 and row['name'].startswith('Coffee') else 'AP_Kitchen_'+row['name']
    if row['target']!=target or not row['collision'] or row['gravity']!=1:raise RuntimeError('Saved cable contract '+row['name'])
(R/'saved_kitchen_readback.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('SAVED_KITCHEN_REFERENCES_READ',len(out['cables']))
