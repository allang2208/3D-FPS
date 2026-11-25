"""Centimetre profile shared by the mesh author and stone placement."""
import math


def section(s, width):
    return width*.5*(.88+.12*math.sin(s*5.2)), 9*math.sin(2.6*s)


def elevation(x,y,length,width,height,rut):
    s=2*x/length
    half,shift=section(s,width)
    t=(y-shift)/half
    edge=max(0,1-abs(s)**2.5-t*t)
    crown=height*edge**1.45*(1+.23*math.sin(.053*x+.082*y)+.15*math.cos(.081*x-.13*y))
    if rut:
        d=t*width/2-3*math.sin(s*3)
        crown*=.9-.8*math.exp(-(d/5.7)**2)+.36*math.exp(-((abs(d)-9)/4.5)**2)
    return -2.8+crown
