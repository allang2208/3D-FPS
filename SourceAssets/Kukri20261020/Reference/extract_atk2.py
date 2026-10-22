import cv2, numpy as np, os
d=r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
c=cv2.VideoCapture(os.path.join(d,"ref.f100024.mp4"))
fps=c.get(cv2.CAP_PROP_FPS)
c.set(cv2.CAP_PROP_POS_FRAMES,int(86.5*fps))
for i in range(int(86.5*fps),int(89.2*fps)):
    ok,f=c.read()
    if not ok: break
    cv2.imwrite(os.path.join(d,"atk2_frames","f%05d.png"%i),f)
print(fps)
