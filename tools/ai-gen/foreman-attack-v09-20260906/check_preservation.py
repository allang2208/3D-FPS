"""Compare the actual V08/V09 exported geometry, skin and unaffected animation."""
from pathlib import Path
import json,struct,numpy as np
R=Path(__file__).resolve().parent
def read_glb(path):
    b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);blob=b[28+n:]
    def acc(i):
        a=d['accessors'][i];v=d['bufferViews'][a['bufferView']]
        dt=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
        w={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        return np.ndarray((a['count'],w),dtype=dt,buffer=blob,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',w*dt.itemsize),dt.itemsize)).copy()
    channels={}
    for anim in d['animations']:
        for c in anim['channels']:
            sampler=anim['samplers'][c['sampler']]
            key=(anim['name'],d['nodes'][c['target']['node']]['name'],c['target']['path'])
            channels[key]=(acc(sampler['input']),acc(sampler['output']))
    return d,blob,acc,channels
d0,b0,r0,c0=read_glb(R.parent/'foreman-retopo-v08-20260906/foreman-retopo-v08.glb')
d1,b1,r1,c1=read_glb(R/'foreman-attack-v09.glb')
assert c0.keys()==c1.keys()
unchanged=0;changed=[]
for key,(t0,v0) in c0.items():
    t1,v1=c1[key]
    if key[0]!='Attack':
        assert np.array_equal(t0,t1) and np.allclose(v0,v1,atol=1e-6),key
        unchanged+=1
    elif not (v0.shape==v1.shape and np.allclose(v0,v1,atol=1e-6)):
        changed.append(key)
    if key[0]=='Attack':
        assert np.allclose(v0[[0,-1]],v1[[0,-1]],atol=1e-5),('attack endpoints',key)
assert len(d0['meshes'])==len(d1['meshes'])
for m0,m1 in zip(d0['meshes'],d1['meshes']):
    assert len(m0['primitives'])==len(m1['primitives'])
    for p0,p1 in zip(m0['primitives'],m1['primitives']):
        assert p0['attributes'].keys()==p1['attributes'].keys()
        for key in p0['attributes']:
            assert np.array_equal(r0(p0['attributes'][key]),r1(p1['attributes'][key])),('mesh',m0['name'],key)
        assert np.array_equal(r0(p0['indices']),r1(p1['indices']))
for s0,s1 in zip(d0['skins'],d1['skins']):
    assert s0['joints']==s1['joints']
    assert np.array_equal(r0(s0['inverseBindMatrices']),r1(s1['inverseBindMatrices']))
assert d0['materials']==d1['materials']
for i0,i1 in zip(d0['images'],d1['images']):
    v0=d0['bufferViews'][i0['bufferView']];v1=d1['bufferViews'][i1['bufferView']]
    assert b0[v0['byteOffset']:v0['byteOffset']+v0['byteLength']]==b1[v1['byteOffset']:v1['byteOffset']+v1['byteLength']]
report={'unaffected_animation_channels':unchanged,'changed_attack_channels':len(changed),
    'mesh_uv_normals_skin_weights_exact':True,'inverse_bind_matrices_exact':True,
    'materials_and_texture_bytes_exact':True,'attack_endpoints_preserved':True}
(R/'preservation-validation.json').write_text(json.dumps(report,indent=2))
print('FOREMAN_V09_PRESERVATION_COMPLETE',json.dumps(report))
