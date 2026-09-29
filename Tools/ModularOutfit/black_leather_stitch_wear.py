"""Final needle seating, panel corners and restrained wear on the V3 glove."""
import shutil
import numpy as np
import black_leather_tailored_surface as previous
from black_leather_tailored_surface import *

V3=previous.R
R=V1/'StitchWearV4'


def stitch_run(distance,arc,pitch=.25,width=.023):
    s=np.mod(arc,pitch)-pitch*.5
    ratio=pitch/.25
    stroke=1-smooth(.058*ratio,.085*ratio,np.abs(s))
    yarn=gauss(distance,0,width)*stroke
    ends=gauss(s,-.081*ratio,.018*ratio)+gauss(s,.081*ratio,.018*ratio)
    hole=np.clip(gauss(distance,0,.023)*ends,0,1)
    variation=.88+.12*np.sin(np.floor(arc/pitch)*1.91+.4)
    arch=.012+.005*(1-smooth(.016*ratio,.065*ratio,np.abs(s)))
    bed=gauss(distance,0,.048)
    fine=yarn*arch*variation-.012*hole-.0035*bed
    rub=gauss(np.abs(distance),.073,.036)*(.55+.45*stroke)
    return dict(thread=yarn,hole=hole,fine=fine,rub=rub)


def back_pattern(x,y):
    shape=(np.abs((x+.55)/3.48)**4+np.abs((y-4.55)/3.35)**4)**.25
    signed=(shape-1)*3.3
    panel=1-smooth(-.07,.08,signed)
    low=.075*(1-smooth(-.45,-.05,signed))
    rim=gauss(signed,-.055,.045)
    phase=np.arctan2((y-4.55)/3.35,(x+.55)/3.48)*3.4
    thread=np.zeros_like(x);hole=np.zeros_like(x);rub=np.zeros_like(x)
    fine=.020*rim;bed=np.zeros_like(x)
    for center in (-.22,-.40):
        row=stitch_run(signed-center,phase)
        thread=np.maximum(thread,row['thread']);hole=np.maximum(hole,row['hole'])
        rub=np.maximum(rub,row['rub']);fine+=row['fine'];bed+=gauss(signed,center,.048)
    crease=np.zeros_like(x)
    for line in [[(-3.55,2.1),(-2.85,4.3),(-2.2,6.8)],
                 [(2.4,2.1),(1.8,4.3),(1.2,6.8)],
                 [(-2.8,6.95),(-1.1,7.50),(.5,7.55),(1.9,7.10)]]:
        distance,arc=polyline(x,y,line);groove=gauss(distance,0,.060)
        crease=np.maximum(crease,groove);fine-=.017*groove
        row=stitch_run(distance-.17,arc,.27,.023)
        fine+=row['fine'];thread=np.maximum(thread,row['thread'])
        hole=np.maximum(hole,row['hole']);rub=np.maximum(rub,row['rub']*.70)
    sd=rectangle(x,y,-.25,-1.28,3.10,.85,.28)
    strap=1-smooth(-.04,.04,sd);low+=.070*(1-smooth(-.32,-.04,sd))
    border=gauss(sd,-.11,.036)
    row=stitch_run(sd+.11,x+2*y,.25,.025)
    thread=np.maximum(thread,row['thread']);hole=np.maximum(hole,row['hole'])
    fine+=.010*border+row['fine'];rub=np.maximum(rub,row['rub']*.8)
    label_sd=rectangle(x,y,-.55,2.45,.83,.75,.17)
    label=1-smooth(-.03,.04,label_sd);low+=.027*label
    label_phase=np.arctan2((y-2.45)/.75,(x+.55)/.83)*.80
    row=stitch_run(label_sd+.065,label_phase,.20,.020)
    thread=np.maximum(thread,row['thread']*.85);hole=np.maximum(hole,row['hole']*.70)
    fine+=row['fine']*.70
    crest=np.zeros_like(x)
    for line in [[(-.98,2.18),(-.55,2.76),(-.12,2.18)],
                 [(-.87,2.07),(-.55,2.48),(-.23,2.07)],
                 [(-.99,2.88),(-.11,2.88)]]:
        distance,_=polyline(x,y,line);crest=np.maximum(crest,gauss(distance,0,.043))
    crest*=label;fine+=.017*crest
    folds=gauss(y,.70+.20*np.sin(x*1.8),.09)*gauss(x,0,2.7)
    folds+=gauss(y,.30+.16*np.sin(x*2.1),.075)*gauss(x,.2,2.4)
    fine-=.012*folds
    # Small asymmetric edge tucks, sculpted in the high-poly only. The game
    # outline, contact envelope and accepted low panels stay exactly V3.
    corners=gauss(x,-3.05,.52)*gauss(y,2.18,.48)
    corners+=.72*gauss(x,1.98,.46)*gauss(y,7.10,.44)
    stack=gauss(signed,-.15,.16)*corners
    fine+=.026*stack+.004*stack*np.sin((x+y)*19)
    rub=np.clip(rub*.48+rim*.28+stack*.40,0,1)
    wear=np.clip(.32*rim+.30*crease+.28*border+.20*folds+.25*rub,0,1)
    cavity=np.clip(.10*bed+.24*hole+.20*crease+.17*folds,0,.62)
    return dict(low=low,fine=fine,thread=np.clip(thread,0,1),panel=panel,
                cloth=np.maximum(label,strap*.72),crest=crest,wear=wear,cavity=cavity,
                hole=hole,rub=rub,stack=stack)


