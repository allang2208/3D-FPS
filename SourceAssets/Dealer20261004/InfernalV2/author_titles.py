"""Original Infernal Dealer display alphabet and nine English title masks.

Polygon lettering, bevels and flame guides are authored here, not taken from a
third-party font. This produces editable SVG/TTF sources and production textures;
it does not render the game or generate a preview.
"""
import json
import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]/'Saved/DealerInfernalV2/PythonPackages'))
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

OUT=ROOT/'Export'
OUT.mkdir(parents=True,exist_ok=True)

# Sharp, inscription-like capitals. The variable stem weight, spear serifs and
# broken-corner bowls form a deliberately readable, original demonic display face.
STROKES={
 'A':[[(0,1),(.31,0),(.62,1)],[(.12,.62),(.5,.62)]],
 'B':[[(0,1),(0,0),(.42,0),(.62,.14),(.62,.35),(.42,.49),(0,.49)],[(.42,.49),(.64,.62),(.64,.84),(.42,1),(0,1)]],
 'C':[[(.62,.12),(.46,0),(.16,0),(0,.18),(0,.82),(.16,1),(.46,1),(.62,.88)]],
 'D':[[(0,1),(0,0),(.36,0),(.62,.19),(.62,.81),(.36,1),(0,1)]],
 'E':[[(.62,0),(0,0),(0,1),(.62,1)],[(0,.49),(.48,.49)]],
 'F':[[(.62,0),(0,0),(0,1)],[(0,.49),(.49,.49)]],
 'G':[[(.62,.12),(.46,0),(.16,0),(0,.18),(0,.82),(.16,1),(.46,1),(.62,.85),(.62,.53),(.34,.53)]],
 'H':[[(0,0),(0,1)],[(.62,0),(.62,1)],[(0,.49),(.62,.49)]],
 'I':[[(.31,0),(.31,1)],[(.11,0),(.51,0)],[(.11,1),(.51,1)]],
 'J':[[(.15,0),(.62,0),(.62,.82),(.43,1),(.15,1),(0,.84)]],
 'K':[[(0,0),(0,1)],[(.62,0),(0,.54),(.62,1)]],
 'L':[[(0,0),(0,1),(.62,1)]],
 'M':[[(0,1),(0,0),(.31,.53),(.62,0),(.62,1)]],
 'N':[[(0,1),(0,0),(.62,1),(.62,0)]],
 'O':[[(.16,0),(.46,0),(.62,.18),(.62,.82),(.46,1),(.16,1),(0,.82),(0,.18),(.16,0)]],
 'P':[[(0,1),(0,0),(.43,0),(.62,.18),(.62,.36),(.43,.53),(0,.53)]],
 'Q':[[(.16,0),(.46,0),(.62,.18),(.62,.82),(.46,1),(.16,1),(0,.82),(0,.18),(.16,0)],[(.37,.76),(.7,1.12)]],
 'R':[[(0,1),(0,0),(.43,0),(.62,.18),(.62,.36),(.43,.53),(0,.53)],[(.31,.53),(.65,1)]],
 'S':[[(.62,.13),(.47,0),(.16,0),(0,.18),(0,.34),(.17,.49),(.46,.49),(.62,.66),(.62,.82),(.46,1),(.15,1),(0,.87)]],
 'T':[[(0,0),(.62,0)],[(.31,0),(.31,1)]],
 'U':[[(0,0),(0,.82),(.16,1),(.46,1),(.62,.82),(.62,0)]],
 'V':[[(0,0),(.31,1),(.62,0)]],
 'W':[[(0,0),(.13,1),(.31,.56),(.49,1),(.62,0)]],
 'X':[[(0,0),(.62,1)],[(.62,0),(0,1)]],
 'Y':[[(0,0),(.31,.49),(.62,0)],[(.31,.49),(.31,1)]],
 'Z':[[(0,0),(.62,0),(0,1),(.62,1)]],
 '0':[[(.15,0),(.46,0),(.62,.17),(.62,.83),(.46,1),(.15,1),(0,.83),(0,.17),(.15,0)]],
 '1':[[(.06,.18),(.3,0),(.3,1)],[(.07,1),(.57,1)]],
 '2':[[(0,.18),(.16,0),(.46,0),(.62,.18),(.62,.35),(0,1),(.62,1)]],
 '3':[[(0,0),(.44,0),(.62,.18),(.62,.32),(.42,.49),(.18,.49)],[(.42,.49),(.62,.67),(.62,.82),(.44,1),(0,1)]],
 '4':[[(.46,1),(.46,0),(0,.68),(.64,.68)]],
 '5':[[(.62,0),(0,0),(0,.47),(.44,.47),(.62,.64),(.62,.84),(.44,1),(0,1)]],
 '6':[[(.56,0),(.16,0),(0,.18),(0,.84),(.16,1),(.46,1),(.62,.84),(.62,.66),(.46,.49),(0,.49)]],
 '7':[[(0,0),(.62,0),(.15,1)]],
 '8':[[(.16,0),(.46,0),(.62,.16),(.62,.33),(.46,.5),(.16,.5),(0,.33),(0,.16),(.16,0)],[(.16,.5),(0,.68),(0,.84),(.16,1),(.46,1),(.62,.84),(.62,.68),(.46,.5)]],
 '9':[[(.62,.5),(.16,.5),(0,.33),(0,.17),(.16,0),(.46,0),(.62,.17),(.62,.83),(.46,1),(.06,1)]],
 '.':[[(.26,.92),(.26,1)]],
}


