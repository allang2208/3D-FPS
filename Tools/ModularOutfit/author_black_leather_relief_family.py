"""Transfer the sculpt and shared atlas to the current native black-glove family."""
import hashlib
import numpy as np
from scipy.spatial import cKDTree
import black_leather_relief_cuff as lib

R=lib.R


def atlas_uv(points,faces,master,tree):
    target=points[faces]
    _,chosen=tree.query(target.mean(1))
    original=np.asarray(master['canonical_positions'])[np.asarray(master['triangles'])[chosen]]
    uv=np.asarray(master['uv'])[chosen]
    ab=original[:,1]-original[:,0];ac=original[:,2]-original[:,0]
    aa=(ab*ab).sum(1);bb=(ab*ac).sum(1);cc=(ac*ac).sum(1)
    determinant=aa*cc-bb*bb
    output=[]
    for corner in range(3):
        ap=target[:,corner]-original[:,0]
        d=(ap*ab).sum(1);e=(ap*ac).sum(1)
        denom=np.maximum(determinant,1.e-18)
        b=(cc*d-bb*e)/denom;c=(aa*e-bb*d)/denom
        result=uv[:,0]*(1-b-c)[:,None]+uv[:,1]*b[:,None]+uv[:,2]*c[:,None]
        # Native copies have identical ordered points even when the UE import
        # splits every triangle (Bow). Match those corners exactly at UV seams.
        distance=np.linalg.norm(target[:,corner,None]-original,axis=2)
        closest=distance.argmin(1);exact=distance.min(1)<.002
        result[exact]=uv[np.arange(len(faces))[exact],closest[exact]]
        output.append(result)
    return np.stack(output,axis=1).tolist()


def main():
    master=lib.read(R/'Baked/M4.json');original=lib.read(R/'Sources/M4.json')
    anatomy=lib.read(lib.ANATOMY)['anatomy']
    triangles=np.asarray(master['triangles'])
    centers=np.asarray(master['canonical_positions'])[triangles].mean(1)
    tree=cKDTree(centers)
    manifest=[]
    for name,path in lib.read(R/'native-sources.json').items():
        raw=(R/'Sources'/(name+'.json')).read_bytes()
        source=lib.read(R/'Sources'/(name+'.json'))
        if name in ('Body','M4'):
            data=lib.read(R/'Baked'/(name+'.json'))
        else:
            points,normals,delta=lib.to_canonical(source,original)
            fields=lib.design_fields(points,normals,source['weights'],original['bones'],anatomy)
            offset=normals*fields['low'][:,None]
            positions=np.asarray(source['positions'])+np.einsum('nij,nj->ni',delta,offset)
            data=dict(source,positions=positions.tolist(),normals=lib.transported_normals(source,positions).tolist(),
                uv=atlas_uv(points,np.asarray(source['triangles']),master,tree),
                contract=master['contract'])
        data.pop('canonical_positions',None);data.pop('canonical_normals',None)
        output=R/'Authored'/(name+'.json');lib.write(output,data)
        manifest.append(dict(profile=name,authored=str(output),material_group='Body' if name=='Body' else 'M4',
            triangles=len(data['triangles']),source=path,source_sha256=hashlib.sha256(raw).hexdigest()))
        print('BLACK_LEATHER_NATIVE_AUTHORED',name,len(data['triangles']),flush=True)
    lib.write(R/'manifest.json',manifest)
    print('BLACK_LEATHER_FAMILY_COMPLETE',len(manifest),flush=True)


if __name__=='__main__':main()
