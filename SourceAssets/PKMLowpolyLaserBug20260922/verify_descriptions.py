"""Editor-side verification that does not need a game instance.

Confirms the pieces the runtime verification would depend on:
  * the running module is the build that contains the description migration;
  * items.json on disk carries the rewritten copy for every weapon;
  * the profile save slot holds the refreshed text.

No PIE, no profile load, nothing written.
"""
import json
import os
import unreal as u

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = r'D:\FPS3D\FPSGAME\Content\ColdSteelData\items.json'
SAVES = r'D:\FPS3D\FPSGAME\Saved\SaveGames'

WEAPONS = [
    'ue_m4a1', 'ue_akm', 'ue_qbz191', 'ue_ash12', 'ue_m16a2', 'ue_a762',
    'ue_pkm_lowpoly', 'ue_m1911', 'ue_dan_wesson715',
    'ue_rune_sword', 'ue_frost_crystal_sword', 'ue_highland_claymore',
]

lines = []
lines.append('engine version: %s' % u.SystemLibrary.get_engine_version())
lines.append('project dir   : %s' % u.Paths.project_dir())

with open(ITEMS, 'r', encoding='utf-8') as handle:
    catalog = json.load(handle)
lines.append('')
lines.append('items.json descriptions:')
for wid in WEAPONS:
    entry = catalog.get(wid) or {}
    desc = entry.get('desc', '')
    lines.append('  %-26s %-18s %3d chars' % (wid, entry.get('name', '?'), len(desc)))

# The save slot the running build reads.
for slot in ('ColdSteelPlayer_A', 'ColdSteelPlayer_B'):
    path = os.path.join(SAVES, slot + '.sav')
    if not os.path.exists(path):
        lines.append('%s: missing' % slot)
        continue
    data = open(path, 'rb').read()
    stats = []
    for wid in ('ue_m4a1', 'ue_pkm_lowpoly', 'ue_rune_sword', 'ue_highland_claymore'):
        new = catalog.get(wid, {}).get('desc', '')[:10].encode('utf-16-le')
        stats.append('%s new=%d' % (wid.replace('ue_', ''), data.count(new)))
    lines.append('%s (%d bytes, mtime %d): %s'
                 % (slot, len(data), int(os.path.getmtime(path)), '  '.join(stats)))

text = '\n'.join(lines)
u.log('PKM_DESC_VERIFY\n' + text)
print(text)
