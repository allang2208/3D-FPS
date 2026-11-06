from pathlib import Path
import cv2,numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import gaussian_filter1d
p=Path(__file__).resolve().parent;c=cv2.VideoCapture(str(p.parent/'ReferenceV2/kubold-indexed.mp4'));c.set(1,1034);ok,first=c.read();ref=cv2.cvtColor(first,cv2.COLOR_BGR2GRAY);mask=np.zeros_like(ref);mask[135:487,8:1268]=255;pts=cv2.goodFeaturesToTrack(ref,450,.015,9,mask=mask);old=pts[:,0];focal=360/np.tan(np.deg2rad(37.5));rays=lambda a: np.array([(a[:,0]-640)/focal,np.ones(len(a)),(360-a[:,1])/focal]).T;values=[np.zeros(3)];details=[]
sift=cv2.SIFT_create(1000); kp0,desc0=sift.detectAndCompute(ref,mask); matcher=cv2.BFMatcher()
for i in range(1035,1115):
 ok,frame=c.read();g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY);kp,desc=sift.detectAndCompute(g,None); pairs=[m for m,n in matcher.knnMatch(desc0,desc,k=2) if m.distance<.75*n.distance]; a=np.float32([kp0[m.queryIdx].pt for m in pairs]);b=np.float32([kp[m.trainIdx].pt for m in pairs]);H,inliers=cv2.findHomography(a,b,cv2.RANSAC,2.0);idx=inliers[:,0]>0;ro,_=Rotation.align_vectors(rays(a[idx])/np.linalg.norm(rays(a[idx]),axis=1)[:,None],rays(b[idx])/np.linalg.norm(rays(b[idx]),axis=1)[:,None]);yaw,pitch,roll=ro.as_euler('ZXY',degrees=True);values.append(np.array([pitch,-yaw,roll]));details.append(idx.sum())
values=gaussian_filter1d(np.array(values),.85,axis=0,mode='nearest');print('inliers min/median',min(details),np.median(details));print(np.round(values[::4],2));print('end',values[-1]);print('headings')
import json
for n in ['Standard','LongGrip']:
 rows=json.loads((p/(n+'-fit.json')).read_text());print(n,[(e['frame'],round(e['heading'])) for e in rows[17:31]])
