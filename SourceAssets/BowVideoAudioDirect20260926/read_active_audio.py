"""Read existing bow audio bindings; no playback, world creation or save edits."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
out = ROOT / 'Saved/BowVideoAudioDirect20260926'
out.mkdir(parents=True, exist_ok=True)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result = {'world': world.get_path_name() if world else None, 'components': []}
pawn = u.GameplayStatics.get_player_character(world, 0) if world else None
if pawn:
    for comp in pawn.get_components_by_class(u.ActorComponent):
        if comp.get_class().get_name() != 'BowWeaponComponent':
            continue
        row = {'component': comp.get_path_name()}
        for name in ('draw_sound', 'release_sound', 'nock_sound', 'take_arrow_sound'):
            try:
                value = comp.get_editor_property(name)
                row[name] = value.get_path_name() if value else None
            except Exception as exc:
                row[name] = {'read_error': str(exc)}
        result['components'].append(row)
result['saved_bows'] = []
for suffix in ('A', 'B'):
    path = ROOT / 'Saved/SaveGames' / f'ColdSteelPlayer_{suffix}.sav'
    if not path.exists():
        continue
    buf = path.read_bytes()
    for encoding in ('utf-16-le', 'utf-8'):
        needle = '{'.encode(encoding)
        start = 0
        while True:
            start = buf.find(needle, start)
            if start < 0:
                break
            try:
                data, _ = json.JSONDecoder().raw_decode(buf[start:].decode(encoding, errors='ignore'))
                if isinstance(data, dict) and data.get('id') == 'bow_dark':
                    result['saved_bows'].append({'slot': suffix, **{key: data.get(key) for key in (
                        'bow_presentation_revision', 'bow_draw_sound', 'bow_release_sound')}})
            except (ValueError, UnicodeError):
                pass
            start += len(needle)
(out / 'active-audio.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('BOW_AUDIO_BINDINGS ' + json.dumps(result, ensure_ascii=False))
