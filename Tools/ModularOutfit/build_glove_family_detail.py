"""Background high-poly sculpt, registered bake and equipment-icon production."""
import sys, math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import glove_family_detail as lib
import build_tailored_fingerless_candidate as leather

R=lib.R
CURRENT='Fingerless'

def active(obj):
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj

class Nodes:
 def __init__(self,mat):self.n=mat.node_tree.nodes;self.l=mat.node_tree.links
 def node(self,kind,**kw):
  n=self.n.new(kind)
  for k,v in kw.items():setattr(n,k,v)
  return n
 def put(self,n,key,v):
  if isinstance(v,(float,int,list,tuple)):n.inputs[key].default_value=v
  else:self.l.new(v,n.inputs[key])
 def op(self,op,a,b=None):
  n=self.node('ShaderNodeMath',operation=op);self.put(n,0,a)
  if b is not None:self.put(n,1,b)
  return n.outputs[0]
 def mix(self,a,b,f):
  n=self.node('ShaderNodeMixRGB');self.put(n,0,f);self.put(n,1,a);self.put(n,2,b);return n.outputs[0]
 def mul(self,a,b):
  n=self.node('ShaderNodeMixRGB',blend_type='MULTIPLY');self.put(n,0,1.);self.put(n,1,a);self.put(n,2,b);return n.outputs[0]
 def sep(self,value):
  n=self.node('ShaderNodeSeparateXYZ');self.put(n,0,value);return n.outputs
 def combine(self,r,g,b):
  n=self.node('ShaderNodeCombineXYZ');self.put(n,0,r);self.put(n,1,g);self.put(n,2,b);return n.outputs[0]
 def gaussian(self,x,w):
  q=self.op('DIVIDE',x,w);return self.op('EXPONENT',self.op('MULTIPLY',self.op('MULTIPLY',q,q),-1.))
 def noise(self,uv,scale,detail=2.):
  n=self.node('ShaderNodeTexNoise');self.put(n,'Vector',uv);self.put(n,'Scale',scale);self.put(n,'Detail',detail);return n.outputs['Fac']

def design_image(palm):
 size=2048;x,y=np.meshgrid((np.arange(size)+.5)/size*16-8,(np.arange(size)+.5)/size*18-5)
 d=lib.pattern(x,y,palm,CURRENT=='Tactical')
 im=bpy.data.images.new('TailoringPalm' if palm else 'TailoringBack',width=size,height=size,alpha=True,float_buffer=True)
 im.colorspace_settings.name='Non-Color'
 im.pixels.foreach_set(np.stack((d['fine']*.01,d['thread'],d['panel'],d['polish']),axis=-1).astype(np.float32).ravel())
 im.pack();return im

