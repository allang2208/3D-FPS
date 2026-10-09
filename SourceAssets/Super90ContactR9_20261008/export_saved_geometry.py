import numpy as np,json
from pathlib import Path
O=Path(__file__).parent;old=O/'render_saved.py'
ns={'__file__':str(old)};exec(compile(old.read_text().split('items=[]')[0],str(old),'exec'),ns)
s=ns['s'];names=s['names'];index={n:i for i,n in enumerate(names)}
verts=[];weights=[];faces=[];labels=[]
for key in ('weapon','props'):
 for ob in ns['groups'][key]:
    off=len(verts);ob.data.calc_loop_triangles()
    for v in ob.data.vertices:
        verts.append([*(ob.matrix_world@v.co),1]);w=[0.]*len(names)
        for g in v.groups:w[index[ob.vertex_groups[g.group].name]]=g.weight
        weights.append(w)
    for t in ob.data.loop_triangles:
        faces.append([off+i for i in t.vertices]);mat=ob.data.materials[t.material_index]
        if key=='props':label='props'
        elif 'Bare' in mat.name:
            wg=np.sum(np.asarray([weights[i] for i in faces[-1]]),axis=0);label='left' if names[int(np.argmax(wg))].endswith('_l') else 'right'
        else:label='gun'
        labels.append(label)
np.savez_compressed(O/'Diagnostics/saved_mesh_inputs.npz',vertices=verts,weights=weights,faces=faces,labels=labels,names=names,
 rest=[np.array(s['rest'][n]) for n in names],parents=[index.get(s['parents'][n],-1) for n in names],
 idle=[np.array(s['idle'][n]) for n in names],pose87=[np.array(s['pose'](87,7,False)[0][n]) for n in names],
 pose114=[np.array(s['pose'](114,7,False)[0][n]) for n in names],
 hand=np.array(s['hand_in_handle']),finger_names=s['finger_names']['l'],
 finger_local=[np.array(s['handle_fingers'][n]) for n in s['finger_names']['l']])
print('FIT_INPUTS',len(verts),len(faces),flush=True)
