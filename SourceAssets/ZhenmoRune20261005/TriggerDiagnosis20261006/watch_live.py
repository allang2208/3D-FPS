"""Read-only, bounded observation of the current PIE field; no gameplay changes."""
from pathlib import Path
import json
import time
import unreal as u

OUT = Path(__file__).resolve().parent / 'observed_field.json'
records = []
started = time.monotonic()
last = 0.
handle = None

def sample(delta):
    global last
    now = time.monotonic()
    if now - started > 180:
        u.unregister_slate_post_tick_callback(handle)
        return
    if now - last < .5:
        return
    last = now
    try:
        w = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not w:
            return
        a = u.GameplayStatics.get_player_character(w, 0)
        if not a:
            return
        c = next((c for c in a.get_components_by_class(u.ActorComponent)
                  if c.get_class().get_name() == 'ZhenmoRuneComponent'), None)
        s = next((c for c in a.get_components_by_class(u.DynamicMeshComponent)
                  if c.get_name() == 'ZhenmoSoftGround'), None)
        n = next((c for c in a.get_components_by_class(u.NiagaraComponent)
                  if c.get_name() == 'ZhenmoRisingGold'), None)
        row = {'seconds': u.GameplayStatics.get_time_seconds(w),
               'world': w.get_name(), 'tick': c.is_component_tick_enabled() if c else None}
        if s:
            m = s.get_material(0)
            row.update(triangles=s.get_dynamic_mesh().get_triangle_count(),
                       visible=s.is_visible(), opacity=m.get_scalar_parameter_value('FieldOpacity'),
                       center=str(m.get_vector_parameter_value('FieldCenter')),
                       material=m.get_path_name())
        if n:
            row['particles_active'] = n.is_active()
        if c and (row['tick'] or not records or len(records) % 10 == 0 or s):
            records.append(row)
            OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        OUT.write_text(json.dumps({'error': str(exc), 'samples': records}, indent=2), encoding='utf-8')
        u.unregister_slate_post_tick_callback(handle)

handle = u.register_slate_post_tick_callback(sample)
print('ZHENMO_READ_ONLY_WATCH_STARTED: at most 180 seconds')