def leather_material(folder):
 leather.T=folder;leather.design_image=design_image
 mat,color,rough,bs,out=leather.authored_material();mat.name=CURRENT+'_HighAuthor';mat.use_fake_user=True
 ns=Nodes(mat);op=ns.op
 for n in ns.n:
  if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('Tailoring'):n.extension='EXTEND'
 uv=ns.node('ShaderNodeUVMap',uv_map='TailoringCoordinates').outputs[0]
 metric=ns.node('ShaderNodeUVMap',uv_map='LeatherMetric25cm').outputs[0]
 ef=ns.sep(ns.node('ShaderNodeUVMap',uv_map='PalmAndEdgeDistance').outputs[0]);sf=ns.sep(ns.node('ShaderNodeUVMap',uv_map='StitchArcAndLining').outputs[0])
 # Needle dimples, seam wear and short nap share the sculpt's physical fields.
 size=2048;x,y=np.meshgrid((np.arange(size)+.5)/size*16-8,(np.arange(size)+.5)/size*18-5)
 results=[]
 for palm in (0.,1.):
  d=lib.pattern(x,y,palm,CURRENT=='Tactical')
  im=bpy.data.images.new('Finish_'+str(palm),width=size,height=size,alpha=True,float_buffer=True);im.colorspace_settings.name='Non-Color'
  im.pixels.foreach_set(np.stack((d['holes'],d['wear'],d['thread'],d['fine']),axis=-1).astype(np.float32).ravel());im.pack()
  tex=ns.node('ShaderNodeTexImage',extension='EXTEND');tex.image=im;ns.put(tex,'Vector',uv);results.append(tex)
 fields=ns.sep(ns.mix(results[0].outputs[0],results[1].outputs[0],ef[0]))
 interior=op('SUBTRACT',1.,sf[1])
 seam=ns.gaussian(op('SUBTRACT',ef[1],.28),.023)
 dash=op('LESS_THAN',op('ABSOLUTE',op('SUBTRACT',op('FRACT',op('DIVIDE',sf[0],.27)),.5)),.30)
 thread=op('MULTIPLY',op('MINIMUM',1.,op('ADD',fields[2],op('MULTIPLY',seam,dash))),interior)
 holes=op('MULTIPLY',fields[0],interior)
 wear=op('MULTIPLY',fields[1],interior)
 nap=op('MULTIPLY',op('ADD',op('MULTIPLY',thread,.6),op('MULTIPLY',ns.gaussian(op('SUBTRACT',ef[1],.06),.065),.5)),interior)
 color=ns.mul(color,op('SUBTRACT',1.,op('MULTIPLY',holes,.38)))
 color=ns.mix(color,ns.mul(color,(1.15,1.10,1.04,1)),op('MULTIPLY',wear,.45))
 color=ns.mix(color,(.20,.118,.058,1) if CURRENT=='Fingerless' else (.145,.112,.07,1),op('MULTIPLY',thread,.48))
 rough=op('MINIMUM',.91,op('MAXIMUM',.34,op('ADD',rough,op('SUBTRACT',op('MULTIPLY',nap,.1),op('MULTIPLY',wear,.06)))))
 grain=next(n for n in ns.n if n.type=='NORMAL_MAP')
 # Fine pores and broken short fibres remain normal detail on the high sculpt.
 micro=ns.noise(metric,1750.,2.);fibers=ns.noise(metric,3300.,2.)
 bh=op('ADD',op('MULTIPLY',op('SUBTRACT',micro,.5),.000012),op('MULTIPLY',op('MULTIPLY',op('SUBTRACT',fibers,.5),nap),.000023))
 bump=ns.node('ShaderNodeBump');ns.put(bump,'Height',bh);ns.put(bump,'Distance',1.);ns.put(bump,'Strength',1.);ns.put(bump,'Normal',grain.outputs[0])
 ns.put(bs,'Normal',bump.outputs[0]);ns.put(bs,'Base Color',color);ns.put(bs,'Roughness',rough);ns.put(bs,'Sheen Weight',op('MULTIPLY',nap,.22));ns.put(bs,'Sheen Roughness',.78)
 orm=ns.combine(op('SUBTRACT',1.,op('MULTIPLY',holes,.22)),rough,0.)
 # Encode the very same point-interpolated fine relief used by the high mesh.
 height=ns.node('ShaderNodeAttribute',attribute_name='DetailFineCm').outputs['Fac']
 relief=ns.combine(op('MINIMUM',1.,op('MAXIMUM',0.,op('ADD',.5,op('DIVIDE',height,.06)))),nap,1.)
 return mat,color,orm,bs,out,relief

def uv_layer(obj,name,coords,flip=True):
 layer=obj.data.uv_layers.get(name) or obj.data.uv_layers.new(name=name)
 for face,uvs in zip(obj.data.polygons,coords):
  for li,(u,v) in zip(face.loop_indices,uvs):layer.data[li].uv=(u,1-v if flip else v)
 obj.data.uv_layers.active=layer;layer.active_render=True
 return layer

