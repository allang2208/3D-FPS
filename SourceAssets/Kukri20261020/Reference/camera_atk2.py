import cv2, numpy as np, os, json, math
d=r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
orb=cv2.ORB_create(3000)
def load(i):
    return cv2.imread(os.path.join(d,"atk2_frames","f%05d.png"%i),cv2.IMREAD_GRAYSCALE)
H,W=720,1280
mask=np.zeros((H,W),np.uint8); mask[90:int(H*0.5),:]=255; mask[0:110,0:260]=0; mask[0:80,1000:]=0
ref=2608  # idle frame before attack
kr,dr=orb.detectAndCompute(load(ref),mask)
bf=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True)
out=[]
for i in range(2600,2676):
    k,dsc=orb.detectAndCompute(load(i),mask)
    m=sorted(bf.match(dr,dsc),key=lambda x:x.distance)[:400]
    src=np.float32([kr[x.queryIdx].pt for x in m]); dst=np.float32([k[x.trainIdx].pt for x in m])
    A,inl=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=3)
    if A is None: out.append((i,None)); continue
    rot=math.degrees(math.atan2(A[1,0],A[0,0])); sc=math.hypot(A[0,0],A[1,0])
    # displacement of the screen centre
    c=np.array([W/2,H/2,1.0]); cd=A@c - c[:2]
    out.append((i,dict(rot=round(rot,2),scale=round(sc,4),dx=round(float(cd[0]),1),dy=round(float(cd[1]),1),inl=int(inl.sum()))))
for i,r in out: print(i, "%.3f"%(i/30), r)
json.dump(out,open(os.path.join(d,"atk2_camera.json"),"w"))
