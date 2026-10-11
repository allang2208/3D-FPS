"""Measure the user's recorded background, excluding HUD, weapon and hands.

This reads existing reference frames; it does not render or run the game.
Coordinates: screen X right, Y down; translations in fractions of frame width.
"""
from pathlib import Path
import json, math
import cv2
import numpy as np

O=Path(__file__).parent
FRAMES=Path('D:/FPS3D/test/super90_df_ref/frames60')
START,END=164,325
def read(f):
    return cv2.imread(str(FRAMES/f'f{f:04d}.jpg'),cv2.IMREAD_GRAYSCALE)
base=read(START);h,w=base.shape
mask=np.zeros_like(base)
# Fixed architecture above every visible weapon/hand position in this interval.
rects=[[310,45,1225,240],[160,200,420,350]]
for x0,y0,x1,y1 in rects:mask[y0:y1,x0:x1]=255
p0=cv2.goodFeaturesToTrack(base,1400,.006,7,mask=mask,blockSize=7)
center=np.array([w/2,h/2],dtype=np.float64)
rows=[]
for f in range(START,END+1):
    img=read(f)
    p1,st,_=cv2.calcOpticalFlowPyrLK(base,img,p0,None,winSize=(41,41),maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,.001))
    back,bs,_=cv2.calcOpticalFlowPyrLK(img,base,p1,None,winSize=(41,41),maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,.001))
    valid=(st[:,0]>0)&(bs[:,0]>0)&(np.linalg.norm(back-p0,axis=2)[:,0]<.75)
    a=p0[:,0][valid];b=p1[:,0][valid]
    M,inliers=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=1.25,maxIters=4000,confidence=.999,refineIters=20)
    if M is None or int(inliers.sum())<40:raise RuntimeError(f'Insufficient architecture matches at {f}')
    # Also retain homography inputs: 2D motion is observable; world translation
    # and camera focal length cannot be uniquely recovered from this capture.
    displacement=M[:,:2]@center+M[:,2]-center
    predicted=a@M[:,:2].T+M[:,2]
    residual=np.linalg.norm(predicted-b,axis=1)[inliers[:,0]>0]
    rows.append(dict(frame=f,x_width=float(displacement[0]/w),y_width=float(displacement[1]/w),
        roll_degrees=math.degrees(math.atan2(M[1,0],M[0,0])),scale=float(math.hypot(M[0,0],M[1,0])),
        features=int(inliers.sum()),median_residual_px=float(np.median(residual))))
(O/'reference_camera.json').write_text(json.dumps(dict(video='C:/Users/allan/Videos/NVIDIA/Delta Force/Delta Force 2026.10.09 - 09.55.46.01.mp4',
    fps=60,width=w,height=h,start=START,end=END,mask_rects=rects,
    method='Reference-to-frame pyramidal LK + forward/back rejection + RANSAC similarity; no accumulated integration',samples=rows),indent=2),encoding='utf-8')
print(json.dumps(dict(frames=len(rows),features_min=min(r['features'] for r in rows),
    median_residual_px=float(np.median([r['median_residual_px'] for r in rows])),
    x_range_px=[min(r['x_width'] for r in rows)*w,max(r['x_width'] for r in rows)*w],
    y_range_px=[min(r['y_width'] for r in rows)*w,max(r['y_width'] for r in rows)*w],
    roll_range=[min(r['roll_degrees'] for r in rows),max(r['roll_degrees'] for r in rows)],
    scale_range=[min(r['scale'] for r in rows),max(r['scale'] for r in rows)],
    selected=[r for r in rows if r['frame'] in (164,187,232,244,254,258,269,285,308,325)]),indent=2))
