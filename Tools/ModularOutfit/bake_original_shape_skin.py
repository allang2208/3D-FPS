"""Bake authored anatomical skin fields into the original hand UV atlas.

This creates material inputs, not an acceptance render. No donor mesh or
photographed skin is used; all fields are located from the original finger rig.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

ROOT=Path(globals().get('AUTHOR_ROOT','D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'))
SMOOTH_SKIN=bool(globals().get('SMOOTH_SKIN',False))
original=json.loads((ROOT/'M4_original.json').read_text())
shape=json.loads((ROOT/'M4_bare_shape.json').read_text())
P=np.asarray(shape['positions']);N=4096
colour=np.zeros((N,N,3),np.float32);normal=np.zeros_like(colour);surface=np.zeros((N,N,4 if SMOOTH_SKIN else 3),np.float32)
valid=np.zeros((N,N),bool)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)
def srgb(v):return np.where(v<=.0031308,v*12.92,1.055*np.maximum(v,0)**(1/2.4)-.055)
def anatomy(p,n,side,stem):
    frame=shape['anatomy'][side]
    palm_back=np.array(frame['dorsal']);q=p-frame['wrist']
    x=q@frame['forward'];y=q@frame['across']
    palmar=smooth(.15,.75,-(n@palm_back))
    crease=np.zeros(p.shape[:-1]);nail=crease.copy();white=crease.copy();cuticle=crease.copy()
    knuckle=crease.copy();height=crease.copy()
    if stem:
        rows=[r for r in frame['digits'] if r['digit']==stem]
        for row in rows:
            local=p-row['head'];along=local@row['axis'];across=local@row['across']
            back=np.array(row['dorsal']);dorsal=local@back;radius=row['radius']
            facing=smooth(.18,.72,n@back)
            radial=np.exp(-((across/(radius*1.35))**4))
            knuckle=np.maximum(knuckle,np.exp(-(along/.44)**2)*radial)
            # Transverse creases have a shallow central line and two softer folds.
            rings=np.exp(-(along/.036)**2)*.62
            rings+=np.exp(-((along-.10)/.032)**2)*.25
            rings+=np.exp(-((along+.105)/.036)**2)*.21
            crease=np.maximum(crease,rings*radial*(.4+.6*palmar))
            if row['segment']==3:
                t=along/row['length'];w=across/(radius*.73)
                ellipse=((t-.56)/.365)**4+w**4
                nail=(1-smooth(.88,1.06,ellipse))*facing*smooth(radius*.15,radius*.5,dorsal)
                white=nail*smooth(.78,.86,t)
                cuticle=np.exp(-((ellipse-1.04)/.12)**2)*facing*smooth(radius*.15,radius*.5,dorsal)
        height=.007*nail-.005*crease-.003*cuticle
    else:
        # Palm creases follow curved local anatomical lines rather than UV axes.
        extent=smooth(1.3,2.2,x)*(1-smooth(7.3,8.3,x))
        life=np.exp(-((y-(1.4-.05*(x-3.6)**2))/.046)**2)
        head=np.exp(-((x-(4.2+.18*y+.09*y*y))/.047)**2)
        heart=np.exp(-((x-(6.25-.12*y+.05*y*y))/.050)**2)
        crease=(.55*life+.6*head+.4*heart)*palmar*extent
        # A pair of faint wrist skin creases; no rolled leather cuff shading.
        contour=shape.get('wrist_contour',{}).get(side)
        if contour:
            wrist_y=q@contour['radial']-(x*contour['centre_slope'][0]+contour['centre_intercept'][0])
            span=1-smooth(1.45,2.25,np.abs(wrist_y))
            main=-.15+.07*wrist_y+.045*wrist_y*wrist_y
            second=.48-.045*wrist_y+.03*wrist_y*wrist_y
            crease+=palmar*span*(.30*np.exp(-((x-main)/.065)**2)+.16*np.exp(-((x-second)/.055)**2))
        else:
            crease+=palmar*.22*(np.exp(-((x-.3)/.05)**2)+np.exp(-((x-.65)/.04)**2))
        for row in frame['digits']:
            if row['segment']==1:
                knuckle=np.maximum(knuckle,np.exp(-np.sum((p-row['head'])**2,axis=-1)/.75)*(1-palmar))
        height=-.0045*crease
    crease=np.clip(crease,0,1)
    # Position-based tone is continuous across the original split UV islands.
    blotch=(np.sin(p[...,0]*2.3+p[...,1]*1.8)*np.sin(p[...,2]*2.7+p[...,0]*.8))*.5
    fine=np.sin(p[...,0]*19+p[...,1]*13)*np.sin(p[...,2]*23-p[...,0]*11)*.5
    skin=np.array([.36,.235,.185])*(1+blotch[...,None]*.04+fine[...,None]*.012)
    skin+=palmar[...,None]*np.array([.020,.012,.009])
    skin+=knuckle[...,None]*np.array([.015,-.002,-.003])
    # Fade variation into the already accepted exposed-forearm skin at the wrist.
    join=1-smooth(-.8,1.5,x)
    wrist=np.array([.372,.232,.182])
    skin=skin*(1-join[...,None])+wrist*join[...,None]
    vein=(np.exp(-((y-(.6+np.sin(x*.65)*.30))/.08)**2)+
          np.exp(-((y-(-.55+np.sin(x*.55+1)*.22))/.09)**2))
    vein*=smooth(1,2,x)*(1-smooth(5.7,6.8,x))*(1-palmar)*(not bool(stem))
    skin+=vein[...,None]*np.array([-.008,-.001,.001])
    skin*=1-crease[...,None]*.10
    nail_colour=np.broadcast_to(np.array([.50,.335,.285]),skin.shape).copy()
    nail_colour=nail_colour*(1-white[...,None]*.48)+np.array([.67,.595,.49])*white[...,None]*.48
    skin=skin*(1-nail[...,None])+nail_colour*nail[...,None]
    skin+=cuticle[...,None]*np.array([.004,-.007,-.006])
    rough=.49-.04*palmar-.16*nail+.02*crease+.015*blotch
    if SMOOTH_SKIN:
        # Keep anatomical creases shallow after removing the old glove relief.
        height*=.55
        return np.clip(skin,0,1),np.stack((nail,np.clip(rough,0,1),crease,palmar),axis=-1),height
    return np.clip(skin,0,1),np.stack((nail,np.clip(rough,0,1),crease),axis=-1),height

for ti,(ids,mat) in enumerate(zip(original['triangles'],shape['triangle_materials'])):
    if mat!=2:continue
    points=P[ids];normals=np.asarray(shape.get('normals',original['normals'])[ti])
    uv=np.asarray(original['uv'][ti]);pts=uv*(N-1);a,b,c=pts
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-8:continue
    lo=np.maximum(0,np.floor(pts.min(axis=0)).astype(int));hi=np.minimum(N-1,np.ceil(pts.max(axis=0)).astype(int))
    if np.any(hi<lo):continue
    yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
    wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;wc=1-wa-wb
    mask=(wa>=-.001)&(wb>=-.001)&(wc>=-.001)
    if not mask.any():continue
    bc=np.stack((wa,wb,wc),axis=-1);p=bc@points;n=unit(bc@normals)
    side='l' if points[:,0].mean()<0 else 'r'
    strengths={stem:sum(sum(w for name,w in original['weights'][i].items() if name.startswith(stem+'_') and '_metacarpal_' not in name) for i in ids)/3 for stem in ('thumb','index','middle','ring','pinky')}
    stem=max(strengths,key=strengths.get)
    if strengths[stem]<.35:stem=None
    rgb,fields,h=anatomy(p,n,side,stem)
    # Original UV tangent basis, with skin relief in physical centimetres.
    duv1=uv[1]-uv[0];duv2=uv[2]-uv[0]
    det=duv1[0]*duv2[1]-duv1[1]*duv2[0]
    dpdu=((points[1]-points[0])*duv2[1]-(points[2]-points[0])*duv1[1])/det
    dpdv=(-(points[1]-points[0])*duv2[0]+(points[2]-points[0])*duv1[0])/det
    t=unit(dpdu-n*np.sum(n*dpdu,axis=-1,keepdims=True));bt=unit(np.cross(n,t))
    bt*=np.where(np.sum(bt*dpdv,axis=-1,keepdims=True)>=0,1,-1)
    hu=np.gradient(h,axis=1)*(N-1) if h.shape[1]>1 else np.zeros_like(h)
    hv=np.gradient(h,axis=0)*(N-1) if h.shape[0]>1 else np.zeros_like(h)
    g00=dpdu@dpdu;g01=dpdu@dpdv;g11=dpdv@dpdv;gdet=max(g00*g11-g01*g01,1e-10)
    gu=(g11*hu-g01*hv)/gdet;gv=(g00*hv-g01*hu)/gdet
    bumped=unit(n-dpdu*gu[...,None]-dpdv*gv[...,None])
    tangent=np.stack((np.sum(bumped*t,axis=-1),np.sum(bumped*bt,axis=-1),np.sum(bumped*n,axis=-1)),axis=-1)
    rect=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1))
    colour[rect][mask]=rgb[mask];surface[rect][mask]=fields[mask];normal[rect][mask]=tangent[mask]
    valid[rect]|=mask

# Sixteen-pixel island dilation is authoring for filtered sampling and LODs.
distance,nearest=distance_transform_edt(~valid,return_indices=True)
padding=(~valid)&(distance<=16)
for tex in (colour,normal,surface):tex[padding]=tex[nearest[0][padding],nearest[1][padding]]
colour[~(valid|padding)]=[.36,.235,.185]
normal[~(valid|padding)]=[0,0,1];surface[~(valid|padding)]=[0,.49,0,0] if SMOOTH_SKIN else [0,.49,0]
Image.fromarray(np.uint8(np.clip(srgb(colour)*255+.5,0,255))).save(ROOT/'T_M4OriginalShape_SkinColour.png')
Image.fromarray(np.uint8(np.clip((normal*.5+.5)*255+.5,0,255))).save(ROOT/'T_M4OriginalShape_SkinNormal.png')
Image.fromarray(np.uint8(np.clip(surface*255+.5,0,255))).save(ROOT/'T_M4OriginalShape_SkinSurface.png')
(ROOT/'texture_source.json').write_text(json.dumps({'source':'Locally authored procedural skin on original Manny UV; no human scan or donor geometry',
 'size':N,'colour':'sRGB; original forearm tint matched; anatomical nails and palm/knuckle tones',
 'normal':'DirectX; original UV tangent basis; shallow nail/cuticle/palm relief',
 'surface':{'R':'nail','G':'roughness','B':'skin crease',**({'A':'palmar skin'} if SMOOTH_SKIN else {})},'generated_preview':False},indent=2))
print('ORIGINAL_SHAPE_SKIN_MAPS_BAKED',N)
