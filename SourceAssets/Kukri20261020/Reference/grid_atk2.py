import cv2, numpy as np, os
d=r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
def grid(im):
    h,w=im.shape[:2]
    for k in range(-4,5):
        x=int((k/4*0.5+0.5)*w); y=int((k/4*0.5+0.5)*h)
        col=(0,255,255) if k==0 else (200,200,200)
        cv2.line(im,(x,0),(x,h),col,1); cv2.line(im,(0,y),(w,y),col,1)
        cv2.putText(im,"%.2f"%(k/4),(x+2,h-6),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,255,0),1)
        cv2.putText(im,"%.2f"%(k/4),(2,y-2),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,255,0),1)
    return im
def sheet(idx,name,cols=3,w=640):
    ims=[]
    for i in idx:
        im=cv2.imread(os.path.join(d,"atk2_frames","f%05d.png"%i)); im=cv2.resize(im,(w,w*9//16)); im=grid(im)
        cv2.putText(im,"%d t=%.3f"%(i,(i-2610)/30),(200,20),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2); ims.append(im)
    while len(ims)%cols: ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d,"sheets",name),np.vstack([np.hstack(ims[i:i+cols]) for i in range(0,len(ims),cols)]))
sheet([2610,2611,2612,2613,2614,2615,2616,2618,2619],"grid_a.jpg")
sheet([2620,2621,2622,2623,2625,2628,2631,2633,2635],"grid_b.jpg")
sheet([2640,2641,2642,2643,2644,2645,2646,2647,2648],"grid_c.jpg")
