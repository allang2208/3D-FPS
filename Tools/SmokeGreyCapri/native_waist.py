"""Keep the native waist in wearable capris; garment-only displays stay skin-free."""
REVISION='NativeWaistSeam20261012'

def append_native_waist(data,patch):
    if any(p['name']=='Native_WaistSeam' for p in data['parts']):
        return
    destination={b['name']:b['index'] for b in data['bones']}
    remap={b['index']:destination[b['name']] for b in patch['bones']}
    start=len(data['positions'])
    data['positions'].extend(patch['positions'])
    data['weights'].extend([[[remap[bi],w] for bi,w in weights] for weights in patch['weights']])
    data['triangles'].extend([[start+i for i in tri] for tri in patch['triangles']])
    data['uv'].extend(patch['uv'])
    data['normals'].extend(patch['normals'])
    data['triangle_materials'].extend([5]*len(patch['triangles']))
    data['parts'].append(dict(name='Native_WaistSeam',first_vertex=start,
        vertices=len(patch['positions']),triangles=len(patch['triangles']),material=5))
    data['contract']+='; '+REVISION+': restore only pants-hidden native waist faces above 90cm; original skin UVs and weights; overlap inside waistband'