def point_uv(mesh,name):
 values=np.empty(len(mesh.loops)*2,dtype=np.float32);mesh.uv_layers[name].data.foreach_get('uv',values);values=values.reshape(-1,2)
 ids=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',ids)
 sums=np.zeros((len(mesh.vertices),2));counts=np.bincount(ids,minlength=len(mesh.vertices))
 np.add.at(sums,ids,values);return sums/np.maximum(counts[:,None],1)

def sculpt_values(obj):
 uv=point_uv(obj.data,'TailoringCoordinates');ef=point_uv(obj.data,'PalmAndEdgeDistance');sf=point_uv(obj.data,'StitchArcAndLining')
 return lib.surface_fields(uv[:,0]*16-8,uv[:,1]*18-5,ef[:,0],ef[:,1],sf[:,0],sf[:,1],CURRENT=='Tactical')['fine']

def attribute(mesh,name,data):
 a=mesh.attributes.get(name) or mesh.attributes.new(name,'FLOAT','POINT');a.data.foreach_set('value',np.asarray(data,dtype=np.float32))

def high_copy(low,levels,sculpt):
 high=low.copy();high.data=low.data.copy();high.name=low.name+'_HIGH';bpy.context.collection.objects.link(high)
 for m in list(high.modifiers):high.modifiers.remove(m)
 active(high)
 if levels:
  mod=high.modifiers.new('SculptSubdivision','SUBSURF');mod.subdivision_type='SIMPLE';mod.levels=levels;mod.render_levels=levels
  bpy.ops.object.modifier_apply(modifier=mod.name)
 p=np.empty(len(high.data.vertices)*3,dtype=np.float32);n=p.copy();high.data.vertices.foreach_get('co',p);high.data.vertices.foreach_get('normal',n)
 p=p.reshape(-1,3);n=n.reshape(-1,3);offset=sculpt(high)
 p+=n*offset[:,None];high.data.vertices.foreach_set('co',p.ravel());high.data.update()
 high.data.normals_split_custom_set_from_vertices([tuple(v.normal) for v in high.data.vertices])
 high['BakeOnly']=True;high['SculptDisplacementRangeMeters']=[float(offset.min()),float(offset.max())]
 print('COMPANION_HIGH_SCULPT',high.name,len(high.data.vertices),len(high.data.polygons),flush=True)
 return high

def bake(folder,group,low,high,material,color,orm,bs,out,relief=None,size=4096,atlas='DetailAtlas',cage=.00055):
 folder=folder/'Textures'/group;folder.mkdir(parents=True,exist_ok=True)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=False
 scene.render.bake.margin=12;scene.render.bake.use_clear=True
 nodes=material.node_tree.nodes;links=material.node_tree.links;maps={}
 for label in ['BaseColor','ORM','Normal']+(['Relief'] if relief is not None else []):
  im=bpy.data.images.new('T_'+CURRENT+'_'+group+'_'+label,width=size,height=size,alpha=True)
  im.colorspace_settings.name='sRGB' if label=='BaseColor' else 'Non-Color'
  target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
  active(low)
  if label in ('Normal','Relief'):
   high.hide_set(False);high.hide_render=False;high.select_set(True)
   if label=='Normal':links.new(bs.outputs[0],out.inputs['Surface']);kind='NORMAL'
   else:
    emit=nodes.new('ShaderNodeEmission');links.new(relief,emit.inputs['Color']);links.new(emit.outputs[0],out.inputs['Surface']);kind='EMIT'
   scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=cage;scene.render.bake.max_ray_distance=cage*1.8
  else:
   high.hide_render=True;scene.render.bake.use_selected_to_active=False
   emit=nodes.new('ShaderNodeEmission');links.new(color if label=='BaseColor' else orm if label=='ORM' else relief,emit.inputs['Color']);links.new(emit.outputs[0],out.inputs['Surface']);kind='EMIT'
  print('COMPANION_BAKE',CURRENT,group,label,size,flush=True)
  bpy.ops.object.bake(type=kind,uv_layer=atlas,normal_space='TANGENT')
  im.filepath_raw=str(folder/(im.name+'.png'));im.file_format='PNG';im.save();maps[label]=im
 links.new(bs.outputs[0],out.inputs['Surface']);high.select_set(False);high.hide_render=True;high.hide_set(True)
 return maps

