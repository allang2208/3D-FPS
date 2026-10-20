from surface import *
oldprofile=json.loads((O/'Inputs/svch_base.json').read_text())
candidate=np.load(O/'poses.npz')['after'] if (O/'poses.npz').exists() else None
data={'frames':{},'triangles':{}}
data['triangles']['coverage']=[t for t,m in zip(coverage['triangles'],coverage['material_ids']) if m!=2]
data['triangles']['glove']=glove['triangles']
data['triangles']['gun']=[t for t,m in zip(weapon['triangles'],weapon['material_ids']) if m>=2 and m not in (5,7)]
for frame in (6,20,40,64,68,75,90):
    row={}
    before=pose('quick_melee',frame,oldprofile)
    svd=comp(matrices(motion['clips']['quick_melee']['frames'][frame]))
    for name,p in [('rejected',before),('SVD',svd)]+([('candidate',candidate[frame])] if candidate is not None else []):
        row[name]={key:skinned(src,p,key=='coverage').tolist() for key,src in [('coverage',coverage),('glove',glove),('gun',weapon)]}
    data['frames'][str(frame)]=row
with gzip.open(O/'review-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('Prepared actual V9 coverage and glove surfaces',flush=True)
