from pathlib import Path
import sys,json
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'pythonlib'))
import numpy as np,shapely,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Patch
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from matplotlib import font_manager
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams['font.family']='Microsoft YaHei';plt.rcParams['axes.unicode_minus']=False
F=json.loads((R/'findings.json').read_text());C=json.loads((R/'precise_contacts.json').read_text())
G={k:shapely.from_wkb((R/(k+'.wkb')).read_bytes()) for k in ['lane','junction','sidewalk','building_pad','park','road']}
def draw(ax,g,color,edge='none',lw=.4):
    for p in (list(g.geoms) if hasattr(g,'geoms') else [g]):
        if p.is_empty or p.geom_type!='Polygon':continue
        p=orient(p,sign=1)
        rings=[p.exterior,*p.interiors]
        path=MPath.make_compound_path(*[MPath(np.asarray(r.coords),closed=True) for r in rings])
        ax.add_patch(PathPatch(path,facecolor=color,edgecolor=edge,lw=lw))
fig,ax=plt.subplots(figsize=(15,10));fig.patch.set_facecolor('#f5f5f1');ax.set_facecolor('#e3e8df')
for k,col in [('junction','#536473'),('lane','#89969e'),('sidewalk','#d8c7a7'),('building_pad','#526985'),('park','#9bb77e')]:draw(ax,G[k],col)
draw(ax,G['road'].intersection(G['building_pad']),'#f55040')
unique={}
for x in C['confirmed']:
    car=x['a'] if x['a']['kind']=='car' else x['b'];key=(car['actor'],car['component'],car['index'])
    unique[key]=x['contact_examples_world_m'][0]
xy=np.array(list(unique.values()));ax.scatter(xy[:,0],xy[:,1],s=19,c='#ad2673',label='确认车辆穿插（92 辆 / 110 组接触）',zorder=5)
old=F['retained_furnishing_conflicts'];xy=np.array([x['p'] for x in old if x['tree']])/100
ax.scatter(xy[:,0],xy[:,1],marker='x',s=40,color='#e07c17',lw=1.7,label='旧树占位冲突（32 棵）',zorder=7)
cfg=json.loads((R.parent/'native_inputs.json').read_text());keep=next(x for x in cfg['inputs'] if x['tag']=='NBPCG_Exclusion');kp=Polygon(np.array(keep['points'])[:,:2]/100)
draw(ax,kp,'#f5f5f1','#cf4e44',1.5)
ax.text(15,-10,'公寓\n保留区',ha='center',va='center',fontsize=10,color='#97382f')
ax.scatter([472.14],[-505],marker='*',s=155,c='#e32620',edgecolor='white',lw=.6,zorder=9)
ax.annotate('收口缺口 + 后侧建筑退界冲突',xy=(472.14,-505),xytext=(110,-538),fontsize=10,color='#9c2925',arrowprops={'arrowstyle':'->','color':'#9c2925'})
ax.set_xlim(-535,535);ax.set_ylim(-560,75);ax.set_aspect('equal');ax.grid(alpha=.12)
ax.set_title('公寓这一岸：正式地图几何排查',fontsize=17,pad=15)
ax.set_xlabel('世界 X（米）');ax.set_ylabel('世界 Y（米）')
handles=[Patch(facecolor='#89969e',label='道路'),Patch(facecolor='#d8c7a7',label='人行道'),Patch(facecolor='#526985',label='建筑占地'),Patch(facecolor='#9bb77e',label='绿地')]
extra,labels=ax.get_legend_handles_labels();ax.legend(handles=handles+extra,loc='upper left',fontsize=9,ncol=3,framealpha=.94)
fig.text(.08,.03,'依据已保存网格与变换绘制；车辆接触已做原始三角网格复核。旧树按树干占位检查。此图不是游戏截图。',fontsize=9,color='#52616b')
fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(R/'audit_overview.png',dpi=170);plt.close(fig)
print('AUDIT_OVERVIEW_SAVED')