def glyph_polygons(char):
    polygons=[]
    for stroke in STROKES.get(char,[]):
        for i,(a,b) in enumerate(zip(stroke,stroke[1:])):
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            # Vertical stems carry more weight than crossbars.
            width=.060 if abs(dy)>abs(dx)*1.2 else .043
            nx,ny=-dy/length*width,dx/length*width
            polygons.append([(a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),(b[0]-nx,b[1]-ny),(a[0]-nx,a[1]-ny)])
        for x,y in stroke:
            r=.046
            polygons.append([(x-r,y),(x,y-r),(x+r,y),(x,y+r)])
        for x,y in [stroke[0],stroke[-1]]:
            if y<.12:
                polygons.append([(x-.115,y+.05),(x+.105,y+.05),(x+.14,y-.06),(x,y-.025),(x-.14,y-.09)])
            elif y>.88:
                polygons.append([(x-.10,y-.04),(x+.10,y-.04),(x+.14,y+.06),(x-.14,y+.06),(x-.12,y+.10)])
    return polygons


def advance(c):
    return .46 if c==' ' else .42 if c=='.' else .80


def measure(text,size):
    return sum(advance(c)*size for c in text)


def draw_text(image,text,center,y,size):
    d=ImageDraw.Draw(image)
    x=center-measure(text,size)/2+.09*size
    for c in text:
        for points in glyph_polygons(c):d.polygon([(x+px*size,y+py*size) for px,py in points],fill=255)
        x+=advance(c)*size


