"""Select the user's requested corrected blade composition and retain its recipe."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
work=ROOT/'SourceAssets/MeleeMasteries20261019'
manifest=work/'manifest.json'
data=json.loads(manifest.read_text(encoding='utf-8'))
revision=json.loads((work/'blade-v2-generation.json').read_text(encoding='utf-8'))
for entry in data['icons']:
    if entry['id']=='swordMastery':
        entry['prompt']=revision['prompt'];entry['generated_source']=revision['generated_source'];entry['revision']=2
manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
