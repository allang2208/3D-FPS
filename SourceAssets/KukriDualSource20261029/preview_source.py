"""Source-only skeleton contact sheet; no retarget or generated movement."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
OUT=Path(__file__).resolve().parent
CHAINS=[('pelvis','spine_01','spine_02','spine_03','neck_01','head'),
    ('spine_03','clavicle_l','upperarm_l','lowerarm_l','hand_l','middle_01_l','middle_02_l','middle_03_l'),
    ('spine_03','clavicle_r','upperarm_r','lowerarm_r','hand_r','middle_01_r','middle_02_r','middle_03_r'),
    ('pelvis','thigh_l','calf_l','foot_l','ball_l'),('pelvis','thigh_r','calf_r','foot_r','ball_r')]
COLORS=['#454f60','#2778d4','#e86928','#2778d4','#e86928']
def draw(ax,d,f):
    ix={n:i for i,n in enumerate(d['names'])};x=np.array(d['frames'][f]);x[:,:2]-=x[ix['pelvis'],:2]
    for chain,color in zip(CHAINS,COLORS):
        points=x[[ix[n] for n in chain]]
        ax.plot(points[:,0],points[:,1],points[:,2],'-o',color=color,markersize=2.5,linewidth=2)
    ax.set(xlim=(-1.05,1.05),ylim=(-1.05,1.05),zlim=(0,2.3));ax.view_init(elev=13,azim=-60)
    ax.set_box_aspect((2.1,2.1,2.3));ax.set_axis_off()
    ax.set_title('Frame %d / %.3f s'%(d['first']+f,f/d['fps']),fontsize=10)
sources=[json.loads((OUT/(s+'-sample.json')).read_text()) for s in ('DualSword_Attack_Slash_01','DualSword_Attack_Cross_Slash')]
fig=plt.figure(figsize=(15,7),facecolor='#f5f6f8')
for row,d in enumerate(sources):
    for col,f in enumerate(np.linspace(0,len(d['frames'])-1,5).round().astype(int)):
        ax=fig.add_subplot(2,5,row*5+col+1,projection='3d',facecolor='#f5f6f8');draw(ax,d,f)
fig.text(.02,.96,'SOURCE ONLY: Slash_01 (0.233 s)',fontsize=15)
fig.text(.02,.49,'SOURCE ONLY: Cross_Slash (0.200 s)',fontsize=15)
fig.text(.02,.02,'Blue = left | Orange = right | Pelvis horizontal travel removed for viewing only. No pose edits.',fontsize=11)
fig.savefig(OUT/'source-contact-sheet.png',dpi=100,bbox_inches='tight');plt.close(fig)
images=[]
for f in range(max(len(d['frames']) for d in sources)):
    fig=plt.figure(figsize=(8,4),facecolor='#f5f6f8')
    for j,d in enumerate(sources):
        ax=fig.add_subplot(1,2,j+1,projection='3d',facecolor='#f5f6f8');draw(ax,d,min(f,len(d['frames'])-1))
    fig.suptitle('Slash_01                            Cross_Slash | 0.1x source speed',fontsize=12)
    fig.canvas.draw();images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB'));plt.close(fig)
images[0].save(OUT/'source-slow.gif',save_all=True,append_images=images[1:],duration=167,loop=0)
