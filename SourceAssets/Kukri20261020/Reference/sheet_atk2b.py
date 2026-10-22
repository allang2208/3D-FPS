import cv2, numpy as np, os
d=r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
def sheet(idx,name,cols=3,w=640):
    ims=[]
    for i in idx:
        im=cv2.imread(os.path.join(d,"atk2_frames","f%05d.png"%i)); im=cv2.resize(im,(w,w*9//16))
        cv2.putText(im,"%d %.3f"%(i,i/30),(6,24),cv2.FONT_HERSHEY_SIMPLEX,.75,(0,255,255),2); ims.append(im)
    while len(ims)%cols: ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d,"sheets",name),np.vstack([np.hstack(ims[i:i+cols]) for i in range(0,len(ims),cols)]))
sheet(range(2609,2618),"atk2_windup.jpg")
sheet(range(2617,2626),"atk2_strike.jpg")
