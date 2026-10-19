import json,numpy as np
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
O=Path('SourceAssets/BlueMageRobe20261018/StairRepair20261019');fig=plt.figure(figsize=(13,6))
for idx,name in enumerate(['hipfit-inplace','leg-guide-01']):
 d=json.loads((O/('simulation-'+name+'.json')).read_text());s=d['samples'][15];p=np.array(s['particles']);f=np.array(d['indices']).reshape(-1,3);ax=fig.add_subplot(1,2,idx+1,projection='3d');poly=Poly3DCollection(p[f],facecolor='#1343a0',edgecolor='#14305c',linewidth=.12);ax.add_collection3d(poly);bones={b['name']:b for b in s['bones']}
 for side in ['l','r']:
  q=np.array([bones[n+'_'+side]['p'] for n in ['thigh','calf','foot','ball']]);ax.plot(q[:,0],q[:,1],q[:,2],color='#da8525',linewidth=5)
 ax.set(xlim=(-40,40),ylim=(-70,70),zlim=(-10,105),title=name+' | isolated frame '+str(s['frame']));ax.set_box_aspect((80,140,115));ax.view_init(elev=12,azim=-30)
plt.tight_layout();fig.savefig(O/'solver-comparison.png',dpi=140)
print('PLOT_SAVED')
