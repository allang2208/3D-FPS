"""Fit shared hammer designs to the host's real section rings, preserving motion contacts."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

P=Path(__file__).resolve().parent; ROOT=P.parents[2]
ANGLE=np.linspace(0.,2*math.pi,257)
HOST_CX=-.0004452141001820564
TARGET_CUTS={'tail':-.085,'wrap':.405,'neck':.842,'left':HOST_CX-.035,'right':HOST_CX+.035}
SOURCE_CUTS={'tail':-.085,'wrap':.405,'neck':.865,'left':-.04,'right':.04}
PIVOTS={'head_mount':(0,0,0),'hammer_heads':(0,0,.916),'grip':(0,0,.405),'pommel':(0,0,-.085)}
OLD_PIVOTS={'head_mount':(0,0,0),'hammer_heads':(0,0,.925),'grip':(0,0,.405),'pommel':(0,0,-.085)}

def geometry(obj, transform=None):
    mesh=obj.data; mesh.calc_loop_triangles()
    q=np.array([tuple(v.co) for v in mesh.vertices])
    if transform is not None:q=np.array([tuple(transform@Vector(v)) for v in q])
    return q,np.array([tuple(t.vertices) for t in mesh.loop_triangles]),mesh

bpy.ops.wm.open_mainfile(filepath=str(P.parent/'RuneboundWarhammer_Editable.blend'))
host_v,host_f,host_mesh=geometry(bpy.data.objects['SM_RuneboundWarhammer'])
host_uv=np.array([[tuple(host_mesh.uv_layers[0].data[i].uv) for i in t.loops] for t in host_mesh.loop_triangles])
host_bvh=BVHTree.FromPolygons([Vector(v) for v in host_v],host_f.tolist(),all_triangles=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/SteelWarhammer20261014/SprintDragV1/RigSource/SteelWarhammer_Editable.blend'))
old=bpy.data.objects['SM_SteelWarhammer']; rig=old.parent
source_v,source_f,_=geometry(old,rig.data.bones['WPN_root'].matrix_local.inverted()@rig.matrix_world.inverted()@old.matrix_world)

def section(v,faces,axis,value):
    t=v[faces]; coords=t[:,:,axis]
    t=t[(coords.min(1)<=value)&(coords.max(1)>=value)]
    cuts=[]
    for tri in t:
        points=[]
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            if (a[axis]<=value<b[axis]) or (b[axis]<=value<a[axis]):
                points.append(a+(b-a)*(value-a[axis])/(b[axis]-a[axis]))
        if len(points)==2:cuts.append(points)
    if not cuts:raise RuntimeError('No source mounting ring at '+str((axis,value)))
    segments=np.array(cuts);axes=[a for a in range(3) if a!=axis]
    segments=segments[:,:,axes]
    center=(segments.reshape(-1,2).min(0)+segments.reshape(-1,2).max(0))*.5
    a=segments[:,0]-center;e=segments[:,1]-segments[:,0]
    direction=np.stack((np.cos(ANGLE),np.sin(ANGLE)),axis=1)
    cross=lambda x,y:x[...,0]*y[...,1]-x[...,1]*y[...,0]
    den=cross(direction[:,None,:],e[None,:,:]);valid=np.abs(den)>1.e-12
    safe=np.where(valid,den,1.)
    distance=cross(a,e)[None,:]/safe
    u=cross(a[None,:,:],direction[:,None,:])/safe
    radii=np.where(valid&(distance>0)&(u>=-1.e-6)&(u<=1+1.e-6),distance,0.).max(1)
    good=radii>1.e-7
    if good.sum()<200:raise RuntimeError('Incomplete mounting section at '+str((axis,value)))
    radii=np.interp(ANGLE,ANGLE[good],radii[good],period=2*math.pi)
    return {'center':center,'radii':radii,'segments':segments}

sections={}
for name,value in SOURCE_CUTS.items():
    axis=0 if name in ('left','right') else 2
    sections[name]=(section(source_v,source_f,axis,value),section(host_v,host_f,axis,TARGET_CUTS[name]))
zg=np.linspace(-.085,.405,41)
grip_source=[section(source_v,source_f,2,z) for z in zg]
grip_target=[section(host_v,host_f,2,z) for z in zg]

def ring_map(q,source,target):
    delta=q-source['center'];angle=np.mod(np.arctan2(delta[:,1],delta[:,0]),2*math.pi)
    rs=np.interp(angle,ANGLE,source['radii']);rt=np.interp(angle,ANGLE,target['radii'])
    return target['center']+delta*(rt/np.maximum(rs,1.e-7))[:,None]

def ease(x):
    x=np.clip(x,0.,1.);return x*x*(3.-2.*x)

def deform(p,slot):
    out=p.copy()
    if slot=='grip':
        z=np.clip(p[:,2],zg[0],zg[-1]);i=np.clip(np.searchsorted(zg,z)-1,0,len(zg)-2)
        a=(z-zg[i])/(zg[i+1]-zg[i])
        for j in np.unique(i):
            mask=i==j
            q0=ring_map(p[mask,:2],grip_source[j],grip_target[j])
            q1=ring_map(p[mask,:2],grip_source[j+1],grip_target[j+1])
            out[mask,:2]=q0*(1-a[mask,None])+q1*a[mask,None]
    elif slot=='pommel':
        q=ring_map(p[:,:2],*sections['tail'])
        w=1-ease((-.085-p[:,2])/.028)
        out[:,:2]=p[:,:2]*(1-w[:,None])+q*w[:,None]
    else:
        if slot=='head_mount':
            out[:,0]=HOST_CX+p[:,0]*.875
            out[:,2]=.842+(p[:,2]-.865)*(.990-.842)/(.990-.865)
        else:
            out[:,0]=p[:,0]+np.sign(p[:,0])*(-.005)+HOST_CX
            out[:,2]-=.009
        # Both alternative seats and paired heads share exactly the same side ring map.
        for side in ('left','right'):
            w=1-ease(np.abs(p[:,0]-SOURCE_CUTS[side])/.025)
            q=ring_map(p[:,1:3],*sections[side])
            out[:,1:3]=out[:,1:3]*(1-w[:,None])+q*w[:,None]
        if slot=='head_mount':
            w=1-ease(np.abs(p[:,2]-.865)/.018)
            q=ring_map(p[:,:2],*sections['neck'])
            out[:,:2]=out[:,:2]*(1-w[:,None])+q*w[:,None]
    return out

jobs=[
 ('hammer_heads','CommonHammerHeads20261014/DesignBuildV2','CommonHammerHeads_DesignV2_Editable.blend'),
 ('hammer_heads','CommonHammerSpecialHeads20261014/PointedHammer/BuildV1','PointedHammer_Editable.blend'),
 ('head_mount','CommonHammerSeats20261014/BuildV1','CommonHammerSeats_Editable.blend'),
 ('grip','CommonHammerGrips20261014/BuildV1','CommonHammerGrips_Editable.blend'),
 ('pommel','CommonHammerPommels20261014/BuildV1','CommonHammerPommels_Editable.blend'),
 ('pommel','CommonHammerPommels20261014/NoPommelV1','NoPommel_EndClosure_Editable.blend'),
]
bpy.ops.wm.open_mainfile(filepath=str(P/'RuneboundWarhammer_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
host_material=bpy.data.objects['SM_RuneboundWarhammer_shaft_factory'].data.materials[0]
rows=[]
for slot,folder,blend in jobs:
    source=ROOT/'SourceAssets'/folder
    # The selected pointed-head author's actual editable filename is in its own folder.
    candidates=[source/blend]
    if not candidates[0].exists():
        candidates=list(source.glob('*Editable.blend'))
        if len(candidates)!=1:raise RuntimeError('Ambiguous shared author: '+str(source))
    blend=candidates[0]
    entries=json.loads((source/'exports.json').read_text(encoding='utf-8-sig'))['parts']
    for row in entries:
        with bpy.data.libraries.load(str(blend),link=False) as (a,b):
            if row['mesh'] not in a.objects:raise RuntimeError('Shared object not found: '+row['mesh'])
            b.objects=[row['mesh']]
        obj=b.objects[0];bpy.context.scene.collection.objects.link(obj)
        obj.parent=None;obj.matrix_world=Matrix.Identity(4)
        mesh=obj.data;mesh.calc_loop_triangles()
        old_pivot=np.array(OLD_PIVOTS[slot]);new_pivot=np.array(PIVOTS[slot])
        points=np.array([tuple(v.co) for v in mesh.vertices])+old_pivot
        normals=np.array([tuple(n.vector) for n in mesh.corner_normals])
        result=deform(points,slot)
        jac=np.empty((len(points),3,3))
        for k in range(3):
            shift=np.zeros(3);shift[k]=2.e-6
            jac[:,:,k]=(deform(points+shift,slot)-deform(points-shift,slot))/4.e-6
        loops=np.array([l.vertex_index for l in mesh.loops])
        inverse=np.linalg.pinv(jac).transpose(0,2,1)
        normals=np.einsum('nij,nj->ni',inverse[loops],normals)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-10)
        mesh.vertices.foreach_set('co',(result-new_pivot).astype(np.float32).ravel());mesh.update()
        # Factory connector portions retain the host PBR rather than donor UV artwork.
        native_indices=[i for i,m in enumerate(mesh.materials) if m and m.name.split('.')[0]=='M_SteelWarhammerSurface']
        for index in native_indices:mesh.materials[index]=host_material
        for face in mesh.polygons:
            if face.material_index not in native_indices:continue
            for li in face.loop_indices:
                point=Vector(result[mesh.loops[li].vertex_index])
                nearest,_,ti,_=host_bvh.find_nearest(point)
                if ti is None:raise RuntimeError('Host connector projection failed')
                tri=host_v[host_f[ti]];uvs=host_uv[ti]
                mapped=barycentric_transform(nearest,*[Vector(v) for v in tri],*[Vector((u,v,0)) for u,v in uvs])
                mesh.uv_layers[0].data[li].uv=mapped.xy
        mesh.normals_split_custom_set(normals.tolist())
        name='SM_RuneboundWarhammer_'+slot+'_'+row['id']
        obj.name=name
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},
            axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
        obj.location=Vector(new_pivot)
        mesh.calc_loop_triangles()
        rows.append({'slot':slot,'id':row['id'],'mesh':name,'location_cm':[float(new_pivot[0]*100),float(-new_pivot[1]*100),float(new_pivot[2]*100)],
            'source_blend':str(blend),'source_mesh':row['mesh'],'triangles':len(mesh.loop_triangles),
            'materials':[m.name for m in mesh.materials]})
        print('HOST_FITTED_SHARED_PART '+slot+' '+row['id'],flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneboundWarhammer_SharedParts_Editable.blend'))
(P/'adapted_exports.json').write_text(json.dumps({'parts':rows,'tested':False,'method':'actual installation section rings, smooth local fitting, host connector PBR'},indent=2),encoding='utf-8')
interface_data={k:{'source_cut':SOURCE_CUTS[k],'target_cut':TARGET_CUTS[k],
    'source_center':a['center'].tolist(),'target_center':b['center'].tolist(),
    'source_radii':a['radii'].tolist(),'target_radii':b['radii'].tolist(),
    'target_segments':b['segments'].tolist()} for k,(a,b) in sections.items()}
(P/'shared_interfaces.json').write_text(json.dumps(interface_data,indent=2),encoding='utf-8')
print('HOST_FITTED_SHARED_PARTS_COMPLETE',flush=True)