def author_font():
    alphabet=list(STROKES)
    glyph_order=['.notdef','space']+['uni%04X'%ord(c) for c in alphabet]
    fb=FontBuilder(1000,isTTF=True);fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({32:'space',**{ord(c):'uni%04X'%ord(c) for c in alphabet}})
    glyphs={};metrics={}
    for c,name in [(None,'.notdef'),(' ','space')]+list(zip(alphabet,glyph_order[2:])):
        pen=TTGlyphPen(None)
        for points in glyph_polygons(c):
            converted=[(round((x+.13)*900),round(900-y*900)) for x,y in points]
            area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(converted,converted[1:]+converted[:1]))
            if area>0:converted.reverse()
            pen.moveTo(converted[0])
            for p in converted[1:]:pen.lineTo(p)
            pen.closePath()
        glyphs[name]=pen.glyph();metrics[name]=(round((advance(c) if c else .8)*900),0)
    fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1050,descent=-200)
    fb.setupNameTable({'familyName':'Infernal Dealer','styleName':'Spear Serif','uniqueFontIdentifier':'FPSGAME.InfernalDealer.20261004.V2',
        'fullName':'Infernal Dealer Spear Serif','psName':'InfernalDealer-SpearSerif','version':'Version 2.000'})
    fb.setupOS2(sTypoAscender=1050,sTypoDescender=-200,usWinAscent=1050,usWinDescent=200)
    fb.setupPost();fb.save(str(ROOT/'InfernalDealer-SpearSerif.ttf'))
    paths=[]
    for i,c in enumerate(alphabet):
        x=(i%9)*110;y=(i//9)*150+20
        for points in glyph_polygons(c):
            points=' '.join(f'{x+px*100+18:.2f},{y+py*100:.2f}' for px,py in points)
            paths.append(f'<polygon points="{points}"/>')
    height=math.ceil(len(alphabet)/9)*150+20
    (ROOT/'InfernalDealer-Glyphs.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}"><g fill="#bf7332">'+''.join(paths)+'</g></svg>',encoding='utf-8')


def build_title_assets():
    author_font()
    project=ROOT.parents[2]
    entries=json.loads((project/'Content/ColdSteelData/enhancement.json').read_text(encoding='utf-8-sig'))['scrolls']
    effects=next(e['effects'] for e in entries if e['id']=='dealer')
    names=['HIGH CARD','ONE PAIR','TWO PAIR','THREE OF A KIND','STRAIGHT','FLUSH','FULL HOUSE','FOUR OF A KIND','STRAIGHT FLUSH']
    keys=['dealerHighCard','dealerPair','dealerTwoPair','dealerThree','dealerStraight','dealerFlush','dealerFullHouse','dealerFour','dealerStraightFlush']
    atlas=Image.new('RGBA',(3072,768));art=Image.new('RGBA',(3072,768))
    tiles=[]
    for index,(title,key) in enumerate(zip(names,keys)):
        glyph=Image.new('L',(1024,256))
        size=min(99,895/measure(title,1))
        draw_text(glyph,title,512,77,size)
        draw_text(glyph,'X'+f'{effects[key]:g}',512,196,41)
        # Fine incandescent bevel and restrained carved cracks never replace the solid readable stem.
        bevel=ImageChops.subtract(glyph,glyph.filter(ImageFilter.MinFilter(5)))
        flames=Image.new('L',glyph.size);fd=ImageDraw.Draw(flames)
        rng=random.Random(1429+index*113)
        pix=glyph.load()
        for x in range(78,945,13):
            top=next((y for y in range(64,182) if pix[x,y]>0),None)
            if top is None:continue
            height=rng.uniform(12,52)*(1.15 if index>=6 else .85)
            width=rng.uniform(3,7);bend=rng.uniform(-9,9)
            fd.polygon([(x-width,top+4),(x-width*.9,top-height*.25),(x+bend,top-height*.70),
                (x+bend+3,top-height),(x+width*.4,top-height*.45),(x+width,top+4)],fill=rng.randint(170,255))
        glow=glyph.filter(ImageFilter.GaussianBlur(3))
        mask=Image.merge('RGBA',(glyph,bevel,flames,glow))
        # The editable artist texture is glyph-only RGBA; no rectangular background or border.
        color=Image.new('RGBA',glyph.size)
        cp=color.load();gp=glyph.load();bp=bevel.load();fp=flames.load();ap=glow.load()
        for y in range(256):
            for x in range(1024):
                coverage=max(gp[x,y],fp[x,y]*.65,ap[x,y]*.30)
                if not coverage:continue
                edge=bp[x,y]/255
                if fp[x,y] and not gp[x,y]:rgb=(245,83+int(fp[x,y]*.3),15)
                else:rgb=(int(122+125*edge),int(48+155*edge),int(18+65*edge))
                cp[x,y]=(*rgb,int(coverage))
        ox,oy=(index%3)*1024,(index//3)*256
        atlas.paste(mask,(ox,oy));art.alpha_composite(color,(ox,oy))
        tiles.append({'index':index,'english':title,'multiplier':effects[key],'tier':max(0,index-5),'column':index%3,'row':index//3})
    atlas=atlas.resize((4096,1024),Image.Resampling.LANCZOS)
    art=art.resize((4096,1024),Image.Resampling.LANCZOS)
    atlas.save(OUT/'T_DealerInfernalMasks.png');art.save(OUT/'T_DealerInfernalTitles.png')
    (ROOT/'title-manifest.json').write_text(json.dumps({'columns':3,'rows':3,'atlas_size':[4096,1024],'author_tile_size':[1024,256],
        'mask_channels':{'R':'solid original glyph','G':'incandescent bevel','B':'flame anchor tongues','A':'soft glyph glow'},'titles':tiles},indent=2),encoding='utf-8')
    (ROOT/'author-receipt.json').write_text(json.dumps({'complete':True,'version':2,'english_titles':9,
        'textures':[str(OUT/'T_DealerInfernalMasks.png'),str(OUT/'T_DealerInfernalTitles.png')],
        'font':str(ROOT/'InfernalDealer-SpearSerif.ttf'),'original_alphabet':True,'background':False,'border':False,
        'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
    print('DEALER_INFERNAL_TITLES_AUTHORED titles=9 original_font=true background=false border=false')


if __name__=='__main__':build_title_assets()
