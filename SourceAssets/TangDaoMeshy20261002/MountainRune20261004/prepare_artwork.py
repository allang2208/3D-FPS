"""Pack generated alpha as a linear shader mask; retain original artwork."""
from pathlib import Path
import json, shutil
from PIL import Image

P=Path(__file__).resolve().parent
GENERATED=Path('C:/Users/allan/.codex/generated_images/01a10038-a50d-7210-964d-929131b424d2')
for folder in ('Artwork','Icons','Records'): (P/folder).mkdir(parents=True,exist_ok=True)
inputs={
    'icon':'exec-05e38a7a-b3ff-4a28-a470-acfd41457027.png',
    'mask':'exec-8ba2ea98-709e-4ce7-8b5e-2814e23cd697.png',
}
shutil.copy2(GENERATED/inputs['icon'],P/'Icons/ue_tang_dao_blade_2_mountain_rune.png')
shutil.copy2(GENERATED/inputs['mask'],P/'Artwork/MountainRune_Alpha.png')
art=Image.open(P/'Artwork/MountainRune_Alpha.png').convert('RGBA')
alpha=art.getchannel('A')
if alpha.getextrema()[0]==alpha.getextrema()[1]:
    raise RuntimeError('Source alpha has no rune coverage; cannot pack a usable mask')
alpha.save(P/'Artwork/TangDao_MountainRune_Mask.png')
# Reuse the authored projection and envelope, with a mountain-only palette.
code=(P.parent/'CloudRune20261002/cloud_emission.hlsl').read_text(encoding='utf-8')
code=code.replace('TangDao mode 6: a retained warm cloud seal with a soft jade current.',
                  'TangDao mode 7: ochre mountain strata and a restrained amber mineral pulse.')
code=code.replace('RuneMode > 5.5 && RuneMode < 6.5','RuneMode > 6.5 && RuneMode < 7.5')
code=code.replace('lerp(.30, .70,','lerp(.22, .78,')
code=code.replace('float3(.72, .49, .20)','float3(.64, .36, .075)')
code=code.replace('float3(.22, .68, .50)','float3(.92, .57, .15)')
code=code.replace('time * .82','time * .46').replace('time * .68','time * .44')
code=code.replace('goldInk','ochreInk').replace('jadeLight','amberLight')
code=code.replace('cloud','mountain').replace('seal remains','rock strata remain')
(P/'mountain_emission.hlsl').write_text(code,encoding='utf-8')
(P/'Records/artwork.json').write_text(json.dumps({
    'tool':'built-in image_gen','inputs':inputs,'texture_size':art.size,
    'mask_encoding':'original alpha channel as linear grayscale; shape unchanged',
    'icon_style':'neutral grayscale mountain relief, approved steel frame',
    'blade_palette':'ochre ink and restrained amber pulse',
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('MOUNTAIN_ARTWORK_PACKED',art.size,flush=True)
