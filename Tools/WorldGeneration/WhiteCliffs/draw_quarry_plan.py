"""Draw the entrance plan and surveyed rock section from the runtime station table."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Ellipse, Polygon
import numpy as np
from quarry_approach_survey import section, ease, verge_pockets

root = Path(__file__).resolve().parents[3]
font_manager.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
plt.rcParams.update({"font.family": "Microsoft YaHei", "axes.unicode_minus": False})
paper, text, dark = "#f6f2e7", "#25382f", "#42574b"
fig = plt.figure(figsize=(14, 9), facecolor=paper)
ax = fig.add_axes((.06,.12,.51,.75), aspect="equal", facecolor="#dcd5bc")
y = np.linspace(-38, 50, 520)
west, east, _, _, road, _ = section(y)
ax.fill_betweenx(y, -45, west, color="#9da197")
ax.fill_betweenx(y, east, 45, color="#adbaa4")
for setback, color in [(0,"#626e65"),(2,"#c6c2ac"),(5,"#86907f"),(8,"#677f6b"),(12,"#81957c")]:
    ax.plot(west-setback, y, color=color, lw=1.4)
    ax.plot(east+setback, y, color=color, lw=1.0)
bay = (y > -7.1) & (y < 9.55)
ax.plot(west[bay]-1.8,y[bay],color="#f1e6cc",lw=4)
ax.fill_betweenx(y,road-3.45,road+3.45,color="#c0b296")
ax.fill_betweenx(y,road-2.28,road+2.28,color="#a3957c")
for side in (-1,1):
    ax.plot(road+side*1.10,y,color="#887c69",lw=.65)
for x, cy, a, b in [(-12.6,-15.1,17.4,14.6),(10.5,-14.3,13,11.4)]:
    ax.add_patch(Ellipse((x,cy),a,b,facecolor="#c3b398",edgecolor="none"))
for x,cy,rx,ry,angle,turf,gravel,_ in verge_pockets():
    phase=np.linspace(0,2*np.pi,60)
    u=np.cos(phase)
    v=np.sin(phase)+.24*np.sin(3.*u)
    rad=np.deg2rad(angle)
    px=x+rx*u*np.cos(rad)-ry*v*np.sin(rad)
    py=cy+rx*u*np.sin(rad)+ry*v*np.cos(rad)
    ax.fill(px,py,fc="#89976c" if turf>gravel else "#afa389",alpha=.86)
for path in [[(section(-21.1)[4],-21.1),(-5.3,-18.7),(-12.6,-15.1)],
             [(section(-20.7)[4],-20.7),(5.2,-16.8),(10.5,-14.3)]]:
    px,py=zip(*path)
    ax.plot(px,py,color="#aa987f",lw=6,solid_capstyle="round")
for tip, end, half in [((-17.5,2.9),(-10.6,.1),1.65),((-17.1,6.7),(-10.85,4.9),1.25),
                       ((-19.5,-20.2),(-13.7,-23.4),1.1)]:
    a,b=np.array(tip),np.array(end)
    vec=b-a; normal=np.array((-vec[1],vec[0]))/np.linalg.norm(vec)
    ax.add_patch(Polygon([a,a+vec*.49+normal*half,b,a+vec*.65-normal*half],fc="#b6ac96",
                         ec="#948773",lw=.6,hatch=".."))

def footprint(x, y, length, width, yaw):
    angle=np.deg2rad(yaw)
    rot=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    corners=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])*np.array([length,width])*.5
    ax.add_patch(Polygon(corners@rot.T+[x,y],fc="#76553d",ec="#503e33",lw=1))

footprint(-12.6,-15.1,9.2,6.5,-124)
footprint(10.5,-14.3,5.82,3.12,-8)
footprint(-15.5,-18.6,2.18,1.42,-124)
ax.plot([0],[-29],"o",c="#974e38")
ax.annotate("",(-1.4,8.6),(0,-29),arrowprops=dict(arrowstyle="-|>",color="#974e38",ls="--",lw=1.25))
ax.axhline(1.8,color=dark,alpha=.55,ls=":",lw=1)
for label, target, at in [
        ("入口", (0,-29),(8,-32)),("工棚与修坯台",(-12.6,-15.1),(-24,-25.5)),
        ("吊装坪",(10.5,-14.3),(24,-20)),("主采面",(-19.8,3),(-32,7)),
        ("东侧低台",(17,3),(30,8.5)),("运输路回折",(9.85,32.3),(2,41))]:
    ax.annotate(label,target,at,ha="center",va="center",fontsize=10,color=text,
                bbox=dict(fc=paper,ec="none",pad=2,alpha=.9),
                arrowprops=dict(arrowstyle="-",color=dark,lw=.8))
ax.set(xlim=(38,-41),ylim=(-38,50),xlabel="采区横向 X（米）　·　按入口朝向排布",ylabel="进场方向 Y（米）")
ax.grid(alpha=.08); ax.tick_params(labelsize=8)
fig.text(.065,.938,"白崖采石场　/　入口与采面",fontsize=25,color=text)
fig.text(.066,.891,"施工平面与横断面　　入口视线朝上，右手为主采面",fontsize=12,color=dark)
fig.text(.609,.806,"沿墙进场",fontsize=17,color=text)
fig.text(.609,.696,"吊架在左，工棚在右，两处工位距入口约 18 米。\n运输路沿崖脚回折，棚后岩壁连续延伸到路弯。",fontsize=11,color=text,linespacing=1.75)
cross=fig.add_axes((.63,.431,.30,.175),facecolor=paper)
x=np.linspace(-35,35,500)
w,e,wh,eh,_,_=section(1.8)
def profile(d,h):
    return h*(.49*ease(.65,3.2,d)+.38*ease(3.5,5.7,d)+.13*ease(6.5,8.6,d))
z=profile(w-x-2.45,wh)+profile(x-e,eh)
cross.fill_between(x,0,z,color="#a2aa96")
cross.plot(x,z,color=dark,lw=1.4)
cross.set(xlim=(35,-35),ylim=(-.3,17),xlabel="横向距离（米）",ylabel="高差（米）",
          title="采面中部 · 地形承托剖面，Y = 1.8 米")
cross.spines[["right","top"]].set_visible(False)
cross.tick_params(labelsize=8)
fig.text(.609,.294,"岩脚与作业面",fontsize=17,color=text)
fig.text(.609,.122,"绿色为避开车流的返草地，灰褐色为砾石沉积。\n棚前踏道收窄，吊架回转处磨出较宽的砾面。\n右侧断面落石向路肩变细，左侧旧台由草地接回。",fontsize=11,color=text,linespacing=1.75)
fig.savefig(root/"SourceAssets/HillsQuarryCutYard/01-site-plan.png",dpi=150,facecolor=paper)
