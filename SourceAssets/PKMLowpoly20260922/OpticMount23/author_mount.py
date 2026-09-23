"""PKM-specific, cover-conforming optic adapter; only the adapter is exported."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

O=Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
rig=bpy.data.objects['PKM_Manny_Rig'];rig.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=rig.data.bones['WPN_root'].matrix_local@fit;Bi=B.inverted()
cover=Vector((0,-.021,.070));surface=bpy.data.objects['PKM_Part_043']
surface.data.calc_loop_triangles()
vertices=[Bi@surface.matrix_world@v.co for v in surface.data.vertices]
triangles=[list(t.vertices) for t in surface.data.loop_triangles]
uvs=[[Vector((*surface.data.uv_layers[0].data[i].uv,0)) for i in t.loops] for t in surface.data.loop_triangles]
bvh=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
def contact(x,y):
 p,n,i,d=bvh.ray_cast(Vector((x,y,.2)),Vector((0,0,-1)))
 if p is None:raise RuntimeError('Missing cover contact at '+str((x,y)))
 return p,i

# Capture an actual clean patch of the installed receiver atlas. The UE
# receiver graph itself is copied later, retaining its channel conversion.
size=512;uvmap=np.empty((size,size,2),dtype=np.float32)
for row in range(size):
 y=.025+.05*(row+.5)/size
 for col in range(size):
  x=-.012+.024*(col+.5)/size;p,i=contact(x,y)
  tri=triangles[i];uv=barycentric_transform(p,*(vertices[j] for j in tri),*uvs[i])
  uvmap[row,col]=uv[:2]
np.save(O/'receiver_patch_uv.npy',uvmap)

mat=bpy.data.materials.new('PKM23_ReceiverMetal');mat.use_nodes=True
bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.025,.029,.033,1)
bs.inputs['Metallic'].default_value=.72;bs.inputs['Roughness'].default_value=.36
mat.diffuse_color=(.085,.10,.115,1)
new=[];contacts=[]
def finish(ob,width=.00025):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 ob.data.materials.clear();ob.data.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(ob.data);bm.free()
 bevel=ob.modifiers.new('Machined edge','BEVEL');bevel.width=width;bevel.segments=3
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 triangulate=ob.modifiers.new('Export triangles','TRIANGULATE')
 bpy.ops.object.modifier_apply(modifier=triangulate.name)
 for p in ob.data.polygons:p.use_smooth=True
 norm=ob.modifiers.new('Weighted normals','WEIGHTED_NORMAL');norm.keep_sharp=True
 bpy.ops.object.modifier_apply(modifier=norm.name)
 # Physical projection onto the receiver-patch scale; UV0 and tangent source
 # agree. Spare UV channels are retained for future coating variants.
 for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer)
 uv=ob.data.uv_layers.new(name='ReceiverMetalUV')
 for face in ob.data.polygons:
  axis=max(range(3),key=lambda k:abs(face.normal[k]));axes=[k for k in range(3) if k!=axis]
  for li in face.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co+cover
   uv.data[li].uv=(p[axes[0]]/.024,p[axes[1]]/.05)
 for label in ['SourceUV','PKM_CoatingUV']:
  layer=ob.data.uv_layers.new(name=label)
  for a,b in zip(layer.data,uv.data):a.uv=b.uv
 ob.data.uv_layers.active_index=0;ob['PKM23_part']=True;new.append(ob)
 return ob
def mesh(name,points,faces,width=.00025):
 data=bpy.data.meshes.new(name);data.from_pydata([Vector(p)-cover for p in points],[],faces);data.update()
 ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob)
 return finish(ob,width)
def extrusion(name,profile,y0,y1,width=.00025):
 count=len(profile);points=[(x,y,z) for y in [y0,y1] for x,z in profile]
 faces=[list(reversed(range(count))),list(range(count,2*count))]
 faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
 return mesh(name,points,faces,width)

# Each foot has a sampled lower surface, rather than burying a rectangular
# block 3.7 mm into the lid. The rear foot follows the narrower raised strip.
for label,y0,y1,half in [('Front',.014,.043,.016),('Rear',.099,.126,.012)]:
 points=[];nx,ny=5,3
 for layer in range(2):
  for j in range(ny):
   y=y0+(y1-y0)*j/(ny-1)
   for i in range(nx):
    x=-half+2*half*i/(nx-1)
    if layer:points.append((x*(.011/half),(y0+y1)*.5+(y-(y0+y1)*.5)*.84,.104))
    else:
     p,_=contact(x,y);points.append((x,y,p.z-.00012));contacts.append({'foot':label,'point':list(p)})
 faces=[];count=nx*ny
 for j in range(ny-1):
  for i in range(nx-1):
   k=j*nx+i;faces += [(k,k+nx,k+nx+1,k+1),(k+count,k+count+1,k+count+nx+1,k+count+nx)]
 perimeter=list(range(nx))+[j*nx+nx-1 for j in range(1,ny)]+list(range((ny-1)*nx+nx-2,(ny-1)*nx-1,-1))+[j*nx for j in range(ny-2,0,-1)]
 for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append((a,b,b+count,a+count))
 mesh('PKM23_'+label+'ContouredFoot',points,faces,.0002)

extrusion('PKM23_TaperedSpine',[(-.007,.1035),(.007,.1035),(.0088,.1095),(-.0088,.1095)],.010,.132,.00045)
profile=[(-.0078,.1088),(.0078,.1088),(.0105,.1111),(.0105,.1129),(.009,.1144),(-.009,.1144),(-.0105,.1129),(-.0105,.1111)]
for i in range(13):
 y=.015+i*.009;extrusion('PKM23_RailLug_%02d'%i,profile,y-.00275,y+.00275,.00018)
# Small recessed fastener heads on the exposed foot shoulders.
for y in [.0285,.1125]:
 for x in [-.0094,.0094]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.00165,depth=.00065,location=Vector((x,y,.1041))-cover)
  ob=bpy.context.object;ob.name='PKM23_Fastener';ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
  finish(ob,.00012)

bpy.ops.object.select_all(action='DESELECT')
for ob in new:ob.select_set(True)
bpy.context.view_layer.objects.active=new[0]
bpy.ops.export_scene.fbx(filepath=str(E/'SM_PKM_optic_rail.fbx'),use_selection=True,object_types={'MESH'},
 axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
# Saved author scene retains the receiver context and real hinged-cover origin.
for ob in new:ob.matrix_world=B@Matrix.Translation(cover)
for ob in bpy.context.scene.objects:
 if ob.type=='MESH' and not ob.get('PKM23_part'):
  ob.hide_render=not ob.name.startswith('PKM_Part_')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_OpticMount_Editable.blend'))
report={'source':'Motion21/PKM_HingedOutlet_Editable.blend','part':'PKM optic cover adapter',
 'rail_y_m':[.010,.132],'rail_top_gun_z_m':.1144,'optic_mount_cover_z_m':.0444,
 'rail_length_old_new_mm':[173,122],'top_height_old_new_mm':[123.5,114.4],
 'width_max_mm':32,'tooth_width_mm':21,'contacts':contacts,'material_slot':'PKM23_ReceiverMetal',
 'uv_scale_m':[.024,.05],'patch_source':'Installed receiver BaseColor/ORM; flat top x=-.012..+.012, y=.025..+.075',
 'geometry_normal':'Weighted geometric normals and bevels; no unrelated atlas normal',
 'export':str(E/'SM_PKM_optic_rail.fbx'),'objects':len(new),'triangles':sum(len(o.data.polygons) for o in new)}
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('PKM23_AUTHORED',len(new),flush=True)
