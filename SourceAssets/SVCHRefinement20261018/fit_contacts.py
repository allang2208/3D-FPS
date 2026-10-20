"""Fit the existing hand shape to the selected SVCh grip and handguard surfaces."""
from contact_inputs import *
from scipy.optimize import least_squares
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

targets=json.loads((O/'contact_meshes.json').read_text())
meshes={k:trimesh.Trimesh(v['positions'],v['triangles'],process=False) for k,v in targets.items()}
isarm=np.array([VM['slots'][s].startswith('MI_Manny') for s in VM['material']])
donor=trimesh.Trimesh(X,T[~isarm],process=False)
dominant=W.argmax(1)
fits={}
fig,axes=plt.subplots(2,2,figsize=(12,9))
for side,key in [('r','pistol grip'),('l','handguard shell (5 slots)')]:
    target=meshes[key]; ids=hand_indices(side); h=X[ids]
    pivot=(TO_BIND@IDLE[N.index('hand_'+side)])[:3,3]
    near,dist,tid=trimesh.proximity.closest_point(donor,h)
    contact=[]
    for digit in ('hand','thumb','index','middle','ring','pinky'):
        if side=='r' and digit=='index':continue
        subset=np.array([j for j,i in enumerate(ids) if N[dominant[i]].startswith(digit)])
        chosen=subset[np.argsort(dist[subset])[:16]]
        contact.extend(chosen)
    contact=np.array(contact)
    index_pad=None
    if side=='r':
        index_ids=np.array([j for j,i in enumerate(ids) if N[dominant[i]]=='index_03_r'])
        # Fit the skin patch on the trigger side of the distal phalanx, not the
        # skeletal joint centre. Keep the complete accepted finger curl.
        old_trigger=np.array([5.93,-23.35,-11.06])
        index_pad=index_ids[np.argsort(np.linalg.norm(h[index_ids]-old_trigger,axis=1))[:12]]
        trigger_target=np.array([6.07,-21.681,-7.068])
    samples=np.linspace(0,len(h)-1,220).astype(int)
    initial=np.array([0,0,2.5 if side=='r' else 4.,0,0,0],float)
    def error(v):
        moved=apply_rigid(h,v[:3],v[3:],pivot)
        pts=moved[contact]
        cp,ds,ts=trimesh.proximity.closest_point(target,pts)
        # The accepted donor chooses the contact patches. A small positive gap
        # keeps the skin surface just outside the rigid gun, never at bone centres.
        signed=np.einsum('ij,ij->i',pts-cp,target.face_normals[ts])
        near2,ds2,ts2=trimesh.proximity.closest_point(target,moved[samples])
        signs=np.einsum('ij,ij->i',moved[samples]-near2,target.face_normals[ts2])
        anchor=(moved[index_pad].mean(0)-trigger_target)*12 if index_pad is not None else []
        return np.r_[((pts-cp)-target.face_normals[ts]*.06).ravel(),
                     np.minimum(signs+.08,0)*3,v[:3]*.08,v[3:]*4,anchor]
    sol=least_squares(error,initial,bounds=([-2,-4,-1,-.3,-.3,-.3],[2,4,6,.3,.3,.3]),max_nfev=75,diff_step=.0005)
    moved=apply_rigid(h,sol.x[:3],sol.x[3:],pivot)
    fits[side]={'translation_cm':sol.x[:3].tolist(),'rotation_vector':sol.x[3:].tolist(),
                'pivot_bind_cm':pivot.tolist(),'contact_vertex_ids':ids[contact].tolist(),
                'surface':key,'source':'saved SVD idle and skinned donor contact patches'}
    row=0 if side=='r' else 1
    for col,points in enumerate((h,moved)):
        ax=axes[row,col]
        tv=np.asarray(target.vertices)
        ax.scatter(-tv[:,1],tv[:,2],s=2,c='#303943')
        for digit,c in [('hand','#b7a18f'),('thumb','#f3b563'),('index','#e75a67'),('middle','#7a86df'),('ring','#5aaa8a'),('pinky','#8b72a1')]:
            subset=[j for j,i in enumerate(ids) if N[dominant[i]].startswith(digit)]
            ax.scatter(-points[subset,1],points[subset,2],s=1,c=c,label=digit)
        ax.set_aspect('equal');ax.set_title(side+' '+('source' if col==0 else 'surface fit'));ax.set_xlabel('forward (cm)');ax.set_ylabel('up (cm)')
        if row==0 and col==0:ax.legend(markerscale=5,fontsize=7)
    print('SVCH_CONTACT',side,'cm',np.round(sol.x[:3],4),'rot_deg',np.round(np.degrees(sol.x[3:]),3),flush=True)
(O/'contact_fit.json').write_text(json.dumps(fits,indent=1))
fig.tight_layout();fig.savefig(O/'contact_diagnosis.png',dpi=120);plt.close(fig)
