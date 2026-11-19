"""Frame the four actual design views for a single Meshy head-and-hair task."""
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / 'SourceAssets/VillageBlacksmithNPC20261118'
DESIGN = ROOT / 'Design'
OUT = ROOT / 'Meshy/CombinedR1/Inputs'
OUT.mkdir(parents=True, exist_ok=True)
turn = Image.open(DESIGN / 'head_finished.png').convert('RGB')
hero = Image.open(DESIGN / 'character.png').convert('RGB')
width = turn.width // 3
# The polygon limits the lower crop to the neck, keeping clothing and the shoulder straps outside.
views = [
    ('01_front', turn.crop((0,0,width,620)), [(84,1),(565,1),(575,443),(510,525),(490,555),(480,585),(210,585),(202,555),(181,512),(105,440)]),
    ('02_three_quarter', hero.crop((875,0,1536,795)), [(55,0),(627,0),(653,343),(631,502),(511,632),(505,681),(490,746),(281,746),(254,692),(215,669),(103,598),(72,494),(64,378)]),
    ('03_profile', turn.crop((width,0,width*2,615)), [(30,0),(641,0),(646,435),(590,489),(555,509),(546,550),(345,550),(309,544),(198,566),(112,561),(54,466),(38,409)]),
    ('04_back', turn.crop((width*2,0,width*3,600)), [(72,0),(635,0),(640,447),(580,494),(535,500),(525,545),(245,545),(241,497),(179,480),(115,437)])
]
for name, im, points in views:
    rgb = np.asarray(im)
    region = np.zeros(rgb.shape[:2], np.uint8)
    cv2.fillPoly(region, [np.int32(points)], 1)
    mask = np.where(region, cv2.GC_PR_FGD, cv2.GC_BGD).astype(np.uint8)
    # Lock only the centre of the actual head as foreground.
    h,w = mask.shape
    cv2.ellipse(mask,(int(w*.50),int(h*.40)),(int(w*.12),int(h*.14)),0,0,360,cv2.GC_FGD,-1)
    cv2.grabCut(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),mask,None,
                np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),5,cv2.GC_INIT_WITH_MASK)
    alpha = np.uint8(((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD))*255)
    count,labels,stats,_=cv2.connectedComponentsWithStats(alpha)
    main=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    alpha=np.uint8((labels==main)*255)
    x,y,w,h=cv2.boundingRect(alpha)
    cut=im.crop((x,y,x+w,y+h))
    m=Image.fromarray(alpha).crop((x,y,x+w,y+h))
    factor=890/h
    size=(round(w*factor),890)
    cut=cut.resize(size,Image.Resampling.LANCZOS)
    m=m.resize(size,Image.Resampling.LANCZOS)
    tile=Image.new('RGB',(1024,1024),(174,173,170))
    tile.paste(cut,((1024-size[0])//2,60),m)
    tile.save(OUT/(name+'.png'))
