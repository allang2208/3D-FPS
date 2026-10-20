"""Scoped offline evidence for the reported grip/ADS defects; no game/render."""
from contact_inputs import *
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
profile=json.loads((O/'shared_profile.json').read_text())
entry=next(c for c in profile['clips'] if c['base'].endswith('_idle'))
local=matrices(D['clips']['idle']['frames'][0])
for tr in entry['tracks']:
    i=N.index(tr['bone']);v=np.array(tr['values'][:10])
    local[i,:3,3]+=v[:3]
    local[i,:3,:3]=Rotation.from_quat(v[3:7]).as_matrix()@local[i,:3,:3]
pose=components(local)
targets=json.loads((O/'contact_meshes.json').read_text())
report={'scope':'saved source geometry and idle profile; not a runtime or visual acceptance','hands':{}}
fig,axes=plt.subplots(2,2,figsize=(12,10))
for row,(side,key) in enumerate([('r','pistol grip'),('l','handguard shell (5 slots)')]):
    ids=hand_indices(side);points=skin(pose,ids);target=targets[key]
    mesh=trimesh.Trimesh(target['positions'],target['triangles'],process=False)
    cp,ds,ts=trimesh.proximity.closest_point(mesh,points)
    inside=mesh.contains(points)
    report['hands'][side]={'surface':key,'max_skin_overlap_mm':float(max(ds[inside],default=0)*10),
                          'vertices_overlap_over_1_5mm':int(np.count_nonzero(inside&(ds>.15)))}
    for col,(a,b,title) in enumerate([(1,2,'side'),(0,2,'cross section')]):
        ax=axes[row,col];verts=np.asarray(target['positions']);faces=np.asarray(target['triangles'])
        ax.add_collection(PolyCollection(verts[faces][:,:,[a,b]],facecolors='#303943',edgecolors='none',alpha=.07))
        for digit,c in [('hand','#b7a18f'),('thumb','#f3b563'),('index','#e75a67'),('middle','#7a86df'),('ring','#5aaa8a'),('pinky','#8b72a1')]:
            subset=[j for j,i in enumerate(ids) if N[W[i].argmax()].startswith(digit)]
            ax.scatter(points[subset,a],points[subset,b],s=1,c=c,label=digit)
        ax.set_aspect('equal');ax.set_title(side+' / '+title+' / source-space cm');ax.autoscale_view()
        # Focus the hand region, retaining the gun's local cross-section.
        lo=points[:,a].min()-1;hi=points[:,a].max()+1;ax.set_xlim(lo,hi)
        ax.set_ylim(points[:,b].min()-1,points[:,b].max()+1)
        if row==0 and col==0:ax.legend(markerscale=4,fontsize=7)
cal=json.loads((O/'calibration.json').read_text())
rear=VR[ROOT]@np.r_[cal['RearSight'],1];front=VR[ROOT]@np.r_[cal['FrontSight'],1]
up=VR[ROOT][:3,:3]@cal['SightUp'];up/=np.linalg.norm(up)
report['ads']={'rear_component_cm':rear[:3].tolist(),'front_component_cm':front[:3].tolist(),
               'physical_up_error_deg':float(np.degrees(np.arccos(np.clip(up@[0,0,1],-1,1)))),
               'sight_radius_cm':float(np.linalg.norm(front[:3]-rear[:3]))}
fig.tight_layout();fig.savefig(O/'contact_diagnosis_final.png',dpi=120);plt.close(fig)
(O/'diagnosis.json').write_text(json.dumps(report,indent=1))
print(json.dumps(report,indent=1))
