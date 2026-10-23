"""Explicit boundary between NumPy/Blender author faces and UE mesh faces.

UE GeometryCore VectorUtil::Normal is (V2-V0).Cross(V1-V0). Author geometry
uses (V1-V0).Cross(V2-V0). Positions and normal vectors already share the
desired component axes, so only triangle corners and their attributes swap.
"""
AUTHOR_CONVENTION = 'cross_e1_e2'
UE_CONVENTION = 'cross_e2_e1'


def to_unreal(data):
    if data.get('geometry_convention') != AUTHOR_CONVENTION:
        raise ValueError('Backpack source must declare its triangle convention')
    out = dict(data)
    for field in ('triangles', 'uv', 'normals'):
        out[field] = [[row[0], row[2], row[1]] for row in data[field]]
    out['geometry_convention'] = UE_CONVENTION
    return out
