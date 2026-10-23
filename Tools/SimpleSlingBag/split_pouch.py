"""Separate the stowed source strap at its two sewn tabs, and close both ports.

The original complete model remains the display source. No simplification is
applied to either source; UV charts stay on loop attributes during seam welding.
"""
import bpy,bmesh,json
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SimpleSlingBag20261022'
bpy.ops.wm.open_mainfile(filepath=str(R/'SimpleSlingBag_source.blend'));ob=bpy.data.objects['SimpleSlingBag_Source']
SCALE=.9

def buffers(mesh,folder):
    folder.mkdir(parents=True,exist_ok=True);mesh.calc_loop_triangles()
    positions=np.asarray([list(v.co) for v in mesh.vertices],np.float32)*100
    triangles=np.asarray([list(t.vertices) for t in mesh.loop_triangles],np.int32)
    loops=np.asarray([list(t.loops) for t in mesh.loop_triangles],np.int32)
    normals=np.asarray([list(n.vector) for n in mesh.corner_normals],np.float32)[loops].reshape(-1,3)
    uv=np.asarray([list(x.uv) for x in mesh.uv_layers.active.data],np.float32)[loops].reshape(-1,2);uv[:,1]=1-uv[:,1]
    keys=np.empty(len(normals),dtype=[('vertex','<i4'),('normal','<f4',(3,)),('uv','<f4',(2,))])
    keys['vertex']=triangles.ravel();keys['normal']=normals;keys['uv']=uv
    _,first,inverse=np.unique(keys,return_index=True,return_inverse=True)
    arrays={'positions':positions[triangles.ravel()[first]],'normals':normals[first],'uv':uv[first],
            'triangles':inverse.reshape(-1,3).astype('<i4'),'materials':np.array([t.material_index for t in mesh.loop_triangles],'<i4')}
    for name,values in arrays.items():values.tofile(folder/(name+'.bin'))
    metadata={'vertices':len(first),'triangles':len(triangles),'geometry_convention':'cross_e1_e2','positions_unit':'cm',
              'bounds_min':positions.min(0).tolist(),'bounds_max':positions.max(0).tolist()}
    (folder/'buffers.json').write_text(json.dumps(metadata,indent=2))
    return metadata,positions,triangles

display=ob.data.copy()
for vertex in display.vertices:vertex.co*=SCALE
display.update();original,_,_=buffers(display,R/'Authored/Display')
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
for point,normal in [(Vector((0,0,.132)),Vector((0,0,1))),(Vector((0,.03,0)),Vector((0,1,0)))]:
    cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,
                               plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
    edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
    if edges:
        closed=bmesh.ops.holes_fill(bm,edges=edges,sides=0)
        for face in closed['faces']:face.material_index=1;face.smooth=False
bm.normal_update()
# The two new caps need a real UV basis, even on their plain binding material.
# Keep every original loop UV; planar coordinates belong only to new seam faces.
uv_layer=bm.loops.layers.uv.active
for face in bm.faces:
    if face.material_index!=1:continue
    dominant=max(range(3),key=lambda axis:abs(face.normal[axis]))
    axes=[axis for axis in range(3) if axis!=dominant]
    for loop in face.loops:loop[uv_layer].uv=(loop.vert.co[axes[0]]/.08,loop.vert.co[axes[1]]/.08)
bm.to_mesh(ob.data);bm.free();me=ob.data
v=np.asarray([list(v.co) for v in me.vertices]);centre=(v.min(0)+v.max(0))/2
caps={}
for key,axis,value in [('top',2,.132),('bottom',1,.03)]:
    ids=set()
    for face in me.polygons:
        if face.material_index==1 and max(abs(v[i,axis]-value) for i in face.vertices)<1e-5:ids.update(face.vertices)
    if not ids:raise RuntimeError('Missing sealed strap interface '+key)
    caps[key]=((v[list(ids)].mean(0)-centre)*100*SCALE).tolist()
for vertex in me.vertices:vertex.co=(vertex.co-Vector(centre))*SCALE
me.update();ob.name='SimpleSlingBag_Pouch'
binding=bpy.data.materials.new('SlingSeamBinding');binding.diffuse_color=(.12,.085,.05,1);me.materials.append(binding)
metadata,positions,faces=buffers(me,R/'Authored/Pouch')
np.savez_compressed(R/'Authored/pouch_support.npz',positions=positions,triangles=faces)
report={'original_display':original,'pouch':metadata,'anchors_cm':caps,'pouch_source_center_m':centre.tolist(),'scale':SCALE,
        'operation':'two cuts at sewn shoulder tabs; source loop removed from wearable body only; both interfaces capped',
        'decimation_applied':False}
(R/'pouch_prepared.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(R/'SimpleSlingBag_pouch.blend'))
print('SLING_POUCH_PREPARED',json.dumps(report),flush=True)