def palm_pattern(x,y):
    sd=rectangle(x,y,-1.05,4.75,2.65,2.65,.80)
    panel=1-smooth(-.05,.05,sd)
    phase=np.arctan2(y-4.75,x+1.05)*2.65
    row=stitch_run(sd+.15,phase,.27,.024)
    crease=np.zeros_like(x)
    for line in [[(2.3,2.0),(1.45,3.1),(.1,4.05),(-2.4,4.25)],
                 [(2.6,2.35),(1.8,4.35),(1.0,6.2)],
                 [(-3.0,6.55),(-1.6,6.10),(.3,6.2),(1.7,6.8)]]:
        d,_=polyline(x,y,line);crease=np.maximum(crease,gauss(d,0,.065))
    fine=row['fine']-.020*crease
    return dict(panel=panel,thread=row['thread'],crease=crease,fine=fine,
                hole=row['hole'],rub=row['rub']*.55)


def finger_detail(arc,seam):
    a=stitch_run(seam+.10,arc);b=stitch_run(seam-.09,arc)
    return dict(thread=np.maximum(a['thread'],b['thread']),hole=np.maximum(a['hole'],b['hole']),
                fine=a['fine']+b['fine']-.004*gauss(seam,0,.05),rub=np.maximum(a['rub'],b['rub'])*.5)


# design_fields uses the unchanged coarse construction plus V4 fine fields.
base.back_pattern=back_pattern
base.palm_pattern=palm_pattern


def prepare():
    R.mkdir(parents=True,exist_ok=True)
    recipe=read(P/'Content/ColdSteelData/modular_outfits.json')['items']['ue_field_gloves_black']
    if recipe!=read(V3/'published.json')['recipe'] and recipe.get('appearance_family')!='BlackLeatherStitchWearV4':
        raise RuntimeError('Black glove appearance changed outside this authoring revision')
    if not (R/'before-recipe.json').exists():write(R/'before-recipe.json',recipe)
    sources=read(V3/'native-sources.json');write(R/'native-sources.json',sources)
    (R/'Sources').mkdir(exist_ok=True)
    for name in sources:shutil.copy2(V3/'Sources'/(name+'.json'),R/'Sources'/(name+'.json'))
    print('STITCH_WEAR_V4_PREPARED',len(sources),flush=True)


if __name__=='__main__':prepare()
