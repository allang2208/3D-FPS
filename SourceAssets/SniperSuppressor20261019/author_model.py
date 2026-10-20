"""Cosmetic FPS attachment mesh and PBR source; no functional internals."""
import bpy,math,json
import numpy as np
from pathlib import Path
O=Path(__file__).parent;T=O/'Textures';E=O/'Exports'
T.mkdir(exist_ok=True);E.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC'
N=192;SIZE=2048;parts=[];textures={};materials={}

def image(name,pixels,color=True):
 im=bpy.data.images.new(name,width=SIZE,height=SIZE,alpha=True,float_buffer=False)
 if not color:im.colorspace_settings.name='Non-Color'
 im.pixels.foreach_set(pixels.astype(np.float32).ravel());im.filepath_raw=str(T/(name+'.png'));im.file_format='PNG';im.save();return im

rng=np.random.default_rng(191019);fine=rng.normal(0,1,(SIZE,SIZE));yy,xx=np.mgrid[:SIZE,:SIZE]
slow=np.sin(xx*.0047)*np.cos(yy*.0031)+.3*np.sin(yy*.014)
for label,base,rough in [('Shell',(.026,.029,.032),.48),('Collar',(.037,.041,.045),.39),('Cap',(.020,.022,.025),.53)]:
 color=np.ones((SIZE,SIZE,4));color[...,:3]=np.array(base)[None,None,:]*(1+fine[...,None]*.015+slow[...,None]*.018)
 orm=np.ones((SIZE,SIZE,4));orm[:,:,1]=np.clip(rough+fine*.008+slow*.012,0,1);orm[:,:,2]=1.
 normal=np.ones((SIZE,SIZE,4));normal[:,:,0]=.5+fine*.0015;normal[:,:,1]=.5+rng.normal(0,.0015,(SIZE,SIZE));normal[:,:,2]=1
 c=image('T_SniperSuppressor_'+label+'_BaseColor',color);r=image('T_SniperSuppressor_'+label+'_ORM',orm,False);n=image('T_SniperSuppressor_'+label+'_Normal',normal,False)
 roughpixels=np.ones((SIZE,SIZE,4));roughpixels[:,:,:3]=orm[:,:,1,None]
 roughtex=image('T_SniperSuppressor_'+label+'_Roughness',roughpixels,False)
 mat=bpy.data.materials.new('SniperSuppressor_'+label);mat.use_nodes=True
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=1
 ct=nodes.new('ShaderNodeTexImage');ct.image=c;links.new(ct.outputs['Color'],bs.inputs['Base Color'])
 rt=nodes.new('ShaderNodeTexImage');rt.image=r;split=nodes.new('ShaderNodeSeparateColor');links.new(rt.outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],bs.inputs['Roughness'])
 nt=nodes.new('ShaderNodeTexImage');nt.image=n;nm=nodes.new('ShaderNodeNormalMap');links.new(nt.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
 materials[label]=mat;textures[label]={'base_color':str(Path(c.filepath_raw)),'orm':str(Path(r.filepath_raw)),'normal':str(Path(n.filepath_raw)),'roughness_texture':str(Path(roughtex.filepath_raw)),'roughness':rough}
dark=bpy.data.materials.new('SniperSuppressor_Recess');dark.use_nodes=True;bs=dark.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(.003,.0035,.004,1);bs.inputs['Roughness'].default_value=.92;materials['Recess']=dark

def lathe(name,profile,material):
 verts=[];rings=[];faces=[];faceuv=[]
 for x,r in profile:
  ring=[]
  for j in range(1 if r==0 else N):
   ring.append(len(verts));verts.append((x,r*math.cos(math.tau*j/N),r*math.sin(math.tau*j/N)))
  rings.append(ring)
 lengths=[0.]
 for a,b in zip(profile,profile[1:]):lengths.append(lengths[-1]+math.dist(a,b))
 for i,(a,b) in enumerate(zip(rings,rings[1:])):
  v0=lengths[i]/lengths[-1];v1=lengths[i+1]/lengths[-1]
  for j in range(N):
   u0=j/N;u1=(j+1)/N
   if len(a)==1:faces.append((a[0],b[(j+1)%N],b[j]));faceuv.append(((u0+u1)/2,v0,u1,v1,u0,v1))
   elif len(b)==1:faces.append((a[j],a[(j+1)%N],b[0]));faceuv.append((u0,v0,u1,v0,(u0+u1)/2,v1))
   else:faces.append((a[j],a[(j+1)%N],b[(j+1)%N],b[j]));faceuv.append((u0,v0,u1,v0,u1,v1,u0,v1))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob);mesh.materials.append(materials[material])
 uv=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  poly.use_smooth=True;flat=faceuv[poly.index]
  for k,loop in enumerate(poly.loop_indices):uv.data[loop].uv=flat[2*k:2*k+2]
 parts.append(ob);return ob

# Surface-only closed forms. The dark central inset is a shallow visual recess,
# not an open internal model. Units and pivots are game-engine authoring values.
lathe('Shell',[(.018,.0248),(.0182,.0256),(.0188,.02615),(.0198,.0265),(.021,.0266),(.027,.0266),(.300,.0266),(.313,.0266),(.315,.0265),(.3162,.0261),(.3168,.0255),(.317,.0246)],'Shell')
lathe('RearCollar',[(0,.0),(0,.0148),(.0005,.0154),(.0013,.0158),(.003,.0159),(.0108,.0159),(.011,.01575),(.0112,.01575),(.0114,.0159),(.016,.0159),(.0168,.017),(.018,.0225),(.019,.0248),(.020,.0248)],'Collar')
lathe('FrontFace',[(.317,.0246),(.317,.0225),(.3168,.0205),(.3164,.012),(.3162,.0052),(.3158,.0048),(.3148,.0046)],'Cap')
lathe('ShallowVisualRecess',[(.3148,.0046),(.3145,.0042),(.3145,0)],'Recess')
lathe('RearClosure',[(.018,.0248),(.018,.017),(.018,0)],'Collar')
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_SniperHeavySuppressor'
ob['purpose']='Game cosmetic mesh; no functional internal structure';ob['axis']='Local +X is forward; origin is visual mount';ob['reference']='UserReference.png / Concept.png'
scene['runtime_tested']=False
blend=O/'SniperHeavySuppressor_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
from mathutils import Matrix
ob.data.transform(Matrix.Scale(100.,4));scene.unit_settings.scale_length=.01
fbx=E/'SM_SniperHeavySuppressor.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
(O/'authoring.json').write_text(json.dumps({'model':ob.name,'blend':str(blend),'fbx':str(fbx),'tip_cm':31.7,'axis':'+X','vertices':len(ob.data.vertices),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'textures':textures,'materials':[m.name for m in ob.data.materials],'runtime_tested':False},indent=2))
print('SNIPER_SUPPRESSOR_MODEL_AUTHORED',str(blend),flush=True)
