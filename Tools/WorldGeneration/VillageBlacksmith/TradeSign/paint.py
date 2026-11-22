"""Packed paint coverage and pigment stencils traced from the approved elevation."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

out=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageBlacksmith20261117/TradeSign'
N=1024
def mask():return Image.new('L',(N,N))
def pts(seq):return [(round(x*N),round(y*N)) for x,y in seq]
def path(start,commands):
    points=[np.array(start)]
    for command in commands:
        if len(command)==2:
            points.append(np.array(command))
        else:
            a=points[-1];b,c,d=np.array(command).reshape(3,2)
            for t in np.arange(1,21)/20:
                points.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
    return pts(points)

cream,ochre,iron=mask(),mask(),mask()
anvil=path((.080,.466),[(.417,.466),(.417,.453),(.903,.453),(.905,.520),
    (.792,.546,.725,.561,.682,.620),(.628,.686,.620,.737,.654,.779),
    (.690,.822,.754,.849,.790,.855),(.790,.929),(.658,.929),(.633,.905),
    (.517,.897,.410,.897,.353,.914),(.333,.931),(.209,.931),(.209,.857),
    (.318,.836,.376,.770,.375,.714),(.376,.656,.326,.596,.260,.570),
    (.165,.538,.107,.497,.080,.466)])
ImageDraw.Draw(cream).polygon(anvil,fill=255)
# Slightly bent handle widens towards the outer end; cream lining surrounds the dark hammer head.
handle=path((.427,.208),[(.526,.239,.734,.311,.866,.357),(.883,.364,.882,.381,.869,.388),
                         (.856,.390,.845,.386,.835,.379),(.407,.260)])
ImageDraw.Draw(ochre).polygon(handle,fill=255)
head=[(.272,.297),(.427,.079),(.540,.133),(.518,.167),(.496,.198),
      (.478,.243),(.439,.287),(.385,.356),(.271,.302)]
ImageDraw.Draw(cream).polygon(pts(head),fill=255)
core=[(.286,.296),(.431,.092),(.523,.137),(.504,.163),(.481,.198),
      (.462,.238),(.425,.280),(.380,.340)]
ImageDraw.Draw(iron).polygon(pts(core),fill=255)
border=path((.038,.038),[(.962,.038),(.962,.766),(.862,.875),(.709,.941,.592,.962,.50,.965),
                         (.404,.963,.291,.942,.138,.876),(.037,.768),(.038,.038)])
ImageDraw.Draw(ochre).line(border,fill=255,width=9,joint='curve')
# Paint loss concentrates on exposed corners, board joints and the rim below the two iron straps.
rng=np.random.default_rng(40731)
def field(h,w,radius=0):
    a=Image.fromarray(rng.integers(0,256,(h,w),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC)
    if radius:a=a.filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(a,dtype=np.float32)/255
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
grains=field(202,680)
fine=field(910,970)
long=field(30,430)
edges=np.minimum.reduce((x,1-x,y,1-y))
joins=np.minimum(abs(x-.327),abs(x-.678))
nails=sum(np.exp(-((x-a)/.034)**2-((y-.045)/.055)**2) for a in (.18,.82))
age=.14*np.exp(-np.maximum(edges,0)*33)+.11*np.exp(-joins*120)+.12*nails
loss=np.clip((.23+age-(.42*fine+.32*grains+.26*long))*7,0,.99)
coverage=np.clip(.96-.90*loss-.07*(1-long),0,1)
channels=[np.uint8(255*coverage),np.maximum(np.asarray(cream),np.asarray(iron)),
          np.maximum(np.asarray(ochre),np.asarray(iron))]
Image.fromarray(np.stack(channels,axis=-1)).save(out/'T_SmithTradeSign_Pigment.png')
