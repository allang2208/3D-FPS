"""Pack the independent original parts into two clear workbench columns."""
import math
def layout(recipe):
    columns=[[],[]];totals=[0.,0.]
    for part in sorted(recipe['parts'],key=lambda p:-p['extent'][1]):
        angle=math.radians(part['angle']);x,y=part['extent'][:2]
        half=abs(math.sin(angle))*x+abs(math.cos(angle))*y
        c=0 if totals[0]<=totals[1] else 1
        columns[c].append((part,half));totals[c]+=2*half+4.
    for c,entries in enumerate(columns):
        cursor=-(totals[c]-4.)*.5
        for part,half in entries:
            part['loose']=[45. if c==0 else 120.,cursor+half,95.4+part['extent'][2]]
            cursor+=2*half+4.
    return recipe
