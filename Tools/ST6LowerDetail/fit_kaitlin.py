"""Fit only the new trim with the existing native Kaitlin surface correspondence."""
import json,sys,copy
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerDetail20261024';W=P/'SourceAssets/KaitlinPlayer20261023'
sys.path.insert(0,str(P/'Tools/KaitlinPlayer'))
from body_surface_fit import BodySurfaceFit,bind_warp,neighbors,regions
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
captured=read(W/'FitInputs/captured.json');body=read(W/'FitInputs/player_body.json');modular=read(W/'FitInputs/modular_outfits.json')
source=read(W/'FitInputs'/captured[modular['profiles'][body['body_mesh']]['native_bare_skin']]['file'])
target=read(W/'NativeGeometry/MHC_Kaitlin_Body.json');fit=BodySurfaceFit(source,target,read(W/'body_correspondence.json')['target_to_source_vertices'])
detail_names=['Jason_boots.json','Jason_pants.json','Jason_pants_HighBootsFit.json','Jason_pants_ShortBootsFit.json','Jason_pants_ST6BootsFit.json']
for file in [R/'Authored'/name for name in detail_names]:
    d=read(file);reg=regions(d);points=np.array(d['positions'])
    def warp(q):
        view=dict(d,positions=q);moved=bind_warp(view,target);near,ws=neighbors(moved,reg,fit.points,fit.regions)
        return moved+(fit.residual[near]*ws[:,:,None]).sum(1)
    result=fit.garment(d);out=copy.deepcopy(d);out['positions']=result['positions'];out['weights']=result['weights'];out['bones']=target['bones'];out['skeleton']=target['skeleton']
    eps=.004;jac=np.empty((len(points),3,3))
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(warp(points+delta)-warp(points-delta))/(2*eps)
    faces=np.array(d['triangles']);normal=np.einsum('fcij,fcj->fci',np.linalg.inv(jac).transpose(0,2,1)[faces],np.asarray(d['normals']))
    normal/=np.maximum(np.linalg.norm(normal,axis=2,keepdims=True),1e-12);out['normals']=normal.tolist()
    out['contract']+='; Kaitlin original bind and region surface field; base female garment retained'
    dest=R/'Authored'/file.name.replace('Jason_','Kaitlin_',1);dest.write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    print('ST6_KAITLIN_DETAIL_AUTHORED',dest.name,flush=True)
