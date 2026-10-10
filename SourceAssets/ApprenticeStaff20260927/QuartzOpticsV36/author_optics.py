"""Author a bounded convex optical proxy from the installed quartz triangles.

No runtime mesh, normal, UV or collision changes. Tiny bevel planes are omitted
from the optical proxy; the rendered V35 bevel remains intact. Not a volume
raymarch or multi-interface refraction renderer.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def author(source):
    p = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
    vertices = source['vertices_cm']
    groups = {}
    total_area = 0.
    for ids in source['triangles']:
        a, b, c = [vertices[i] for i in ids]
        n = cross(sub(b, a), sub(c, a))
        twice_area = math.sqrt(dot(n, n))
        if twice_area < 1.e-7:
            continue
        n = [x / twice_area for x in n]
        key = tuple(round(x, 3) for x in n)
        group = groups.setdefault(key, {'normal': n, 'area': 0.})
        group['area'] += twice_area * .5
        total_area += twice_area * .5
    selected = sorted(groups.values(), key=lambda g: g['area'], reverse=True)
    selected = [g for g in selected if g['area'] >= total_area*p['minimum_plane_area_fraction']]
    selected = selected[:p['max_macro_planes']]
    lo = [min(v[k] for v in vertices) for k in range(3)]
    hi = [max(v[k] for v in vertices) for k in range(3)]
    # Support planes enclose the real vertices even when an authored surface is
    # slightly concave. Six bounds guarantee a finite ray exit in every direction.
    normals = [g['normal'] for g in selected]
    normals += [[s if i == k else 0. for i in range(3)] for k in range(3) for s in (-1., 1.)]
    planes = []
    for n in normals:
        if any(dot(n, plane[:3]) > .99999 for plane in planes):
            continue
        planes.append(n + [max(dot(n, v) for v in vertices) + .002])
    data = dict(revision=36, source=source['source'], bounds_min_cm=lo, bounds_max_cm=hi,
                planes=planes, authored_in='UE mesh local centimetres',
                method='area-selected convex support planes; small bevels approximated',
                runtime_geometry_changed=False)
    (ROOT / 'optical-geometry.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    lines = [
        '// V36: actual installed mesh local coordinates, cm. No SceneDepth.',
        'float3 V = normalize(CameraLocal - PositionLocal);',
        'float3 N = normalize(NormalLocal);',
        'N = dot(N,V) < 0 ? -N : N;',
        'float3 D = normalize(refract(-V, N, rcp(max(IOR, 1.001))));',
        'float3 P = PositionLocal + D * 0.004;',
        'float exitDistance = 1000.0;',
    ]
    for i, plane in enumerate(planes):
        values = ','.join(f'{x:.9f}' for x in plane)
        lines += [f'float4 plane{i}=float4({values});',
                  f'float den{i}=dot(plane{i}.xyz,D);',
                  f'if(den{i}>0.00001) exitDistance=min(exitDistance,max(0.0,(plane{i}.w-dot(plane{i}.xyz,P))/den{i}));']
    lines += [
        'float pathCm=clamp(exitDistance+0.004,0.004,40.0);',
        '// Substrate applies refracted angular transmission itself. Convert our',
        '// finite chord back to the equivalent normal depth to avoid doubling it.',
        'float normalDepth=pathCm*max(0.05,abs(dot(-D,N)));',
        f'float root=1-smoothstep({lo[2]:.7f},{lo[2]+(hi[2]-lo[2])*.38:.7f},PositionLocal.z);',
        'return float3(normalDepth,pathCm,root);',
    ]
    (ROOT / 'OpticalChord.hlsl').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return data
