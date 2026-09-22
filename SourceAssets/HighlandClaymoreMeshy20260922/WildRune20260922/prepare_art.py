"""Author the code-defined six-fang rune mask and package the generated UI icon."""
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

P = Path(__file__).resolve().parent
for folder in ['Textures', 'Icons', 'Generated']:
    (P / folder).mkdir(exist_ok=True)
W, H, S = 512, 2048, 2
mask = Image.new('L', (W*S, H*S), 0)
draw = ImageDraw.Draw(mask)
# Authored polygons form a broken spine and paired hooked fangs. This is a
# material coverage asset, independent of the semantic inventory illustration.
spine = [(0,-.40),(.065,-.19),(.030,.02),(.048,.19),(0,.36),(-.036,.19),(-.022,-.10),(-.055,-.18)]
fang = [(-.032,-.085),(-.145,-.18),(-.295,-.13),(-.415,-.28),(-.290,.055),(-.120,.115),(-.048,.055)]
lower = [(-.04,.17),(-.13,.14),(-.25,.205),(-.29,.10),(-.27,.295),(-.13,.245)]
centers = [.105,.264,.423,.582,.741,.900]
for i, cy in enumerate(centers):
    span = .148 * (1.0 if i not in [0,5] else .88)
    width = .92 if i % 2 == 0 else .80
    paths = [spine, fang, [(-x,y) for x,y in fang], lower, [(-x,y) for x,y in lower]]
    for j, path in enumerate(paths):
        pts = [((.5+x*width)*W*S,(cy+y*span)*H*S) for x,y in path]
        draw.polygon(pts, fill=255 if j==0 else 225 if j<3 else 170)
    # Short separated fractures soften the rigid-line impression.
    for sign in [-1,1]:
        pts = [(sign*.13,-.32),(sign*.19,-.37),(sign*.235,-.31),(sign*.18,-.335)]
        draw.polygon([((.5+x)*W*S,(cy+y*span)*H*S) for x,y in pts], fill=150)
mask = mask.filter(ImageFilter.GaussianBlur(1.3*S)).resize((W,H), Image.Resampling.LANCZOS)
coverage = np.asarray(mask, dtype=np.float32)/255.
yy, xx = np.mgrid[0:H,0:W].astype(np.float32)
grain = .93+.045*np.sin(xx*.077+yy*.018)+.025*np.sin(yy*.14-xx*.052)
coverage *= np.clip(grain, .83, 1.)
Image.fromarray(np.uint8(np.clip(coverage*255.,0,255))).save(P/'Textures/T_Mask_wild_rune.png')

source = Path(r'C:\Users\allan\.codex\generated_images\01a0c6c5-5fe4-7550-8c0f-abed299812e8\exec-a247becb-7282-4494-9e09-7be1bba72486.png')
raw = P/'Generated/wild_rune_semantic.png'
shutil.copy2(source,raw)
im = Image.open(raw).convert('RGBA')
box = im.getchannel('A').getbbox()
if not box or im.getchannel('A').getextrema()[0]!=0:
    raise RuntimeError('Generated icon needs true transparency before packaging.')
subject = im.crop(box)
subject.thumbnail((840,840), Image.Resampling.LANCZOS)
canvas = Image.new('RGBA',(1024,1024),(0,0,0,0))
canvas.paste(subject,((1024-subject.width)//2,(1024-subject.height)//2))
icon_name = 'ue_highland_claymore_blade_2_wild_rune.png'
canvas.save(P/'Icons'/icon_name)
production = {
    'weapon':'ue_highland_claymore','option':'wild_rune','name':'蛮荒符文',
    'icon':icon_name,'generated_icon':str(source),'icon_generator':'Built-in imagegen',
    'mask':'Textures/T_Mask_wild_rune.png','mask_size':[W,H],
    'pattern':'Six segmented hooked fang glyphs, broken central spine, feathered coverage',
    'colors_linear':{'WildCoreColor':[.36,.012,.007,1],'WildGlowColor':[1,.026,.007,1]},
    'scalars':{'WildPulseSpeed':1.85,'EmissionPeak':2.3,'RuneOpacity':.80,
               'HaloOpacity':.19,'HaloRadiusTexels':3.5},
    'stats':{'toughness_damage_mult':1.3,'physical_armor_penetration':.2},
    'tested':False}
(P/'production.json').write_text(json.dumps(production,ensure_ascii=False,indent=2),encoding='utf-8')
print('HIGHLAND_WILD_RUNE_ART_READY')
