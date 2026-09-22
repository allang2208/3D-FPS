"""Build editable shader source and package the generated UI icon."""
from pathlib import Path
import json
from PIL import Image

P=Path(__file__).resolve().parent
prefix=(P.parent/'RuneSwordSemanticGlow20260922/semantic_runes.hlsl').read_text(encoding='utf-8').split('// GOLD-RUNE-V1')[0]
(P/'spirit_burst.hlsl').write_text(prefix+(P/'spirit_burst_tail.hlsl').read_text(encoding='utf-8'),encoding='utf-8')
im=Image.open(P/'spirit_burst_generated.png').convert('RGBA')
subject=im.crop(im.getchannel('A').getbbox())
subject.thumbnail((840,840),Image.Resampling.LANCZOS)
canvas=Image.new('RGBA',(1024,1024),(0,0,0,0))
canvas.paste(subject,((1024-subject.width)//2,(1024-subject.height)//2))
canvas.save(P/'ue_frost_crystal_sword_blade_2_spirit_burst_rune.png')
(P/'production.json').write_text(json.dumps({
    'icon_mode':'built-in image_gen',
    'icon_source':'C:/Users/allan/.codex/generated_images/01a0c6c5-5fe4-7550-8c0f-abed299812e8/exec-06600840-f410-4506-a42c-d49393a84b3a.png',
    'icon_prompt':'icon_prompt.json',
    'mask':'/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_erosion_rune',
    'pattern':'existing erosion cracks plus three procedural diamond nodes and paired expanding waves',
    'colors_linear':{'BurstColor':[.40,.004,.92,1], 'InnerColor':[.015,.28,.80,1]},
    'scalars':{'BurstRate':.55,'BurstHalo':.70},
    'runtime_tests':'not run; user will test'
},indent=2),encoding='utf-8')
print('FROST_SPIRIT_ASSETS_AUTHORED')
