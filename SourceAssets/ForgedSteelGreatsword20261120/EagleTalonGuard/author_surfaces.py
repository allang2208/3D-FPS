"""Author de-lit, registered metal maps plus an independent ice-inlay mask."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from talon_profile import ATLAS_SIZE, CHART_BORDER, CHART_SCALE

ART = Path(__file__).resolve().parent / 'Art'
SIZE = ATLAS_SIZE
rng = np.random.default_rng(221126)
source = np.asarray(Image.open(ART/'EagleTalon-Reference.png').convert('RGB'), dtype=np.float32)/255
grid_y,grid_x = np.mgrid[:SIZE,:SIZE].astype(np.float32)
chart_x = (grid_x-CHART_BORDER)/CHART_SCALE
chart_y = (grid_y-CHART_BORDER)/CHART_SCALE
image_x = 100+chart_x/1.6
image_y = 210+chart_y/1.6
front = chart_y < 595


def sample(x):
    return cv2.remap(source, x, image_y, cv2.INTER_CUBIC,
                     borderMode=cv2.BORDER_REPLICATE).clip(0,1)


def blur(field, sigma):
    return cv2.GaussianBlur(field, (0,0), sigma)


def noise(size):
    samples = rng.standard_normal((size,size)).astype(np.float32)
    return cv2.resize(samples, (SIZE,SIZE), interpolation=cv2.INTER_CUBIC)


def save(suffix, value):
    Image.fromarray(np.rint(np.clip(value,0,1)*255).astype('uint8')).save(
        ART/('T_EagleTalon_'+suffix+'.png'))


rest = sample(image_x)
awake = sample(image_x+720.)
luma = rest @ np.array([.2126,.7152,.0722], dtype=np.float32)
# Remove the broad studio lighting. Keep material variation at several scales and
# reconstruct micro-surface independently, so the metal responds to a moving light.
detail = np.where(front, np.clip(luma-blur(luma,17),-.14,.16),0)
grain = noise(SIZE)
hammer = noise(84)*.67 + noise(187)*.33
patina = np.clip(noise(24)*.30+noise(64)*.20+.25,0,1)
toolmarks = np.zeros_like(luma)
for i in range(530):
    x,y = rng.integers(0,SIZE,2)
    dx = int(rng.uniform(4,35))
    dy = int(dx*rng.uniform(-.6,.3))
    cv2.line(toolmarks,(int(x),int(y)),(int(x+dx),int(y+dy)),float(rng.uniform(.16,.52)),1,cv2.LINE_AA)
toolmarks = blur(toolmarks,.55)
# Retain the bevels and the cut lines around the beak at game mip sizes.
# A local reference band separates these shapes from the broad studio gradient.
relief = np.where(front, blur(luma,2.0)-blur(luma,31), 0)
cut = np.clip(-relief*4.8 - .025,0,1)
burnish = np.clip(relief*4.2 + np.maximum(detail,0)*.9,0,1)
tone = .345 + .33*burnish - .19*cut + .23*detail + .018*hammer + .008*grain - .042*patina + .16*toolmarks
save('BaseColor',np.stack([tone+.022+.012*patina,tone+.009,tone-.004-.018*patina],axis=-1))
rough = (.475-.21*burnish+.12*cut-.22*detail+.024*hammer+.016*grain+.075*patina-.14*toolmarks).clip(.22,.69)
occ = np.clip(.97-.18*cut+np.minimum(detail,0)*.35,.72,1.)
save('ORM',np.stack([occ,rough,.94-.17*cut-.08*patina],axis=-1))
height = .48*hammer+.064*grain+.105*noise(360)+detail*1.3-.51*toolmarks
dy,dx = np.gradient(height)
normal = np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
save('Normal',.5+.5*normal)
# The reference provides the exact illuminated pattern. Isolate the blue-white
# core in its second panel; reject the broad painted halo and ambient studio tint.
def blue_excess(rgb):
    return (rgb[:,:,2]-.67*rgb[:,:,0]-.33*rgb[:,:,1])

blue = (blue_excess(awake)-np.maximum(blue_excess(rest),0)).clip(0,1)
local = np.maximum(0,blue-blur(blue,9)*.68)
ice = np.clip((local-.014)*5.4,0,1)*np.clip((awake[:,:,2]-.10)*1.6,0,1)
save('IceMask',np.where(front,ice,0))
