"""Bake the boar's coat from the animal pack albedo, its UV layout and reference pose."""
from pathlib import Path
import argparse
import math
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt


def smooth(low, high, x):
    t = np.clip((x-low)/(high-low), 0, 1)
    return t*t*(3-2*t)


def surface_map(geometry, size=1536):
    xyz = geometry['p']
    uv = geometry['uv'].copy()
    uv[:, 1] = 1 - uv[:, 1]
    uv = uv * size - .5
    field = np.zeros((size, size, 3), np.float32)
    used = np.zeros((size, size), bool)
    # The pack reuses some UVs on the fur cards. Give the opaque skin priority.
    for i in np.argsort(-geometry['mats'], kind='stable'):
        a, b, c = uv[geometry['loop'][i]]
        x0, y0 = np.maximum(0, np.floor(np.minimum(np.minimum(a, b), c)).astype(int))
        x1, y1 = np.minimum(size-1, np.ceil(np.maximum(np.maximum(a, b), c)).astype(int))
        ab, ac = b-a, c-a
        det = ab[0]*ac[1] - ab[1]*ac[0]
        if abs(det) < .00001 or x1 < x0 or y1 < y0:
            continue
        yy, xx = np.ogrid[y0:y1+1, x0:x1+1]
        v = ((xx-a[0])*ac[1]-(yy-a[1])*ac[0])/det
        w = (ab[0]*(yy-a[1])-ab[1]*(xx-a[0]))/det
        inside = (v>=0) & (w>=0) & (v+w<=1)
        p, q, r = xyz[geometry['tri'][i]]
        patch = field[y0:y1+1, x0:x1+1]
        patch[inside] = p + v[inside,None]*(q-p) + w[inside,None]*(r-p)
        used[y0:y1+1, x0:x1+1] |= inside
    near = distance_transform_edt(~used, return_distances=False, return_indices=True)
    return field[tuple(near)]


def coat(base, geometry, dest):
    img = np.asarray(Image.open(base).convert('RGBA'))
    h, w = img.shape[:2]
    field = surface_map(np.load(geometry))
    lum = cv2.transform(img[:,:,:3], np.array([[.28,.57,.15]], np.float32))
    local = cv2.GaussianBlur(lum, (0,0), 2.2)
    field = cv2.resize(field,(w,h),interpolation=cv2.INTER_LINEAR)
    result = img.copy()
    for start in range(0,h,128):
        s = slice(start,min(start+128,h))
        x, y, z = np.moveaxis(field[s],-1,0)
        l = lum[s].astype(np.float32)/255.
        detail = (lum[s].astype(np.float32)-local[s])/255.
        # A broad cool saddle feathers out below the crest. Cheeks and flanks are
        # warmer, the lower legs and the muzzle have shorter, darker hair.
        saddle = np.exp(-(x/(.082+.077*np.exp(-((y+.34)/.58)**2)))**2)*smooth(.59,.90,z)
        face = smooth(.73,1.10,-y)
        feet = 1.-smooth(.08,.32,z)
        ear = smooth(.64,.77,z)*smooth(.58,.72,-y)
        v = .038+.56*l**1.18+.68*detail
        v *= 1. - .29*saddle-.16*feet-.16*face
        wave = 2.*np.sin(13*y+5*z)+.54*np.sin(39*y+8*x)
        side_phase = 1850*(z-.42*y+.20*y*y+.19*x)+wave
        top_phase = 1990*(abs(x)+.07*y+.045*np.sin(8*y))+wave
        top = np.exp(-(x/.16)**2)*smooth(.65,.9,z)
        grain = (1-top)*np.sin(side_phase)+top*np.sin(top_phase)
        v += .010*grain*(.44+.56*np.cos(65*y+98*z)**2)*(1-.55*face)
        warm = 1.-.48*saddle-.28*face
        rgb = np.stack((v*(1+.102*warm),v*(.957+.018*saddle),v*(.828+.074*saddle)),axis=-1)
        # Leave a muted umber at the ears so their thin skin remains distinct.
        rgb[:,:,0] += .014*ear
        # Follow the mirrored eye islands in reference-pose centimetres. A dark
        # upper rim and a warm umber iris leave the original black pupil legible.
        dx, dy, dz = 100*abs(x)-9.8, -100*y-99.45, 100*z-54.1
        along, depth = .84*dx-.54*dy, .54*dx+.84*dy
        plane = np.exp(-(depth/2.6)**2)
        lid = np.exp(-(along/4.1)**2-((dz-1.17-.12*along)/.83)**2)*plane
        socket = np.exp(-(along/5.1)**2-((dz-.9)/2.25)**2)*plane
        rgb *= (1.-.34*lid-.14*socket)[:,:,None]
        iris = (1.-smooth(.76,1.18,np.hypot(along/1.65,dz/1.17)))*plane
        pupil = 1.-smooth(.37,.66,np.hypot((along+.12)/1.30,dz/1.02))
        rgb += (iris*(1.-pupil))[:,:,None]*np.array([.18,.098,.036],np.float32)
        result[s,:,:3] = np.rint(np.clip(rgb,0,1)*255).astype(np.uint8)
    Image.fromarray(result).save(dest/'T_WL_BoarCoat.tga')


def mane_atlas(dest):
    rng = random.Random(94831)
    cols, cell, height, ss = 8, 128, 512, 3
    output = Image.new('RGBA',(cols*cell,height))
    for col in range(cols):
        tile = Image.new('RGBA',(cell*ss,height*ss))
        draw = ImageDraw.Draw(tile)
        for i in range(150):
            base = rng.uniform(-.04,1.04)
            tip = (.51+.48*rng.random())*(1.-.13*abs(2*base-1)**1.5)
            splay = rng.uniform(-.12,.12)+.09*(base-.5)
            curl = rng.uniform(-.065,.065)
            thick = rng.uniform(.42,1.20)
            shade = rng.uniform(-7,10)
            if rng.random()<.045:shade += 11
            def point(t,off):
                xx = base+splay*t+curl*math.sin(math.pi*t)
                return (int((xx*cell+off)*ss), int((t*tip*(height-1))*ss))
            for j in range(10):
                a,b = j/10,(j+1)/10
                aw,bw = thick*(1-a)**.70, thick*(1-b)**.70
                c = tuple(round(n+shade+11*a) for n in (53,45,38))
                draw.polygon([point(a,-aw),point(a,aw),point(b,bw),point(b,-bw)],fill=(*c,255))
        # Preserve colour under masked edges when generating engine mips.
        tile=tile.resize((cell,height),Image.Resampling.LANCZOS)
        pix=np.asarray(tile).copy()
        near=distance_transform_edt(pix[:,:,3]<16,return_distances=False,return_indices=True)
        pix[:,:,:3]=pix[tuple(near)][:,:,:3]
        output.paste(Image.fromarray(pix),(col*cell,0))
    output.save(dest/'T_WL_BoarMane.tga')


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('albedo',type=Path)
    p.add_argument('geometry',type=Path,help='Exported FBX reference pose and UV arrays')
    p.add_argument('destination',type=Path)
    args=p.parse_args()
    args.destination.mkdir(parents=True,exist_ok=True)
    coat(args.albedo,args.geometry,args.destination)
    mane_atlas(args.destination)
