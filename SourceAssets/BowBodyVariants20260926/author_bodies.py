"""Continuous body variations with retained contact geometry and string notches."""
import bpy,bmesh,json,math,bisect
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
WOOD=P.parent/'DarkBow20260925/WoodLongbow20260925'
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BowModular20260926/Bow_ModularParts.blend'))
bpy.context.preferences.filepaths.save_version=0
src=bpy.data.objects['SM_Bow_BodyModular'];data=src.data.copy()
keep=set(json.loads((P/'donor-inputs.json').read_text())['wood_ids'])
bm=bmesh.new();bm.from_mesh(data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS');bm.to_mesh(data);bm.free()
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
coords=[v.co.copy() for v in data.vertices];mid=-.5468215942382812
# True edge/plane sections supply local centres without bounding-box rescaling.
sections=[]
zmin=min(v.z for v in coords);zmax=max(v.z for v in coords)
for step in range(285):
 z=zmin+.02+(zmax-zmin-.04)*step/284;pts=[]
 for edge in data.edges:
  a,b=(coords[i] for i in edge.vertices)
  if (a.z<=z<b.z) or (b.z<=z<a.z):pts.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
 if pts:sections.append((z,*[(min(p[j] for p in pts)+max(p[j] for p in pts))*.5 for j in [0,1]],*[(max(p[j] for p in pts)-min(p[j] for p in pts))*.5 for j in [0,1]]))
zz=[s[0] for s in sections]
def section(z):
 i=max(0,min(len(zz)-2,bisect.bisect_right(zz,z)-1));a,b=sections[i:i+2]
 t=max(0,min(1,(z-a[0])/(b[0]-a[0])));return [a[j]*(1-t)+b[j]*t for j in range(1,5)]
def smooth(x):x=max(0,min(1,x));return x*x*x*(x*(x*6-15)+10)
def weights(z):
 a=abs(z-mid);return smooth((a-21)/11)*smooth((68-a)/10),smooth((a-21)/8)*smooth((68-a)/4)
def image_node(m,path,uv,noncolor=False):
 n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True)
 n.image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB';m.node_tree.links.new(uv.outputs['UV'],n.inputs['Vector']);return n
def material(name):
 m=bpy.data.materials.new('M_Bow_Body_'+name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
 p=next(n for n in n if n.type=='BSDF_PRINCIPLED');p.inputs['Metallic'].default_value=0
 uv0=n.new('ShaderNodeUVMap');uv0.uv_map=data.uv_layers[0].name
 uv1=n.new('ShaderNodeUVMap');uv1.uv_map='TimberUV'
 attr=n.new('ShaderNodeVertexColor');attr.layer_name='LimbBlend'
 split=n.new('ShaderNodeSeparateColor');l.new(attr.outputs['Color'],split.inputs['Color'])
 for i,(suffix,inputname) in enumerate([('BaseColor','Base Color'),('ORM','Roughness'),('Normal','Normal')]):
  old=image_node(m,WOOD/'Textures'/('Image_'+str(i)+'.png'),uv0,i>0)
  new=image_node(m,P/'Textures'/('T_Bow_'+name+'_'+suffix+'.png'),uv1,i>0)
  first,second=old.outputs['Color'],new.outputs['Color']
  if i==2:
   for texture,uvname in [(old,data.uv_layers[0].name),(new,'TimberUV')]:
    nm=n.new('ShaderNodeNormalMap');nm.uv_map=uvname;nm.inputs['Strength'].default_value=.6;l.new(texture.outputs['Color'],nm.inputs['Color'])
    if texture==old:first=nm.outputs['Normal']
    else:second=nm.outputs['Normal']
  mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';l.new(split.outputs['Red'],mix.inputs[0]);l.new(first,mix.inputs[1]);l.new(second,mix.inputs[2])
  output=mix.outputs[0]
  if i==1:
   s=n.new('ShaderNodeSeparateColor');l.new(output,s.inputs['Color']);output=s.outputs['Green']
  if i==2:
   norm=n.new('ShaderNodeVectorMath');norm.operation='NORMALIZE';l.new(output,norm.inputs[0]);output=norm.outputs['Vector']
  l.new(output,p.inputs[inputname])
 return m
variants=[('Swift','swift_limb',.60,.57,3.8),('Heavy','heavy_limb',1.19,1.23,-1.4),('Steady','steady_limb',1.40,.48,-2.3)]
records=[];scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
for name,part,width,depth,shift in variants:
 me=data.copy();o=bpy.data.objects.new('SM_Bow_Body_'+name,me);scene.collection.objects.link(o)
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 uv=me.uv_layers.new(name='TimberUV');color=me.color_attributes.new(name='LimbBlend',type='FLOAT_COLOR',domain='CORNER')
 parameters=[];protected=0
 for idx,(vertex,c) in enumerate(zip(me.vertices,coords)):
  cx,cy,hx,hy=section(c.z);w,shade=weights(c.z);a=abs(c.z-mid)
  nx=(c.x-cx)/max(hx,.01);ny=(c.y-cy)/max(hy,.01)
  t=smooth((a-21)/44)
  move=shift*w*(.5+.5*math.sin(t*math.pi))
  shape_x=c.x-cx
  if name=='Heavy':shape_x=hx*(math.copysign(abs(nx)**.78,nx))
  vertex.co.x=c.x+w*(shape_x*depth-(c.x-cx))+move
  vertex.co.y=c.y+(c.y-cy)*(width-1)*w
  if w==0:protected+=1
  angle=math.atan2(ny,nx)/(2*math.pi)+.5
  parameters.append((angle,(c.z-zmin)/(zmax-zmin),shade))
 for f in me.polygons:
  us=[parameters[me.loops[i].vertex_index][0] for i in f.loop_indices];seam=max(us)-min(us)>.5
  for i in f.loop_indices:
   u,v,s=parameters[me.loops[i].vertex_index];uv.data[i].uv=(u+1 if seam and u<.5 else u,v)
   color.data[i].color=(s,s,s,1)
  f.material_index=0;f.use_smooth=True
 # Source vertex positions remain untouched at mating surfaces; only regenerate shading.
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 if me.has_custom_normals:
  try:bpy.ops.mesh.customdata_custom_splitnormals_clear()
  except RuntimeError:pass
 me.materials.clear();me.materials.append(material(name))
 me.uv_layers.active_index=0
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
 records.append(dict(name=name,id=part,mesh=o.name,material='M_Bow_Body_'+name,vertices=len(me.vertices),triangles=sum(len(f.vertices)-2 for f in me.polygons),protected_source_vertices=protected,width_factor=width,depth_factor=depth,curve_shift_cm=shift))
 o.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ThreeBodies.blend'))
(P/'authoring.json').write_text(json.dumps(dict(assets=records,donor='SourceAssets/BowModular20260926/Bow_ModularParts.blend',method='continuous deformation of wood shell, original topology and UV0; no added sleeves or intersecting limb joints',protected_region='abs(Z + 0.5468216) <= 21 cm or >= 68 cm; all XYZ retained',mounts='original grip, arrow rest, sight, string notches',material_blend='vertex red; original surface at mounts, directional timber UV1 on limbs',centimetres=True,gameplay_tested=False),indent=2),encoding='utf8')
print('BOW_THREE_BODIES_AUTHORED',flush=True)
