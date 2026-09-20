"""Produce per-rifle finish, rail saddle and the AKM's existing receiver adapter."""
import bpy, json, os, math, runpy, shutil, sys
import numpy as np
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'Integration';S=ROOT.parent
profiles={
 'M4':{'color':(.07,.075,.08),'rough':.44,'metal':.85,'source':'M4InfimaV3/Body_001; isolated receiver color crop, steel fastener response'},
 'AKM':{'color':(.035,.043,.048),'rough':.48,'metal':.85,'source':'AKMIntegration/SovietFab/M_AKM_Soviet_PBR; receiver metal crop'},
 'QBZ191':{'color':(.025,.029,.032),'rough':.35645,'metal':.72,'source':'QBZ191MetalCoat20260913/bake_coating.py receiver coating'},
 'ASH12':{'color':(.09,.095,.103),'rough':.45,'metal':.70,'source':'ASH12/Surface20260919 Front; UniversalAttachments GripMetal coating'}}
def sample(path,color=False):
 im=bpy.data.images.load(str(path),check_existing=True);a=np.array(im.pixels[:],dtype=np.float32).reshape(-1,4);rgb=np.median(a[:,:3],axis=0)
 # Image.pixels for loaded byte textures exposes encoded RGB. Principled
 # constants are scene-linear; roughness/metallic remain raw data values.
 if color:rgb=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 return rgb.tolist()
def finish(ob,mat):
 bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 ob.data.materials.clear();ob.data.materials.append(mat)
 mod=ob.modifiers.new('Rail contact chamfer','BEVEL');mod.width=.00025;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in ob.data.polygons:p.use_smooth=True
 mod=ob.modifiers.new('Rail weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
def box(name,loc,size,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.scale=size;finish(ob,mat)
def jaw(sign,mat):
 sec=[(sign*y,z) for y,z in [( .0106,-.004),(.0153,-.004),(.0153,.0015),(.0129,.0045),(.0106,.0015)]]
 if sign<0:sec.reverse()
 v=[(x,y,z) for x in (-.025,.025) for y,z in sec];n=len(sec)
 f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new('RailJaw');me.from_pydata(v,[],f);ob=bpy.data.objects.new('SaddleJaw_'+str(sign),me);bpy.context.collection.objects.link(ob)
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);finish(ob,mat)
guns=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(profiles)
for gun in guns:
 profile=profiles[gun]
 folder=D/gun;(folder/'Source').mkdir(parents=True,exist_ok=True);(folder/'Reference').mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Source/TacticalVerticalForegrip_Construction.blend'))
 bpy.context.preferences.filepaths.save_version=0
 if gun=='M4':profile['color']=sample(S/'WeaponAttachmentFinish20260913/Textures/T_M4_Receiver_BaseColor.png',True)
 if gun=='AKM':
  base=S/'AKMArmSupport20260911/Metal'
  for key,file in [('color','T_AKM_Mount_Base_color.png'),('rough','T_AKM_Mount_Roughness.png'),('metal','T_AKM_Mount_Metallic.png')]:
   value=sample(base/file,key=='color');profile[key]=value if key=='color' else float(value[0])
 # Preserve the physical polymer body and its fine roughness/normal pattern.
 metal=bpy.data.materials['Fastener_DarkMetal'];metal.name='Coating_'+gun
 for mat in [metal,bpy.data.materials['Fastener_Inset']]:
  bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  bs.inputs['Metallic'].default_value=profile['metal']
  ramp=next(n for n in mat.node_tree.nodes if n.type=='VALTORGB')
  dark=.40 if 'Inset' in mat.name else .90;light=.65 if 'Inset' in mat.name else 1.08
  ramp.color_ramp.elements[0].color=tuple(x*dark for x in profile['color'])+(1,)
  ramp.color_ramp.elements[1].color=tuple(x*light for x in profile['color'])+(1,)
  rough=next(n for n in mat.node_tree.nodes if n.type=='MAP_RANGE');rough.inputs['To Min'].default_value=max(.1,profile['rough']-.025);rough.inputs['To Max'].default_value=min(.95,profile['rough']+.025)
 for ob in list(bpy.context.scene.objects):
  if ob.name.startswith('Saddle'):bpy.data.objects.remove(ob,do_unlink=True)
 box('SaddleContactFloor',(0,0,-.003),(.050,.0212,.006),metal)
 jaw(-1,metal);jaw(1,metal)
 # Z=0 is the rail underside; side jaws rise around its shoulders.
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Source/TacticalVerticalForegrip_Construction.blend'))
 for f in ['user_reference.png','three_views.png']:shutil.copy2(ROOT/'Reference'/f,folder/'Reference'/f)
 os.environ['TACTICAL_GRIP_AUTHOR_ROOT']=str(folder)
 runpy.run_path(str(ROOT/'Scripts/bake_local.py'),run_name='__main__')
 low=bpy.data.objects['SM_TacticalVerticalForegrip_Candidate'];low.name='SM_TacticalVerticalForegrip'
 if gun=='AKM':
  mount=Matrix(json.loads((S/'VerticalGripFront20260911/akm/fits.json').read_text())['vertical']['grip_in_root'])
  low.data.transform(mount)
  # The accepted AKM mount includes a separate receiver adapter. Keep its
  # mesh, UV, material identity and root-space placement intact.
  previous=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=str(D/'References/AKM_vertical.fbx'),use_custom_normals=True)
  old=[o for o in bpy.context.scene.objects if o not in previous and o.type=='MESH']
  import bmesh
  adapters=[]
  for ob in old:
   indices={i for i,m in enumerate(ob.data.materials) if m and ('Adapter' in m.name or 'MountSteel' in m.name)}
   if not indices:bpy.data.objects.remove(ob,do_unlink=True);continue
   bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in indices],context='FACES');bm.to_mesh(ob.data);bm.free()
   ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);adapters.append(ob)
  if not adapters:raise RuntimeError('Accepted AKM adapter not found in exported source')
  bpy.ops.object.select_all(action='DESELECT');low.select_set(True)
  for ob in adapters:ob.select_set(True)
  bpy.context.view_layer.objects.active=low;bpy.ops.object.join()
 bpy.ops.object.select_all(action='DESELECT');low.hide_set(False);low.select_set(True);bpy.context.view_layer.objects.active=low
 bpy.ops.export_scene.fbx(filepath=str(folder/'Export/SM_TacticalVerticalForegrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Source/TacticalVerticalForegrip_Integrated.blend'))
 profile['attachment_frame']='AKM existing grip_in_root baked into vertices' if gun=='AKM' else 'top saddle frame; X forward, Z up; centimeters after FBX'
 accumulated=json.loads((D/'finish_profiles.json').read_text()) if (D/'finish_profiles.json').exists() else {}
 accumulated[gun]=profile
 (D/'finish_profiles.json').write_text(json.dumps(accumulated,indent=2),encoding='utf-8')
 print('INTEGRATION_AUTHORED '+gun,flush=True)
