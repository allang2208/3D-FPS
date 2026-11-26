"""Offline comparison of the two gloves on identical M870 idle bone transforms."""
import gzip
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation

from native_glove_author import R, read, unit
from native_glove_review import Skin, component

W,H,S=440,278,2
palette=np.asarray([[122,106,77],[68,62,54],[84,76,62],[75,72,61],[130,117,87],[106,94,72]])
old=read(R/'Read/R4.json')
new=read(R/'ShotgunGloves.json')
new['bones']=old['bones']
clip=json.load(gzip.open(R/'Read/M870_poses.json.gz','rt'))
names=clip['names']
pose=component(clip['clips']['A_M870_idle']['local'][0],[names.index(n) if n in names else -1 for n in clip['parents']])
skins=[Skin(data,names,False) for data in [old,new]]
positions=[s.skin(pose) for s in skins]
out=Image.new('RGB',(W*2,H*2+66+198),(31,33,32))
draw=ImageDraw.Draw(out)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
for col,label in enumerate(['原手套','按原生手型修订']):
    draw.text((col*W+13,8),label,font=font,fill=(225,224,215))
for row,side in enumerate('lr'):
    def bone(key):
        return pose[names.index(key+'_'+side),:3,3]
    wrist=bone('hand')
    front=unit(bone('middle_01')-wrist)
    across=unit(bone('index_01')-bone('pinky_01'))
    dorsal=unit(np.cross(across,front))
    if side=='r':
        dorsal=-dorsal
    # The side carrying the hard pad gives the viewing hemisphere.
    gs=skins[1]
    pad=np.unique(gs.faces[gs.mats==3])
    near=pad[(gs.zones[pad]==side+'/palm')]
    if len(near) and np.dot(positions[1][near].mean(0)-wrist,dorsal)<0:
        dorsal=-dorsal
    sight=unit(.64*dorsal+.72*across+.16*front)
    horizontal=unit(front-sight*np.dot(front,sight))
    vertical=unit(np.cross(sight,horizontal))
    cam=np.stack([horizontal,vertical,sight],axis=1)
    proj=[(p-wrist)@cam for p in positions]
    indices=[np.array([z.startswith(side+'/') for z in s.zones]) for s in skins]
    # Frame both versions with one orthographic camera and scale.
    merged=np.vstack([xy[ids,:2] for xy,ids in zip(proj,indices)])
    center=(merged.min(0)+merged.max(0))/2
    scale=min((W-38)/np.ptp(merged[:,0]),(H-38)/np.ptp(merged[:,1]))
    for col,(s,px,ids) in enumerate(zip(skins,proj,indices)):
        img=Image.new('RGB',(W*S,H*S),(48,51,49))
        panel=ImageDraw.Draw(img)
        fs=s.faces[ids[s.faces].all(axis=1)]
        mats=s.mats[ids[s.faces].all(axis=1)]
        verts=px[fs]
        n=unit(np.cross(verts[:,1]-verts[:,0],verts[:,2]-verts[:,0]))
        n[n[:,2]<0]*=-1
        ndl=np.maximum(0,n@unit(np.array([-.36,-.4,.78])))
        colors=np.clip(palette[mats]*(.65+.58*ndl[:,None]),0,255).astype('uint8')
        points=np.rint(((px[:,:2]-center)*scale+[W/2,H/2])*S).astype(int)
        for i in np.argsort(verts[:,:,2].mean(axis=1)):
            panel.polygon([tuple(p) for p in points[fs[i]]],fill=tuple(colors[i]))
        out.paste(img.resize((W,H),Image.Resampling.LANCZOS),(col*W,38+row*(H+13)))
    draw.text((13,40+row*(H+13)),('左手' if side=='l' else '右手')+' · M870 待机',font=font,fill=(235,231,218))
# The fitted source and the held model use the same saved idle pose.
model=json.load(gzip.open(R.parents[1]/'M870SurfaceFit20261016/m870.json.gz','rt'))
gbones={}
for n,t in model['rest'].items():
    gbones[n]=dict(index=len(gbones),position=t[:3],axes=(Rotation.from_quat(t[3:7]).as_matrix()*np.array(t[7:])[None,:]).T)
gun=Skin(dict(positions=model['vertices'],weights=model['weights'],bones=gbones,triangles=model['faces'],
              triangle_materials=model['materials']),names,False)
gunpoints=gun.skin(pose)
gunfaces=gun.faces[gun.mats==4]
forward=unit(pose[names.index('WPN_FrontSight'),:3,3]-pose[names.index('WPN_RearSight'),:3,3])
sight=unit(np.array([1.,.18,.32]))
x=unit(-forward-sight*np.dot(-forward,sight))
y=unit(np.cross(x,sight))
if y[2]>0:y=-y
cam=np.stack([x,y,sight],axis=1)
hands=np.vstack(positions)@cam
center=(np.max(hands[:,:2],axis=0)+np.min(hands[:,:2],axis=0))*.5
for col,(s,pts) in enumerate(zip(skins,positions)):
    xy=np.vstack((pts,gunpoints))@cam
    f=np.concatenate((s.faces,gunfaces+len(pts)))
    m=np.concatenate((s.mats,np.full(len(gunfaces),len(palette))))
    tris=xy[f]
    n=unit(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]))
    n[n[:,2]<0]*=-1
    shades=np.clip(np.vstack((palette,[[65,68,70]]))[m]*(.65+.68*np.maximum(0,n@unit(np.array([-.3,-.6,.75])))[:,None]),0,255).astype('uint8')
    img=Image.new('RGB',(W*S,198*S),(48,51,49))
    canvas=ImageDraw.Draw(img)
    scale=min((W-22)/np.ptp(hands[:,0]),156/np.ptp(hands[:,1]))
    pixels=np.rint(((xy[:,:2]-center)*scale+[W/2,110])*S).astype(int)
    for i in np.argsort(tris[:,:,2].mean(1)):
        canvas.polygon([tuple(v) for v in pixels[f[i]]],fill=tuple(shades[i]))
    out.paste(img.resize((W,198),Image.Resampling.LANCZOS),(col*W,2*H+66))
draw.text((13,2*H+69),'双手持握 · 同一待机姿态',font=font,fill=(235,231,218))
out.save(R/'M870-idle-comparison.jpg',quality=92)