def baked_material(family,group,maps=None,uv_name='',repeat=None):
 folder=R/family/'Textures'/group
 if maps is None:
  maps={ch:leather.image(folder/('T_'+family+'_'+group+'_'+ch+'.png'),'sRGB' if ch=='BaseColor' else 'Non-Color') for ch in ('BaseColor','ORM','Normal')}
  path=folder/('T_'+family+'_'+group+'_Relief.png')
  if path.exists():maps['Relief']=leather.image(path)
 mat=bpy.data.materials.new('Detail_'+family+'_'+group);mat.use_nodes=True;ns=Nodes(mat);bs=next(n for n in ns.n if n.type=='BSDF_PRINCIPLED');bs.inputs['Specular IOR Level'].default_value=.42
 uv=ns.node('ShaderNodeUVMap',uv_map=uv_name).outputs[0] if uv_name else ns.node('ShaderNodeTexCoord').outputs['UV']
 if repeat:
  m=ns.node('ShaderNodeVectorMath',operation='MULTIPLY');ns.put(m,0,uv);ns.put(m,1,(*repeat,1.));uv=m.outputs[0]
 for ch,im in maps.items():
  tex=ns.node('ShaderNodeTexImage');tex.image=im;ns.put(tex,'Vector',uv)
  if ch=='BaseColor':ns.put(bs,'Base Color',tex.outputs[0])
  elif ch=='ORM':
   sep=ns.sep(tex.outputs[0]);ns.put(bs,'Roughness',sep[1]);ns.put(bs,'Metallic',sep[2])
  elif ch=='Normal':
   nm=ns.node('ShaderNodeNormalMap',uv_map=uv_name);ns.put(nm,'Color',tex.outputs[0]);ns.put(bs,'Normal',nm.outputs[0])
  else:ns.put(bs,'Sheen Weight',ns.op('MULTIPLY',ns.sep(tex.outputs[0])[1],.22));ns.put(bs,'Sheen Roughness',.78)
 return mat

