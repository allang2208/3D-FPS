"""Publish saved native-bound bare skin without changing equipment or savegames."""
import json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
AUTHOR=ROOT/'SourceAssets/ModularOutfit20260924/NativeSkin'
path=ROOT/'Content/ColdSteelData/modular_outfits.json'
saved=json.loads((AUTHOR/'saved.json').read_text())
config=json.loads(path.read_text(encoding='utf-8-sig'))
required={p['rig_profile'] for p in config['profiles'].values()}
if not required.issubset(saved):raise RuntimeError('Finish native skin asset production before enabling default hands')
backup=AUTHOR/'modular_outfits.before_native_skin.json'
if not backup.exists():backup.write_bytes(path.read_bytes())
for source,profile in config['profiles'].items():
    native=saved[profile['rig_profile']]
    if native['source']!=source:raise RuntimeError('Native source identity differs: '+source)
    profile['base']=native['mesh']
    profile['native_bare_skin']=native['mesh']
    profile['shirt_covers']=native['shirt_covers']
    profile['glove_covers']=native['glove_covers']
# Registration is not visual approval. Preserve the chosen default, including
# the original-hands fallback while a single-weapon candidate is being authored.
config.setdefault('native_bare_hands_default',False)
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('NATIVE_BARE_SKIN_REGISTERED',len(required),'DEFAULT_ENABLED',config['native_bare_hands_default'])
