"""Read an existing, unresponsive-to-input game session; never start or alter it.

Run through the project's existing Python/MCP bridge only while the user's
affected session is still alive. Does not press keys, change focus, unlock
input, load a map, save assets, or start a performance recording.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import unreal as u


def path(obj):
    return obj.get_path_name() if obj else None


def prop(obj, name):
    if not obj:
        return None
    try:
        value = obj.get_editor_property(name)
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        return path(value) if isinstance(value, u.Object) else str(value)
    except Exception:
        return None  # Unexposed fields remain unknown, never treated as false.


def call(obj, name):
    try:
        return getattr(obj, name)()
    except (AttributeError, TypeError):
        return None


editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world() if editor else None
if not world:
    raise RuntimeError('No existing game world. This script does not launch or resume a game.')
pc = u.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_pawn() if pc else None
report = {
    'utc': datetime.now(timezone.utc).isoformat(),
    'world': path(world),
    'paused': u.GameplayStatics.is_game_paused(world),
    'controller': path(pc),
    'pawn': path(pawn),
    'cursor_visible': prop(pc, 'show_mouse_cursor'),
    'move_ignored': call(pc, 'is_move_input_ignored'),
    'look_ignored': call(pc, 'is_look_input_ignored'),
    'controller_block_input': prop(pc, 'block_input'),
    'pawn_block_input': prop(pawn, 'block_input'),
    'panels': {name: prop(pc, name) for name in (
        'GameMenu', 'AlchemyPanel', 'WoodworkingPanel', 'ExpeditionPanel',
        'GunsmithPanel', 'EnhancementPanel', 'WeatherPanel', 'ColdSteelHUD')},
    'input_components': [],
    'widgets': [],
    'limitations': 'Input-component list is not the controller input-stack order. Native routing is null on an older binary; unknown fields are never treated as false.',
}
game_instance = u.GameplayStatics.get_game_instance(world)
# UE marks SubsystemBlueprintLibrary.GetGameInstanceSubsystem internal-only,
# so Python does not export it. Select the existing instance by its exact outer.
loading = next((obj for obj in u.ObjectIterator(u.TransitLoadingSubsystem)
                if obj.get_outer() == game_instance), None)
native_state = call(loading, 'get_input_routing_state')
report['native_routing'] = json.loads(native_state) if native_state else None
if isinstance(pawn, u.Character):
    movement = pawn.get_character_movement()
    report['movement'] = {
        'tick_enabled': call(movement, 'is_component_tick_enabled'),
        'active': call(movement, 'is_active'),
        'mode': prop(movement, 'movement_mode'),
    }
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
    for component in actor.get_components_by_class(u.InputComponent):
        report['input_components'].append({
            'actor': path(actor), 'component': path(component),
            'actor_block_input': prop(actor, 'block_input'),
            'auto_receive_input': prop(actor, 'auto_receive_input'),
            'block_input': prop(component, 'block_input'),
            'priority': prop(component, 'priority'),
        })
for widget in u.WidgetBlueprintLibrary.get_all_widgets_of_class(world, u.UserWidget, False):
    if widget.is_in_viewport() or widget.has_keyboard_focus() or widget.has_mouse_capture():
        report['widgets'].append({
            'widget': path(widget), 'visibility': str(widget.get_visibility()),
            'enabled': widget.get_is_enabled(), 'in_viewport': widget.is_in_viewport(),
            'keyboard_focus': widget.has_keyboard_focus(), 'mouse_capture': widget.has_mouse_capture(),
        })
out = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir())) / 'InputHandoff20261017'
out.mkdir(parents=True, exist_ok=True)
target = out / ('input-state-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ENTRY_INPUT_STATE ' + str(target))
