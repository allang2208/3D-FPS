"""Separate approved door metal from glass, author closed panes and Voronoi shard meshes.

Original local precision geometry, not a copy of the NDD plugin. No simulation/render.
FBX reverses V on import: metadata UVs below account for that and Blender -> UE Y.
"""
import json, math, random
from pathlib import Path
import bpy, bmesh

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'WardGlassDoors.blend'))
records=[]
paths=json.loads((OUT/'door-manifest.json').read_text(encoding='utf-8'))['objects'][0]['materials']
glass=bpy.data.materials.get('RS_Glass')

def cube(name,center,size,material=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center)
 o=bpy.context.object;o.name=name;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if material:o.data.materials.append(material)
 bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 return o

def export(obj,kind,boxes=(),shards=0):
 name='SM_Ward_'+kind;obj.name=name
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
 triangulate=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=triangulate.name)
 collisions=[cube('UCX_'+name+'_'+str(i).zfill(2),c,s) for i,(c,s) in enumerate(boxes)]
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True)
 for c in collisions:c.select_set(True)
 bpy.context.view_layer.objects.active=obj
 fbx=OUT/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
     bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
 for c in collisions:c.hide_set(True);c.hide_render=True
 obj.data.calc_loop_triangles()
 records.append(dict(name=name,kind=kind,fbx=str(fbx),materials=paths,triangles=len(obj.data.loop_triangles),
                     collision=bool(boxes),collision_boxes=len(boxes),nanite=False,sample_only=False,
                     assembly_only=True,full_precision_uvs=shards>0,fracture_shards=shards))
 print('WARD_GLASS_AUTHORED',name,len(obj.data.loop_triangles),shards,flush=True)

source=bpy.data.objects['SM_Ward_GlassDoorLeaf']
metal=source.copy();metal.data=source.data.copy();bpy.context.collection.objects.link(metal)
bm=bmesh.new();bm.from_mesh(metal.data)
glass_slots={i for i,m in enumerate(metal.data.materials) if m and m.name=='RS_Glass'}
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in glass_slots],context='FACES')
bm.to_mesh(metal.data);bm.free()
boxes=[((0,y,0),(.05,.07,2.95)) for y in (-.7625,.7625)]
boxes += [((0,0,z),(.05,1.455,.07)) for z in (-1.44,1.44)]
boxes += [((0,0,-1.27),(.048,1.455,.27)),((0,0,-.23),(.05,1.455,.055))]
boxes += [((x,-.7625,-.10),(.12,.052,.63)) for x in (-.048,.048)]
export(metal,'GlassDoorMetalV5',boxes)

def clipped(poly,n,limit):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=a[0]*n[0]+a[1]*n[1]-limit;db=b[0]*n[0]+b[1]*n[1]-limit
  if da<=0:result.append(a)
  if (da<=0)!=(db<=0):
   t=da/(da-db);result.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
 return result

def panes(kind,width,height,depth,nx,nz,seed):
 intact=cube('Pane',(0,0,0),(depth,width,height),glass)
 uv=intact.data.uv_layers.active or intact.data.uv_layers.new(name='UVMap')
 for loop in intact.data.loops:
  p=intact.data.vertices[loop.vertex_index].co
  uv.data[loop.index].uv=(p.y/width+.5,p.z/height+.5)
 export(intact,kind+'PaneV5',[((0,0,0),(depth,width,height))])
 rand=random.Random(seed)
 sites=[((x+.5+rand.uniform(-.43,.43))*width/nx-width/2,
         (z+.5+rand.uniform(-.43,.43))*height/nz-height/2) for x in range(nx) for z in range(nz)]
 vertices=[];faces=[];attributes=[]
 for index,site in enumerate(sites):
  poly=[(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)]
  for other in sites:
   if other==site:continue
   normal=(other[0]-site[0],other[1]-site[1])
   limit=(other[0]**2+other[1]**2-site[0]**2-site[1]**2)/2
   poly=clipped(poly,normal,limit)
   if len(poly)<3:break
  if len(poly)<3:continue
  cy=sum(p[0] for p in poly)/len(poly);cz=sum(p[1] for p in poly)/len(poly)
  radius=max(math.hypot(y-cy,z-cz) for y,z in poly)
  shrink=max(.90,1-.0005/max(.001,radius))
  poly=[(cy+(y-cy)*shrink,cz+(z-cz)*shrink) for y,z in poly]
  base=len(vertices);n=len(poly);piece_seed=rand.random()
  vertices.extend((x,y,z) for x in (-depth/2,depth/2) for y,z in poly)
  piece_faces=[tuple(base+i for i in reversed(range(n))),tuple(base+n+i for i in range(n))]
  piece_faces += [(base+i,base+(i+1)%n,base+n+(i+1)%n,base+n+i) for i in range(n)]
  faces.extend(piece_faces)
  attributes.extend((cy,cz,piece_seed,radius,i>=2) for i in range(len(piece_faces)))
 mesh=bpy.data.meshes.new(kind+'FractureMesh');mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(glass)
 uv0=mesh.uv_layers.new(name='UVMap');uv1=mesh.uv_layers.new(name='ShardCenter');uv2=mesh.uv_layers.new(name='ShardSeed')
 edge=mesh.color_attributes.new(name='FractureEdge',type='FLOAT_COLOR',domain='CORNER')
 for face,attr in zip(mesh.polygons,attributes):
  cy,cz,s,r,side=attr
  for li in face.loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co
   uv0.data[li].uv=(p.y/width+.5,p.z/height+.5)
   uv1.data[li].uv=(-cy/width+.5,.5-cz/height)
   uv2.data[li].uv=(s,1-r)
   edge.data[li].color=(1 if side else 0,0,0,1)
 obj=bpy.data.objects.new(kind+'Fracture',mesh);bpy.context.collection.objects.link(obj)
 export(obj,kind+'FractureV5',shards=len(sites))

panes('Door',1.42,2.50,.012,11,16,29551)
# Each observation opening has a retained 4 cm central metal mullion: one pane per side.
panes('Window',1.655,1.28,.016,12,8,29552)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WardBreakableGlassV5.blend'))
(OUT/'breakable-glass-manifest.json').write_text(json.dumps(dict(objects=records,revision='ward_glass_v5',
 source='Original ward mesh separation and local Voronoi half-plane clipping',
 uv_contract='UV1 normalized UE Y/Z centroid; UV2.x seed; vertex R fractured edge; FBX V inversion compensated',
 tests_run=False,rendered=False),indent=2),encoding='utf-8')
