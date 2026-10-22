import cv2, numpy as np, os, glob
d=r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
files=sorted(glob.glob(os.path.join(d,"atk2_frames","*.png")))
def sheet(sel,name,cols=4,w=480):
    ims=[]
    for f in sel:
        im=cv2.imread(f); i=int(os.path.basename(f)[1:6])
        im=cv2.resize(im,(w,w*9//16))
        cv2.putText(im,"%d %.3f"%(i,i/30),(6,22),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2)
        ims.append(im)
    while len(ims)%cols: ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d,"sheets",name),np.vstack([np.hstack(ims[i:i+cols]) for i in range(0,len(ims),cols)]))
sheet(files[0:24:2],"atk2_a.jpg")
sheet(files[24:40],"atk2_b.jpg")
sheet(files[40:64:2],"atk2_c.jpg")
sheet(files[64:81:2],"atk2_d.jpg")
print(len(files), os.path.basename(files[0]), os.path.basename(files[-1]))
