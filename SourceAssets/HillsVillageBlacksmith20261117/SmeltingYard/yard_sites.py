"""Local UE metres, measured from the repaired shelter pivot. Positive X points into the shop."""
import math

WEST, HALF = -1.90, 3.78
WALL_YAW = -2.
BAY_Y = (-.84, 1.50)
# Back of the 1.20 m furnace stands 23 cm off the face, including the facade's skew.
def wall(y):
    return 7.99 - math.tan(math.radians(WALL_YAW))*y

def bay(y):
    return wall(y)-.83/math.cos(math.radians(WALL_YAW)), y

def sockets_cm():
    result = {}
    for i,y in enumerate(BAY_Y):
        x,_ = bay(y)
        result[f'FurnaceBay{i}'] = ([100*x,100*y,0], [0,180+WALL_YAW,0])
    # A down-facing decal uses local Z for texture U (+yard X) and local Y for V.
    result['ApronWear'] = ([290,0,0], [-90,0,0])
    result['WallBloom'] = ([100*wall(.30),30,254], [0,WALL_YAW,0])
    return result
