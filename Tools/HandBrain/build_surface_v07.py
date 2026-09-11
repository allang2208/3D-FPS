"""Locally refine connected hand surfaces while retaining UV and deform layers."""
import bpy,bmesh,json,sys
import numpy as np
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');o=r/'surface_v07';o.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(r/'sculpt_v06/HandBrain_Refined_Baked.blend'))
oldhigh=bpy.data.objects.get('HandBrain_Sculpt_High')
if oldhigh:bpy.data.objects.remove(oldhigh,do_unlink=True)
body=bpy.data.objects['HandBrain_Body'];bpy.context.view_layer.objects.active=body
bpy.ops.mesh.customdata_custom_splitnormals_clear()
features=json.loads((r/'sculpt_v06/projected_features.json').read_text())['features']
def area(coords):
 mask=np.zeros(len(coords),np.float32)
 for f in features:
  if f['kind'] not in ['bone','shaft','tendon','wrist']:continue
  c=np.array(f['center']);a=np.array(f['axis']);b=np.array(f['side']);n=np.array(f['normal'])
  L=max(f['length']*2,.028);W=max(f['width']*2,.023)
  ids=np.where(np.all(np.abs(coords-c)<max(L,W)*3+.025,axis=1))[0];d=coords[ids]-c
  w=np.exp(-.5*((d@a/L)**2+(d@b/W)**2+(d@n/.024)**2))
  mask[ids]=np.maximum(mask[ids],w)
 return np.clip((mask-.10)/.40,0,1)
bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
before={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges)}
mask=area(np.array([v.co[:] for v in bm.verts]));layer=bm.verts.layers.float.new('SurfaceRegion')
for v in bm.verts:v[layer]=float(mask[v.index]) if all(f.material_index==0 for f in v.link_faces) else 0
edges=[e for e in bm.edges if min(v[layer] for v in e.verts)>.15 and not e.is_boundary]
bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
bm.verts.ensure_lookup_table();bm.verts.index_update();bm.edges.ensure_lookup_table()
coords=np.array([v.co[:] for v in bm.verts],np.float64);base=coords.copy();mask=np.array([v[layer] for v in bm.verts])
for v in bm.verts:
 if v.is_boundary or any(f.material_index!=0 for f in v.link_faces):mask[v.index]=0
edge=np.array([[e.verts[0].index,e.verts[1].index] for e in bm.edges]);src=np.r_[edge[:,0],edge[:,1]];dst=np.r_[edge[:,1],edge[:,0]];degree=np.bincount(src,minlength=len(coords))
# Alternating Laplacian steps soften tessellation kinks with little net shrinkage.
for k in range(24):
 avg=np.stack([np.bincount(src,weights=coords[dst,j],minlength=len(coords)) for j in range(3)],axis=1)/np.maximum(degree[:,None],1)
 coords+=(avg-coords)*mask[:,None]*(.52 if k%2==0 else -.53)
 delta=coords-base;size=np.linalg.norm(delta,axis=1);coords=base+delta*np.minimum(1,.0035/np.maximum(size,1e-9))[:,None]
for v,co in zip(bm.verts,coords):v.co=co
bm.normal_update()
# Retain a distinct dorsal joint contour after relaxation; no uniform inflation.
norm=np.array([v.normal[:] for v in bm.verts]);change=np.zeros_like(coords)
for f in features:
 if f['kind'] not in ['bone','tendon']:continue
 c=np.array(f['center']);a=np.array(f['axis']);b=np.array(f['side']);n=np.array(f['normal']);L=f['length'];W=f['width']
 ids=np.where(np.all(np.abs(coords-c)<max(L,W)*3+.02,axis=1))[0];d=coords[ids]-c
 w=np.exp(-.5*((d@a/L)**2+(d@b/W)**2+(d@n/.014)**2))*np.clip((norm[ids]@n-.25)/.6,0,1)*mask[ids]
 change[ids]+=w[:,None]*n*(.0007 if f['kind']=='bone' else .00035)
coords+=change
for v,co in zip(bm.verts,coords):v.co=co
bm.normal_update();after={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges)}
assert after['boundary_edges']==before['boundary_edges']
bm.to_mesh(body.data);bm.free();body.data.update()
for p in body.data.polygons:p.use_smooth=True
attr=body.data.attributes.get('SurfaceRegion');assert attr
high=body.copy();high.data=body.data.copy();bpy.context.collection.objects.link(high);high.name='HandBrain_Sculpt_High'
for m in list(high.modifiers):high.modifiers.remove(m)
bpy.context.view_layer.objects.active=high
sub=high.modifiers.new('Fine surface bake','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
vcount=len(high.data.vertices);co=np.empty(vcount*3,np.float32);high.data.vertices.foreach_get('co',co);co=co.reshape(-1,3);normal=np.empty_like(co);high.data.vertices.foreach_get('normal',normal.ravel());detail=np.zeros_like(co)
for f in features:
 if f['kind'] not in ['crease','nail']:continue
 c=np.array(f['center']);a=np.array(f['axis']);b=np.array(f['side']);n=np.array(f['normal']);L=f['length'];W=f['width']
 ids=np.where(np.all(np.abs(co-c)<max(L,W)*3+.025,axis=1))[0];d=co[ids]-c;x=d@a;y=d@b
 gate=np.exp(-.5*(d@n/.014)**2)*np.clip((normal[ids]@n-.2)/.6,0,1)
 if f['kind']=='nail':
  rr=((x/L)**4+(y/W)**4)**.25;amount=(.0007*np.clip((1.12-rr)/.20,0,1)-.00065*np.exp(-((rr-1.15)/.18)**2))*gate
 else:amount=-.0004*np.exp(-.5*((x/L)**2+(y/W)**2))*gate
 detail[ids]+=amount[:,None]*n
high.data.vertices.foreach_set('co',(co+detail).ravel());high.data.update()
for i,m in enumerate(high.data.materials):
 m=m.copy();high.data.materials[i]=m;p=m.node_tree.nodes.get('Principled BSDF')
 for link in list(p.inputs['Normal'].links):m.node_tree.links.remove(link)
 tc=m.node_tree.nodes.new('ShaderNodeTexCoord');noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=650;m.node_tree.links.new(tc.outputs['Object'],noise.inputs['Vector'])
 bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00025;bump.inputs['Strength'].default_value=.22;m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs[0],p.inputs['Normal'])
high.hide_render=True;high.hide_set(True)
report={'before':before,'after':after,'high_vertices':vcount,'max_surface_shift_m':float(np.linalg.norm(coords-base,axis=1).max()),'local_refinement':True,'complete_anatomical_retopology':False}
(o/'surface_report.json').write_text(json.dumps(report,indent=2));(o/'material_report.json').write_text((r/'sculpt_v06/material_report.json').read_text());(o/'bake_manifest.json').write_text((r/'sculpt_v06/bake_manifest.json').read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(o/'HandBrain_Sculpt_Source.blend'))
print('SURFACE_V07_BUILT',report,flush=True)
