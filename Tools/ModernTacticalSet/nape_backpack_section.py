"""Plot a native centimetre section of the pack-facing side and rear helmet rim."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties
from scipy.spatial.transform import Rotation

P=Path(__file__).resolve().parents[2]
S=P/"SourceAssets/ModernTacticalSet20261113"
R=P/"SourceAssets/BackpackFit20261024/ModernTacticalHelmetPacks20261118"
OLD=R.with_name("ModernTacticalShoulders20261118")
read=lambda p:json.loads(p.read_bytes())

def section(p,f,cut):
    tri=p[f].copy();tri[:,:,0]-=cut
    select=(tri[:,:,0].min(axis=1)<0)&(tri[:,:,0].max(axis=1)>=0);tri=tri[select]
    segments=[]
    for a,b,c in ((0,1,2),(1,2,0),(2,0,1)):
        hit=tri[((tri[:,a,0]>=0)!=(tri[:,b,0]>=0))&((tri[:,a,0]>=0)!=(tri[:,c,0]>=0))]
        if len(hit):
            def where(j):
                u=hit[:,a,0]/(hit[:,a,0]-hit[:,j,0])
                return hit[:,a,1:]*(1-u[:,None])+hit[:,j,1:]*u[:,None]
            segments.append(np.stack((where(b),where(c)),axis=1))
    return np.concatenate(segments)

def main():
    fig,axes=plt.subplots(1,2,figsize=(8.5,4.7),layout="constrained")
    font=FontProperties(fname="C:/Windows/Fonts/msyh.ttc",size=10)
    base=read(OLD/"authored.json");new=read(R/"authored.json");cache=read(OLD/"captured.json")
    for ax,rig in zip(axes,("Jason","Kaitlin")):
        head=read(S/"HelmetNapeR3/Authored"/f"helmet_{rig}_world.json")
        p=np.asarray(head["positions"]);f=np.array(head["triangles"])[np.array(head["triangle_materials"])==0]
        ob=next(s for s in base["rows"] if s["rig"]==rig and s["item"]=="ue_special_duty_backpack")
        ax.add_collection(LineCollection(section(p,f,1.5),colors="black",linewidths=2.5,label="盔壳"))
        for src,co,label in ((base,"#d98448","原背包"),(new,"#177e79","修订背包")):
            r=next(s for s in src["statics"] if rig in s["asset"] and "special_duty" in s["asset"])
            a=np.fromfile(r["positions"],dtype="<f4").reshape(-1,3)
            a=Rotation.from_quat(ob["rigid_rotation_quat"]).apply(a)+ob["rigid_location"]
            f=np.fromfile(Path(cache[r["source"]]["folder"])/"triangles.bin",dtype="<i4").reshape(-1,3)
            ax.add_collection(LineCollection(section(a,f,1.5),colors=co,linewidths=1.65,label=label))
        h=p[np.unique(np.array(head["triangles"])[np.array(head["triangle_materials"])==0]),2].max()
        ax.set(xlim=(-28,14),ylim=(h-33,h+2),aspect="equal",title=rig)
        ax.set_xlabel("前后位置（厘米）",fontproperties=font);ax.set_ylabel("高度（厘米）",fontproperties=font)
        ax.grid(alpha=.18);ax.legend(loc="upper left",prop=font,frameon=False)
    fig.suptitle("特勤背包装备截面 · 自然站姿",fontproperties=font,size=15)
    fig.savefig(R/"special-duty-section.png",dpi=145)
if __name__=="__main__":main()
