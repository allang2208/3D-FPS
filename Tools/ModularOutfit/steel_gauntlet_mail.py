"""Thin articulated mail on the native glove, below independent rigid plates."""
import numpy as np
import bpy
import build_metal_gauntlet_sample as s

def build(d,anatomy,side,rig,mat):
    directions={q['bone']:s.unit(q['dorsal']) for q in anatomy[side]['digits']}
    dorsal=s.unit(anatomy[side]['dorsal'])
    points=np.asarray(d['positions']);triangles=np.asarray(d['triangles'])
    normals=np.asarray(d['normals']);vertex_normals=np.zeros_like(points)
    for corner in range(3):np.add.at(vertex_normals,triangles[:,corner],normals[:,corner])
    vertex_normals/=np.maximum(1e-12,np.linalg.norm(vertex_normals,axis=1)[:,None])
    ids=[]
    for fi,face in enumerate(triangles):
        if not all(sum(v for b,v in d['weights'][i].items() if b.endswith('_'+side))>.5 for i in face):continue
        direction=sum((directions.get(b,dorsal)*w for i in face for b,w in d['weights'][i].items()),np.zeros(3))
        normal=normals[fi].mean(0)
        if normal@s.unit(direction)>.10:ids.append(fi)
    faces=triangles[ids];used=np.unique(faces);remap={int(v):i for i,v in enumerate(used)}
    positions=points[used]+vertex_normals[used]*.035
    obj=s.mesh_object('FlexibleMail_'+side,positions,[[remap[int(v)] for v in f] for f in faces],mat)
    uv=obj.data.uv_layers.new(name='SteelPanelUV')
    for poly,fi in zip(obj.data.polygons,ids):
        for li,(u,v) in zip(poly.loop_indices,d['uv'][fi]):uv.data[li].uv=(u,1-v)
    weights=[d['weights'][int(i)] for i in used]
    for name in {b for w in weights for b in w}:
        group=obj.vertex_groups.new(name=name)
        for i,w in enumerate(weights):
            if name in w:group.add([i],w[name],'REPLACE')
    obj.parent=rig;arm=obj.modifiers.new('NativeFlexibleJointBinding','ARMATURE');arm.object=rig
    atlas=obj.data.uv_layers.new(name='SteelSampleUV');obj.data.uv_layers.active=atlas
    for layer in obj.data.uv_layers:layer.active_render=layer.name=='SteelSampleUV'
    obj.color=(.25,.25,.70,1.)
    obj['Construction']='Flexible fine mail follows native liner weights; rigid plates are separate'
    s.PARTS.append(dict(name=obj.name,bone='hand_'+side,kind='flexible_mail',object=obj,weights=weights))
