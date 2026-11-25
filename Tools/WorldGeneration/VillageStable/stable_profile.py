"""Measured top of the fitted slate shingles, sampled at the two bay interfaces (cm)."""
from bisect import bisect_right

DISTANCES=(0,20,60,100,140,180,220,260,300,340,360,380,400,420,431)
NORTH=(529,528,513,493,476,457,439,422,405,387,377,363,334,311,303)
SOUTH=(529,525,515,484,471,450,431,414,397,382,372,354,332,312,302)

def roof_top(y):
    heights=NORTH if y<0 else SOUTH
    d=min(431,abs(y))
    i=min(len(heights)-2,max(0,bisect_right(DISTANCES,d)-1))
    t=(d-DISTANCES[i])/(DISTANCES[i+1]-DISTANCES[i])
    return heights[i]*(1-t)+heights[i+1]*t