def author_leather(family,group):
 global CURRENT
 CURRENT=family;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 source=lib.FAMILIES[family]['source'];folder=R/family;name='M4' if group=='Shared' else group
 if family=='Fingerless':
  data=lib.read(source/'Authored'/(name+'_fullshell.json'));baked=lib.read(source/'Authored'/(name+'_baked_fullshell.json'))
  if group=='Shared':
   # The family's M4 copy already stores the runtime atlas in UV0. Restore
   # the original scan projection from the unbaked selected author instead.
   candidate=lib.read(lib.P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessCandidate/M4_fullshell.json')
   data['uv']=candidate['uv']
  if group=='Body':
   # Body uses unit bone axes; normalize both reference bases before moving
   # the tailoring coordinates, avoiding the legacy 100x author-field scale.
   canon=lib.read(source/'Authored/M4_fullshell.json');anatomy=lib.read(lib.P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
   from tailored_fingerless_candidate import frame,unit
   positions=np.asarray(data['positions']);local=np.zeros_like(positions)
   for side in ('l','r'):
    own=np.asarray([sum(v for n,v in w.items() if n.endswith('_'+side))>.5 for w in data['weights']]);bn='hand_'+side
    src=unit(np.asarray(canon['bones'][bn]['axes'])).T;dst=unit(np.asarray(data['bones'][bn]['axes'])).T
    back=(positions[own]-data['bones'][bn]['position'])@(dst@src.T)+canon['bones'][bn]['position']
    basis,wrist=frame(canon['bones'],anatomy,side);local[own]=(back-wrist)@basis.T
   faces=np.asarray(data['triangles']);data['uv3']=np.stack(((local[faces,0]+8)/16,(local[faces,1]+5)/18),axis=-1).tolist()
 else:
  data=lib.read(source/'Authoring'/(name+'.json'));baked=lib.read(source/'Baked'/(name+'.json'))
 mat,color,orm,bs,out,relief=leather_material(folder)
 low=leather.make_mesh(data,mat);low.name=family+'_'+group+'_LOW';uv_layer(low,'DetailAtlas',baked['uv'])
 attribute(low.data,'DetailFineCm',sculpt_values(low))
 high=high_copy(low,3,lambda o:sculpt_values(o)*.01)
 # Preserve the evaluated fine field for height rebakes and editable sources.
 attribute(high.data,'DetailFineCm',sculpt_values(high))
 size=2048 if group=='Body' else 4096
 maps=bake(folder,group,low,high,mat,color,orm,bs,out,relief,size)
 low.data.materials.clear();low.data.materials.append(baked_material(family,group,maps,'DetailAtlas'))
 leather.rig(low,data);active(low)
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Editable'/(group+'_HighPoly.blend')))
 lib.write(folder/'Baked'/(group+'.json'),dict(uv=baked['uv']))
 lib.write(folder/(group+'-production.json'),dict(group=group,game_vertices=len(low.data.vertices),game_faces=len(low.data.polygons),high_vertices=len(high.data.vertices),high_polygons=len(high.data.polygons),texture_size=size,geometry_changed=False,native_weights_changed=False,runtime_tested=False))
 print('COMPANION_LEATHER_SAVED',family,group,flush=True)

def steel_displacement(obj):
 mesh=obj.data;uv=point_uv(mesh,'SteelPanelUV');a=mesh.attributes['PanelDimensions']
 arr=np.empty(len(mesh.vertices)*4,dtype=np.float32);a.data.foreach_get('color',arr);dim=arr.reshape(-1,4)
 width,height,style=dim[:,0],dim[:,1],dim[:,2]
 mx=np.minimum(uv[:,0],1-uv[:,0])*width;my=np.minimum(uv[:,1],1-uv[:,1])*height;edge=np.minimum(mx,my)
 hardware=(style>.2)&(style<.4);mail=(style>.65)&(style<.75)
 groove=np.maximum(lib.gauss(edge-.00155,.00018)*(~hardware),lib.gauss(edge-.00225,.00010)*(style>.8))
 x=uv[:,0]*width;y=uv[:,1]*height
 h=-.000038*groove+.000006*np.sin(x*37000+np.sin(y*2100))*np.sin(y*5000)
 row=y/.0006;col=x/.0007;rx=(np.mod(col+np.mod(np.floor(row),2)*.5,1)-.5)/.43;ry=(np.mod(row,1)-.5)/.39
 wire=lib.gauss(np.sqrt(rx*rx+ry*ry)-.84,.19)
 h=np.where(mail,.000105*wire,h)
 return h

def steel_author_material():
 import steel_gauntlet_finish as finish
 bpy.context.preferences.view.use_translate_new_dataname=False
 mat,color,orm,bs,out=finish.material();mat.name='CompanionSteel_HighAuthor';mat.use_fake_user=True;ns=Nodes(mat)
 for n in list(ns.n):
  if n.type=='OBJECT_INFO':
   attr=ns.node('ShaderNodeAttribute',attribute_name='PanelDimensions')
   for link in list(n.outputs['Color'].links):ns.l.new(attr.outputs['Color'],link.to_socket)
 # Engravings are real high-poly displacement. The micro normal contributes
 # only satin brush grain, avoiding a second copy of the carved groove.
 uv=ns.node('ShaderNodeUVMap',uv_map='SteelPanelUV').outputs[0]
 mapping=ns.node('ShaderNodeVectorMath',operation='MULTIPLY');ns.put(mapping,0,uv);ns.put(mapping,1,(1500.,40.,1.))
 noise=ns.noise(mapping.outputs[0],1.,2.)
 bump=ns.node('ShaderNodeBump');ns.put(bump,'Height',noise);ns.put(bump,'Distance',.000018);ns.put(bump,'Strength',.45)
 ns.put(bs,'Normal',bump.outputs[0])
 # Slight fine abrasion remains restrained and directional on the steel.
 color=ns.mul(color,ns.op('ADD',.975,ns.op('MULTIPLY',noise,.05)));ns.put(bs,'Base Color',color)
 return mat,color,orm,bs,out

def panel_attribute(obj):
 a=obj.data.attributes.get('PanelDimensions') or obj.data.attributes.new('PanelDimensions','FLOAT_COLOR','POINT')
 a.data.foreach_set('color',np.tile(np.asarray(obj.color,dtype=np.float32),(len(obj.data.vertices),1)).ravel())

def author_steel(group):
 global CURRENT
 CURRENT='Steel';folder=R/'Steel';source=lib.FAMILIES['Steel']['source'];bpy.context.preferences.filepaths.save_version=0
 if group=='Plates':
  bpy.ops.wm.open_mainfile(filepath=str(source/'SteelGauntlet_M4.blend'))
  pieces=[o for o in bpy.data.objects if o.type=='MESH' and any(m and m.name.startswith('SteelGauntlet_Baked') for m in o.data.materials)]
  if not pieces:raise RuntimeError('Current plate authoring source is missing')
  for o in list(bpy.data.objects):
   if o not in pieces:bpy.data.objects.remove(o,do_unlink=True)
  for o in pieces:
   for m in list(o.modifiers):o.modifiers.remove(m)
   panel_attribute(o)
  active(pieces[0])
  for o in pieces:o.select_set(True)
  bpy.ops.object.join();low=bpy.context.object;low.name='Steel_Plates_LOW';atlas='SteelSampleUV';size=4096
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.mesh.primitive_grid_add(x_subdivisions=256,y_subdivisions=256,size=1)
  highbase=bpy.context.object;highbase.scale=(.0056,.0048,1.);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  highbase.data.uv_layers[0].name='SteelPanelUV';highbase.color=(.0056,.0048,.70,1.);panel_attribute(highbase)
  # A dense authored height surface forms real interwoven ring relief.
  low=highbase;low.name='Steel_MailTile_LOW';atlas='SteelPanelUV';size=1024
 mat,color,orm,bs,out=steel_author_material();low.data.materials.clear();low.data.materials.append(mat)
 for f in low.data.polygons:f.material_index=0
 high=high_copy(low,2 if group=='Plates' else 0,steel_displacement)
 if group=='Mail':
  # AO belongs to the small recesses, not an infinitely dark tiled horizon.
  pack=next(n for n in mat.node_tree.nodes if n.type=='COMBINE_COLOR');ns=Nodes(mat)
  for link in list(pack.inputs['Red'].links):ns.l.remove(link)
  pack.inputs['Red'].default_value=1.
 maps=bake(folder,group,low,high,mat,color,orm,bs,out,size=size,atlas=atlas,cage=.00018)
 low.data.materials.clear();low.data.materials.append(baked_material('Steel',group,maps,atlas))
 active(low);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Editable'/(group+'_HighPoly.blend')))
 lib.write(folder/(group+'-production.json'),dict(group=group,high_vertices=len(high.data.vertices),high_polygons=len(high.data.polygons),texture_size=size,geometry_changed=False,native_weights_changed=False,runtime_tested=False))
 print('COMPANION_STEEL_SAVED',group,flush=True)

def icon(family,export_pickup=True):
 """Production deliverable only: the existing single empty display shape."""
 global CURRENT
 CURRENT=family;spec=lib.FAMILIES[family];folder=R/family
 bpy.ops.wm.open_mainfile(filepath=str(spec['icon_source']));bpy.context.preferences.filepaths.save_version=0
 objs=[o for o in bpy.data.objects if o.type=='MESH'];obj=next(o for o in objs if 'Pickup' in o.name) if any('Pickup' in o.name for o in objs) else objs[0]
 for other in list(bpy.data.objects):
  if other is not obj:bpy.data.objects.remove(other,do_unlink=True)
 if family=='Steel':
  obj.data.materials[0]=baked_material(family,'Mail',repeat=(.25/.0056,.25/.0048));obj.data.materials[1]=baked_material(family,'Plates')
 else:
  group='Shared' if family=='Fingerless' else 'M4';mat=baked_material(family,group)
  for i in range(len(obj.data.materials)):
   if i==0:obj.data.materials[i]=mat
   else:
    lining=mat.copy();lining.name='Detail_Tactical_Interior';ns=Nodes(lining);bs=next(n for n in ns.n if n.type=='BSDF_PRINCIPLED');old=bs.inputs['Base Color'].links[0].from_socket;ns.put(bs,'Base Color',ns.mul(old,(.55,.55,.55,1)));obj.data.materials[i]=lining
 # Keep the matching pickup source export separate from icon framing.
 active(obj)
 if export_pickup:bpy.ops.export_scene.fbx(filepath=str(folder/('SM_'+family+'_Detail_Pickup.fbx')),use_selection=True,object_types={'MESH'},bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
 import render_steel_gauntlet_icon as studio
 # Reuse framing/light setup; publication belongs to the UE import step.
 coords=np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices]);lo,hi=coords.min(0),coords.max(0);center=(lo+hi)*.5
 scene=bpy.context.scene;camdata=bpy.data.cameras.new('IconCamera');camdata.type='ORTHO';camdata.ortho_scale=float(max((hi-lo)[:2])/.91);camdata.clip_start=.01
 cam=bpy.data.objects.new('IconCamera',camdata);scene.collection.objects.link(cam);cam.location=Vector((center[0],center[1],hi[2]+1.5));scene.camera=cam
 for name,offset,power,size in [('Key',(-.4,-.12,.7),15.,.55),('Fill',(.4,.15,.6),7.,.65),('Rim',(.08,.48,.45),12.,.45)]:
  light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size;o=bpy.data.objects.new(name,light);scene.collection.objects.link(o);o.location=Vector(center)+Vector(offset);o.rotation_euler=(Vector(center)-o.location).to_track_quat('-Z','Y').to_euler()
 world=bpy.data.worlds.new('NeutralIconStudio');world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.35,.35,.35,1);bg.inputs[1].default_value=.12;scene.world=world
 scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.render.film_transparent=True
 scene.render.resolution_x=scene.render.resolution_y=320;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
 scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0.;scene.view_settings.gamma=1.
 output=folder/(spec['item']+'.png');scene.render.filepath=str(output)
 # The same area-weighted production colour correction used by black V4.
 # Mail's repeat is read from the node mapping by that helper.
 if family=='Steel':obj.data.materials[0].name='GreyMetalLiner_Baked_Detail'
 target=float(studio.production_color(obj)@np.asarray([.2126,.7152,.0722]))
 for attempt in range(3):
  bpy.ops.render.render(write_still=True);pixels=studio.measure(output);actual=float(np.asarray(pixels['mean_linear'])@np.asarray([.2126,.7152,.0722]));adjust=math.log2(target/max(actual,1.e-6))
  if abs(adjust)<.08 or attempt==2:break
  scene.view_settings.exposure+=float(np.clip(adjust,-1,1))
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Editable'/(family+'_EquipmentIcon.blend')))
 lib.write(folder/'artwork.json',dict(item=spec['item'],icon=str(output),pickup_source=str(spec['icon_source']),source_materials='same baked maps as worn equipment',**pixels,runtime_tested=False))
 print('COMPANION_ICON_SAVED',family,flush=True)

if __name__=='__main__':
 args=sys.argv[sys.argv.index('--')+1:];family=args[0];group=args[1]
 if group=='icon':icon(family)
 elif family=='Steel':author_steel(group)
 else:author_leather(family,group)
