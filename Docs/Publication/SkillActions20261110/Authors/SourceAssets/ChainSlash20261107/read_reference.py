"""Decode the requested reference interval for motion authoring (not game QA)."""
from pathlib import Path
import cv2
import numpy as np
P=Path(__file__).resolve().parent/'Reference'
cap=cv2.VideoCapture(str(P/'NTrzxPIXer4.mp4'))
fps=cap.get(cv2.CAP_PROP_FPS)
frames=[]
cap.set(cv2.CAP_PROP_POS_FRAMES,round(34*fps))
for i in range(round(7*fps)+1):
    ok,img=cap.read()
    if not ok: break
    frame=round(34*fps)+i
    cv2.imwrite(str(P/f'f{frame:04d}.jpg'),img)
    if i%10==0:
        tile=cv2.resize(img,(384,216))
        cv2.putText(tile,f'{frame/fps:.3f}s  f{frame}',(8,20),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,255),1)
        frames.append(tile)
for j in range(0,len(frames),15):
    tiles=frames[j:j+15]
    tiles += [np.zeros_like(tiles[0])]*(15-len(tiles))
    grid=np.vstack([np.hstack(tiles[k:k+3]) for k in range(0,15,3)])
    cv2.imwrite(str(P/f'contact-{j//15}.jpg'),grid)
print('Reference FPS',fps,'frames decoded',i+1)
