"""Switch only the two completed audio assets and their playback option."""
from pathlib import Path
import json

ROOT = Path('D:/FPS3D/FPSGAME')
HERE = Path(__file__).resolve().parent
receipt = json.loads((HERE/'import-receipt.json').read_text(encoding='utf-8'))
if len(receipt) != 2 or not all(row.get('saved') for row in receipt):
    raise RuntimeError('Both direct-video sounds must be saved before activation')
path = ROOT/'Content/ColdSteelData/bows.json'
data = json.loads(path.read_text(encoding='utf-8'))
bow = data['bow_dark']
base = '/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926/'
bow['bow_draw_sound'] = base+'S_BowVideoDirect_Draw.S_BowVideoDirect_Draw'
bow['bow_release_sound'] = base+'S_BowVideoDirect_Release.S_BowVideoDirect_Release'
bow['bow_audio_original_speed'] = 1
bow['bow_presentation_revision'] = max(20, bow.get('bow_presentation_revision', 0))
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
config = ROOT/'Config/DefaultGame.ini'
text = config.read_text(encoding='utf-8')
entry = '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926")'
if entry not in text:
    anchor = '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/AudioVideo20260926")'
    if anchor not in text:
        raise RuntimeError('Bow audio packaging anchor changed; preserve config for a scoped update')
    text = text.replace(anchor, anchor+'\n'+entry, 1)
    config.write_text(text, encoding='utf-8')
print('BOW_VIDEO_DIRECT_ACTIVATED revision='+str(bow['bow_presentation_revision']))
