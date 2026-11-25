"""Bake eight narrow hair locks and a continuous, parted undercoat for the mounted view."""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def bake(out):
    rng = random.Random(292)
    width, height, scale = 2048, 1536, 2
    lock_width = 192
    canvas = Image.new('RGBA', (width*scale, height*scale), (40, 31, 27, 0))
    draw = ImageDraw.Draw(canvas)
    for group in range(8):
        for strand in range(126):
            root = rng.triangular(.06, .94, .50)
            fan = rng.uniform(-.17, .17)
            length = rng.uniform(.52, .99)
            shade = rng.uniform(.66, 1.32)
            curl = rng.uniform(-.032, .032)
            previous = None
            for j in range(33):
                t = j/32
                u = root + fan*t + curl*math.sin(t*4+group)*t
                tip = ((group+max(.012,min(.988,u)))*lock_width*scale, t*length*(height-1)*scale)
                if previous:
                    value = (.84+.16*math.sin(t*math.pi))*shade
                    color = tuple(round(c*value) for c in (47, 36, 30))+(round(250-65*t**5),)
                    draw.line((previous,tip), fill=color, width=max(1,round((1.40-.97*t)*scale)))
                previous=tip
    image = canvas.resize((width,height), Image.Resampling.LANCZOS)
    # A longitudinal drift, a wandering parting and non-periodic filaments.
    # The undercoat is continuous beneath the loose cards even in grazing light.
    w=width-8*lock_width
    y,x=np.mgrid[:height,:w].astype(float)
    part=w*(.49+.072*np.sin(y/157)+.036*np.sin(y/61+.4))
    dist=(x-part)/w
    stream=y+height*(.195*abs(dist)**1.25+.085*dist)+7*np.sin(y/133+dist*6)
    noise=np.random.default_rng(174)
    def filaments(coord, spacing):
        values=noise.normal(0,1,2600)
        return np.interp((coord/spacing)%2599,np.arange(len(values)),values)
    light=1+.11*filaments(stream,2.7)+.061*filaments(stream,8.4)+.07*np.cos(9*dist+.005*y)
    light-=.08*np.exp(-(dist/.075)**2)
    color=np.clip(light[:,:,None]*np.array([46,35,29]),0,255).astype(np.uint8)
    under=Image.fromarray(color,'RGB').convert('RGBA')
    image.paste(under,(8*lock_width,0))
    image.save(out/'T_Warhorse_Mane.png')


if __name__=='__main__':
    bake(Path(sys.argv[-1]))
