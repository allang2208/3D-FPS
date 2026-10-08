from pathlib import Path
import base64,json
import unreal as u
OUT=Path(__file__).resolve().parent
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
a=u.GameplayStatics.get_player_character(w,0)
pc=u.GameplayStatics.get_player_controller(w,0)
if not (OUT/'camera_before.json').exists():
    (OUT/'camera_before.json').write_text(json.dumps({'rotation':pc.get_control_rotation().to_tuple()}),encoding='utf-8')
u.GameplayStatics.set_game_paused(w,True)
pc.set_control_rotation(u.Rotator(-60,pc.get_control_rotation().yaw,0))
for c in a.get_components_by_class(u.DynamicMeshComponent):
    if c.get_name()=='ZhenmoSoftGround':
        c.set_visibility(True)
        c.get_material(0).set_scalar_parameter_value('FieldOpacity',1)
        print('SURFACE bounds='+str(u.SystemLibrary.get_component_bounds(c))+' mat='+str(c.get_material(0))+' hidden='+str(c.get_editor_property('hidden_in_game')))
for c in a.get_components_by_class(u.NiagaraComponent):
    if c.get_name()=='ZhenmoRisingGold':
        print('NIAGARA methods='+str([n for n in dir(c) if any(s in n for s in ['asset','valid','ready','complete','cull','scalab'])]))
        print('NIAGARA asset='+str(c.get_asset()))
print('PAUSED_FOR_VISUAL_DIAGNOSIS')
