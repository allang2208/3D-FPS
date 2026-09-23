"""Make sure the two superseded floor actors really stop rendering in the editor viewport.

`AActor::SetActorHiddenInGame` sets bHidden, which in UE hides at RUNTIME only: the editor
viewport still draws the actor, so a coplanar leftover would keep z-fighting against the new
paving. Component visibility is what actually hides it in both places. The builder set that
property through a guarded call, so this script verifies and repairs it.

Idempotent: writes and saves only when a component is still visible. No PIE.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
TAG_SUP = 'ColdSteel.MainPlaza.Superseded'

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def run():
    rows = []
    changed = False
    for actor in api.get_all_level_actors():
        if TAG_SUP not in [str(t) for t in actor.tags]:
            continue
        comp = actor.static_mesh_component if isinstance(actor, unreal.StaticMeshActor) else None
        row = dict(label=actor.get_actor_label(),
                   comp_visible_before=(comp.get_editor_property('visible') if comp else None))
        if comp is not None and row['comp_visible_before']:
            actor.modify()
            try:
                comp.set_visibility(False)
            except Exception as exc:
                row['set_visibility_error'] = str(exc)
                comp.set_editor_property('visible', False)
            changed = True
        if comp is not None:
            row['comp_visible_after'] = comp.get_editor_property('visible')
        rows.append(row)
    result = dict(rows=rows, changed=changed)
    if changed:
        result['saved'] = bool(level.save_current_level())
    else:
        result['saved'] = False
    return result


try:
    result = run()
    (HERE / 'superseded_visibility.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('VISIBILITY_OK changed=%s saved=%s' % (result['changed'], result['saved']))
    for row in result['rows']:
        print('  %-24s before=%-5s after=%s %s'
              % (row['label'], row['comp_visible_before'], row.get('comp_visible_after'),
                 row.get('set_visibility_error', '')))
except Exception:
    (HERE / 'superseded_visibility_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('VISIBILITY_FAILED')
    raise
