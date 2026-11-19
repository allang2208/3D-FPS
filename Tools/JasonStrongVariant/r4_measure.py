"""Measure the same frontal contour interval previously reported for R3."""
import ast, math, json
from pathlib import Path
import numpy as np
from r4_pose import BASE,OUT,pose_values
here=Path(__file__).resolve().parent
r3=BASE/'R3_ArmsRefined'
head=json.loads((r3/'head_source.json').read_text());before=json.loads((r3/'AnatomyReview/derived_saved_mesh.json').read_text())
forms=json.loads((OUT/'Review/forms.json').read_text());after=dict(before,positions=forms['base'])
datasets=[before,after]
for data in datasets:data['head_z_cm']=4.5
def review_apply_forms(data,bind,posed):
    p=np.asarray(data['positions']).copy()
    if data is before:return p,{}
    values=pose_values(data,bind,posed)
    for name,weight in values.items():
        rows=np.array(forms['targets'][name]);p[rows[:,0].astype(int)]+=weight*rows[:,1:]
    return p,values
tree=ast.parse((here/'render_anatomy_review.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pose','elbow_axis','rotation')],type_ignores=[]),'<review>','exec'))
def contour(tri,x):
    cut=tri[(tri[:,:,0].min(1)<=x)&(tri[:,:,0].max(1)>=x)]
    heights=[]
    for i,j in [(0,1),(1,2),(2,0)]:
        a=cut[:,i];b=cut[:,j];mask=((a[:,0]-x)*(b[:,0]-x)<=0)&(a[:,0]!=b[:,0])
        a=a[mask];b=b[mask]
        heights.extend(a[:,2]+(b[:,2]-a[:,2])*(x-a[:,0])/(b[:,0]-a[:,0]))
    return max(heights)
out={}
for data,key in zip(datasets,['R3','R4']):
    q,h,_,_=pose(data,'shoulders_high');tri=np.concatenate([q[data['triangles']],h[head['triangles']]])
    xs=np.linspace(9.5,22,26);zs=np.array([contour(tri,x) for x in xs])
    out[key]=round(float(zs[xs>=14].max()-zs[xs<=13.5].min()),3)
tri=np.array(before['triangles']);old=np.array(before['positions']);flat=np.asarray(after['positions'])
def normals(p):return np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]])
base=normals(old)
def folds(p):return int(np.sum((base*normals(p)).sum(1)<-1e-8))
out['rest_flips_against_R3']=folds(flat)
all_on=flat.copy()
for target in forms['targets'].values():
    rows=np.asarray(target);all_on[rows[:,0].astype(int)]+=rows[:,1:]
out['all_correctives_bind_space_flips']=folds(all_on)
print(out);(OUT/'Review/contour.json').write_text(json.dumps(out,indent=2))
