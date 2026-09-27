from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
paths={k:'/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_'+k for k in ['resonance_rune','erosion_rune','conduction_rune']}
paths['wild_rune']='/Game/Weapons/HighlandClaymore20260922/WildRune/T_Mask_wild_rune'
result={}
for k,path in paths.items():
    tex=u.load_asset(path)
    result[k]={'asset':path,'source':list(tex.get_editor_property('asset_import_data').extract_filenames())}
(P/'rune_sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('RUNE_SOURCE_PATHS_SAVED')
