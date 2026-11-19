"""Localized marks on a 116 cm trestle table, in tabletop centimetres."""
from pathlib import Path

import numpy as np
from PIL import Image


out = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/Furniture'
out.mkdir(exist_ok=True, parents=True)
y, x = (np.mgrid[:1024,:1024]+.5)*(120./1024.)-60.
stain = np.zeros_like(x)
for cx,cy,radius,rotation,strength in ((-17,28,3.78,.8,.67), (27,4,4.08,-1.6,.56),
                                       (28,4.7,4.08,2.3,.18), (-22,-24,5.18,-.6,.55)):
    dx,dy = x-cx, y-cy
    phi = np.arctan2(dy,dx)+rotation
    r = np.hypot(dx,dy)
    boundary = radius+.10*np.sin(3*phi)+.06*np.cos(5*phi)
    edge = np.exp(-((r-boundary)/(.20+.065*np.sin(phi)))**2)
    broken = np.clip(.52+.65*np.cos(phi)+.27*np.sin(3*phi+.2),0.,1.)
    stain = np.maximum(stain,strength*edge*broken)

scuff = np.zeros_like(x)
for cx,cy,length,angle in ((12,-31,6.4,1.2),(14,-30,4.5,1.1),(-29,8,8.1,-.4),
                           (-30,8.3,4.,-.45),(17,28,4.5,2.21)):
    u = (x-cx)*np.cos(angle)+(y-cy)*np.sin(angle)
    v = (y-cy)*np.cos(angle)-(x-cx)*np.sin(angle)
    scuff = np.maximum(scuff, np.exp(-((v-.09*np.sin(u*.57))/.09)**2-(u/length)**4))

radius = np.hypot(x,y)
phi = np.arctan2(y,x)
contact = np.exp(-((radius-48.)/8.4)**2) * (.42+.23*np.sin(3*phi+.6)+.15*np.cos(5*phi))
fade = np.clip((58.-radius)/1.8, 0., 1.)
colour = 1.-fade*(.30*stain+.03*contact+.095*scuff)
roughness = .5+fade*(.13*stain-.16*contact+.105*scuff)
channels = np.stack((colour,roughness,np.zeros_like(colour)),axis=-1)
Image.fromarray(np.rint(255.*channels.clip(0.,1.)).astype(np.uint8)).save(out/'T_TavernTableWear.png')
