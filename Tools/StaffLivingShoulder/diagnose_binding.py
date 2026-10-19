import bpy,bmesh,numpy as np,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/StaffLivingShoulder20261017'
report={}
for role,tool,sourceblend,name in [
 ('FemaleA','FacelessReceptionist/author_character_v02.py','FacelessReceptionist20261007/V04/Authoring/FacelessReceptionist_V04.blend','Receptionist'),
 ('FemaleB','FacelessResearcher/body_fit_helpers.py','FacelessResearcher20261009/V01/Authoring/FacelessResearcher_V01.blend','Researcher')]:
 text=(ROOT/'Tools'/tool).read_text(encoding='utf-8-sig')
 prefix=text[:text.index('def vertex_weights')]
 # Omit historical production folder/texture writes; this diagnostic only reads inputs.
 if 'for folder in ' in prefix:prefix=prefix[:prefix.index('for folder in ')]+prefix[prefix.index('bpy.ops.wm.open_mainfile'):]
 # Prefix only opens preserved input and recreates the original affine fit maps.
 ns={};exec(compile(prefix,'read_original_fit_maps','exec'),ns)
 original=ns['body'];p=np.array([v.co[:] for v in original.data.vertices]);tri=np.array([f.vertices[:] for f in original.data.polygons]);names=sorted(ns['MAP']);maps=np.array([np.array(ns['MAP'][n]) for n in names]);index={n:i for i,n in enumerate(names)}
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets'/sourceblend));body=bpy.data.objects[name+'_CompleteBody']
 assert len(body.data.vertices)==len(p)
 assert np.array_equal(tri,np.array([f.vertices[:] for f in body.data.polygons]))
 old=np.array([v.co[:] for v in body.data.vertices]);w=np.zeros((len(p),len(names)))
 for v in body.data.vertices:
  for g in v.groups:w[v.index,index[body.vertex_groups[g.group].name]]=g.weight
 fitted=np.einsum('vij,vj->vi',np.einsum('vb,bij->vij',w,maps),np.c_[old,np.ones(len(old))])[:,:3]
 _,weld=np.unique(np.round(p,6),axis=0,return_inverse=True);cnt=np.bincount(weld)
 mean=np.column_stack([np.bincount(weld,weights=w[:,j])/cnt for j in range(len(names))])[weld]
 gap=np.linalg.norm(w-mean,axis=1)
 report[role]={'source_vertex_count':len(p),'source_triangles':len(tri),'max_reconstruction_error':float(np.linalg.norm(fitted-p,axis=1).max()),'inconsistent_seam_weight_vertices':int(np.sum(gap>1e-5)),'max_seam_weight_delta':float(gap.max()),'seam_weight_region_bounds':[p[gap>1e-5].min(0).tolist(),p[gap>1e-5].max(0).tolist()] if np.any(gap>1e-5) else None}
 # Store exact source topology and current skin for the local repair, including UV split identity.
 np.savez_compressed(OUT/'Diagnosis'/f'{role}_binding.npz',source=p,current=old,weights=w,maps=maps,names=np.array(names),weld=weld,triangles=tri)
(OUT/'Diagnosis/binding_cause.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('BINDING_CAUSE',json.dumps(report),flush=True)
