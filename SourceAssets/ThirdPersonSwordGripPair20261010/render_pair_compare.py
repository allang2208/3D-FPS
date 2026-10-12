"""Before/after pose diagnosis using native output and the production gauntlets."""
from study_pair import *

fig,axs=plt.subplots(2,3,figsize=(10,9),facecolor='#20252c')
summary={}
for row_id,stage in enumerate(('before','after')):
    capture=json.loads((OUT/f'native-{stage}.json').read_text())
    values=[]
    for sample_id,row in enumerate(capture['dash_samples']):
        f=np.array([row['actual_local'][n] for n in names]);w,p=skin(f);wp=weapon(w,row['grip_roll']);v=in_weapon(p,wp)
        top=float(v[hand_ids['r'],2].min());bottom=float(v[hand_ids['l'],2].max())
        values.append({'progress':row['progress'],'axial_gap_cm':top-bottom})
        if sample_id not in (0,3,7):continue
        ax=axs[row_id,(0,3,7).index(sample_id)];view=R.from_euler('z',-35,degrees=True).as_matrix();vv=v@view.T
        faces=[];colors=[]
        for s,color in [('r',np.array([.25,.65,1.])),('l',np.array([1.,.6,.28]))]:
            keep=np.zeros(len(points),bool);keep[hand_ids[s]]=True;idx=tri[np.all(keep[tri],axis=1)];pf=vv[idx]
            norm=np.cross(pf[:,1]-pf[:,0],pf[:,2]-pf[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-8)
            shade=.5+.5*np.abs(norm@np.array([.2,-.8,.55]));faces.append(pf);colors.append(shade[:,None]*color)
        faces=np.concatenate(faces);colors=np.concatenate(colors);order=np.argsort(-faces[:,:,1].mean(1))
        ax.add_collection(PolyCollection(faces[order][:,:,[0,2]],facecolors=colors[order],edgecolors='none'))
        ax.plot([0,0],[-26,1],color='white',alpha=.25,lw=.8)
        color='#80dfb4' if top>bottom else '#ec877f'
        ax.hlines([top,bottom],-10,10,color=color,linestyle=':',lw=.8)
        ax.set_xlim(-12,12);ax.set_ylim(-26,1);ax.set_aspect('equal');ax.set_facecolor('#20252c');ax.axis('off')
        ax.set_title(f'{stage.upper()} | {row["progress"]:.0%}\nGrip clearance {top-bottom:.2f} cm',color='white',fontsize=11)
    summary[stage]={'clip':capture['dash_clip'],'samples':values,'minimum_axial_gap_cm':min(r['axial_gap_cm'] for r in values)}
fig.suptitle('Production gauntlets / native animation poses\nRight hand: blue    Left hand: orange',color='white',fontsize=13)
fig.tight_layout();fig.savefig(OUT/'pair-comparison.png',dpi=140)
(OUT/'pair-comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({key:val['minimum_axial_gap_cm'] for key,val in summary.items()}))
