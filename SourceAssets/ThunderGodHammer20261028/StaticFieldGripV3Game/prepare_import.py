"""Reuse the established import, changing only the owned visual and leather bake."""
from pathlib import Path
P=Path(__file__).resolve().parent
V2=P.parent/'StaticFieldGripV2'
s=(V2/'import_assets.py').read_text(encoding='utf-8')
s=s.replace('StaticFieldGripV2','StaticFieldGripV3Game')
s=s.replace("D = '/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV3Game'", "D = '/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV3Game'\nOLD = '/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV2'")
s=s.replace("for family in sorted({r['family'] for r in manifest['materials'] if r['kind']=='pbr'}):", "for family in ('Leather',):")
s=s.replace("    if row['kind'] == 'native':", """    if row['slot'] != 'M_StaticField_Leather' and row['kind'] != 'native':
        reused = u.load_asset(OLD+'/Materials/'+row['slot'])
        if not reused:raise RuntimeError('Existing metal material missing: '+row['slot'])
        materials[row['slot']] = reused
        receipt['materials'].append(dict(slot=row['slot'], asset=reused.get_path_name(), reused=True))
        continue
    if row['kind'] == 'native':""")
s=s.replace('settings.fallback_percent_triangles = 1.', 'settings.fallback_percent_triangles = .15')
s=s.replace('full_fidelity_fallback=True', 'full_fidelity_fallback=False,fallback_fraction=.15,nanite_triangles=mesh.get_num_nanite_triangles(),fallback_triangles=mesh.get_num_triangles(0)')
s=s.split('# Install this exclusive grip icon')[0]+"""
# The accepted design icon remains unchanged: this revision changes topology only.
receipt['icon'] = dict(reused=True, reason='Same design and materials; existing actual-model icon preserved')
receipt['complete'] = True
record()
print('STATIC_FIELD_GAME_ASSETS_SAVED',mesh.get_path_name())
"""
(P/'import_assets.py').write_text(s,encoding='utf-8')
s=(V2/'install.ps1').read_text(encoding='utf-8')
(P/'install.ps1').write_text(s,encoding='utf-8')
s=(V2/'publish.py').read_text(encoding='utf-8').replace('StaticFieldGripV2','StaticFieldGripV3Game').replace('V2 import','V3 import').replace('STATIC_FIELD_V2_VISUAL','STATIC_FIELD_V3_GAME_VISUAL')
(P/'publish.py').write_text(s,encoding='utf-8')
print('Version-isolated V3 import and publication prepared')
