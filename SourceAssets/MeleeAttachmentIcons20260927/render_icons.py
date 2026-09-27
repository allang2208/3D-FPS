"""Render current authored parts, preserving their geometry, UVs and material partitions.

Blender --background --python render_icons.py -- <weapon> [option-key-substring]
No changes to UE models, catalog stats or saves. Only the icon staging directory is written.
"""
import bpy,bmesh,json,math,sys,shutil
from pathlib import Path
from mathutils import Vector,Matrix

P=Path(__file__).resolve().parent;SRC=P.parent;ROOT=SRC.parent
sys.path.insert(0,str(P))
import rune_surface
OUT=P/'Icons';OUT.mkdir(exist_ok=True)
SCENES=P/'Scenes';SCENES.mkdir(exist_ok=True)
baseline=json.loads((P/'baseline.json').read_text(encoding='utf-8'))
runtime=json.loads((P/'runtime_sources.json').read_text(encoding='utf-8'))
args=sys.argv[sys.argv.index('--')+1:];weapon=args[0];only=args[1] if len(args)>1 else ''
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 devices=[d for d in prefs.devices if d.type=='OPTIX']
 for d in prefs.devices:d.use=d in devices
 if devices:scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
world=bpy.data.worlds.new('Neutral icon studio');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.22,.22,.22,1);bg.inputs['Strength'].default_value=.65
camera=bpy.data.objects.new('Level side camera - blade axis to left',bpy.data.cameras.new('Orthographic'))
scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_start=.0001
camera.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler()
lights=[]
for name,offset,power,size in [('Key',(1.8,-3,1.4),420,2.2),('Fill',(-1.8,-2.4,-1.8),150,2.8),('Rim',(.7,1.8,.5),320,1.6)]:
 lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
 lights.append((lamp,Vector(offset),power,size))

def append(file,name):
 path=SRC/file
 with bpy.data.libraries.load(str(path),link=False) as (a,b):
  if name not in a.objects:raise RuntimeError('Missing '+name+' in '+str(path))
  b.objects=[name]
 obj=b.objects[0];scene.collection.objects.link(obj);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
 obj.hide_set(False);obj.hide_render=False
 return obj

def material(file,name):
 with bpy.data.libraries.load(str(SRC/file),link=False) as (a,b):b.materials=[name]
 if b.materials[0] is None:raise RuntimeError('Missing authored material '+name)
 return b.materials[0]

def blade_material(obj):
 # Restore the shipped leather textures; older authoring scenes may retain an unbaked placeholder.
 for slot in obj.material_slots:
  if slot.material and slot.material.name.startswith('M_Grip_Leather'):
   m=bpy.data.materials.new('Icon_Current_FrostGrip_Leather');m.use_nodes=True
   bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Metallic'].default_value=0
   for key,target in [('base_color','Base Color'),('roughness','Roughness'),('normal','Normal')]:
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SRC/'FrostSwordGrips20260919/Textures'/(key+'.png')),check_existing=True)
    tex.image.colorspace_settings.name='sRGB' if key=='base_color' else 'Non-Color'
    output=tex.outputs['Color']
    if key=='normal':
     normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(output,normal.inputs['Color']);output=normal.outputs['Normal']
    m.node_tree.links.new(output,bs.inputs[target])
   slot.material=m

def load_part(spec):
 mesh=spec['mesh'];name=mesh.split('.')[-1]
 sources=runtime['meshes'][mesh]['sources']
 stem=Path(sources[0]).stem if sources else name
 if '/BladeVariants20260922/' in mesh:
  file='SwordBladeVariants20260922/'+('RuneSword' if weapon=='ue_rune_sword' else 'FrostSword')+'_Blades_V1_Editable.blend';objname=stem
 elif '/AzureRunesword20260913/Modules' in mesh:file='RuneSwordModules20260919/RuneSword_Modular_Editable.blend';objname=name
 elif '/FrostCrystalSword20260915/Modules' in mesh:file='FrostSwordModules20260915/FrostSword_Modular_Editable.blend';objname=name
 elif '/Grips20260919/' in mesh:
  oid=name.replace('SM_FrostGrip_','');file=f'FrostSwordGrips20260919/{oid}/{name}_Editable.blend';objname=name
 elif '/PommelsRepair20260915/' in mesh:
  oid=name.replace('SM_FrostPommel_','')
  file='SixSharedSwordPommels20260920/SixSharedPommels_RuneFit.blend' if weapon=='ue_rune_sword' else f'FrostSwordPommelsRepair20260915/{oid}/FrostPommel_Editable.blend';objname=name
 elif '/Pommels20260920/' in mesh:
  file='RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend';objname=name
 elif '/SixSharedSwordPommels20260920/' in mesh:file='SixSharedSwordPommels20260920/SixSharedPommels_RuneFit.blend';objname=name
 elif '/SharedSwordPommels20260920/' in mesh:file='SharedSwordPommels20260920/SharedPommels_FrostFit.blend';objname=name
 elif '/RidgePiercer20260927/' in mesh:file='HighlandClaymoreMeshy20260922/RidgePiercerRootV2_20260927/Highland_RidgePiercer_RootV2_Editable.blend';objname=name
 elif '/HighlandClaymore20260922/' in mesh:
  file='HighlandClaymoreMeshy20260922/JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend';objname=stem
 else:raise RuntimeError('No authored source mapping '+mesh)
 obj=append(file,objname);obj.name='Icon_'+name
 for slot in obj.material_slots:
  for old,new in spec.get('materials',{}).items():
   if slot.material and slot.material.name.startswith(old) and 'FrostBronze' in new:
    slot.material=material('SharedSwordPommels20260920/SharedPommels_FrostFit.blend','FrostFinish_'+old)
 blade_material(obj)
 obj.location=Vector(spec.get('location_cm',[0,0,0]))*.01
 obj.scale=Vector(spec.get('scale',[1,1,1]))
 if any(spec.get('rotation_deg',[0,0,0])):raise RuntimeError('Explicit mount rotation needs an authored conversion: '+mesh)
 return obj,{'runtime_mesh':mesh,'source_blend':str(SRC/file),'source_object':objname,'runtime_spec':spec}

def rune(obj,oid,spec):
 if not oid or oid=='false':return
 masks=json.loads((P/'rune_sources.json').read_text())
 mode='erosion_rune' if oid=='spirit_burst_rune' else oid
 tint={'resonance_rune':(.008,.48,.42,1),'erosion_rune':(.30,.008,.62,1),
       'conduction_rune':(.008,.10,.68,1),'wild_rune':(.65,.008,.018,1),
       'golden_glow_rune':(.65,.26,.022,1),'spirit_burst_rune':(.018,.36,.72,1)}[oid]
 isgold=oid=='golden_glow_rune'
 imagepath=SRC/'NativeRuneGold20260922/T_RuneSword_NativeMask.png' if isgold else Path(masks[mode]['source'][0])
 # Match the runtime projection, with the UE top-origin texture coordinate converted to Blender V.
 uv=obj.data.uv_layers.new(name='IconRuneProjection')
 dim=spec.get('rune_dimensions_cm',[12,10,63])
 for loop in obj.data.loops:
  v=obj.data.vertices[loop.vertex_index].co
  uv.data[loop.index].uv=(.5+v.x/(dim[0]*.01*.92) if oid=='wild_rune' else .5-v.x/(dim[0]*.01), (v.z-dim[1]*.01)/(dim[2]*.01))
 for slot in obj.material_slots:
  if not slot.material:continue
  m=slot.material.copy();slot.material=m;N=m.node_tree.nodes;L=m.node_tree.links
  bs=next(n for n in N if n.type=='BSDF_PRINCIPLED')
  coords=N.new('ShaderNodeUVMap');coords.uv_map=obj.data.uv_layers[0].name if isgold else uv.name
  tex=N.new('ShaderNodeTexImage')
  tex.image=bpy.data.images.load(str(imagepath),check_existing=True) if isgold else rune_surface.make(oid,dim,weapon=='ue_frost_crystal_sword' and oid=='erosion_rune')
  tex.image.colorspace_settings.name='Non-Color';tex.extension='CLIP'
  L.new(coords.outputs['UV'],tex.inputs['Vector'])
  if not isgold:
   emission=N.new('ShaderNodeEmission');L.new(tex.outputs['Color'],emission.inputs['Color'])
   mixshader=N.new('ShaderNodeMixShader');L.new(tex.outputs['Alpha'],mixshader.inputs[0]);L.new(bs.outputs[0],mixshader.inputs[1]);L.new(emission.outputs[0],mixshader.inputs[2])
   output=next(n for n in N if n.type=='OUTPUT_MATERIAL');L.new(mixshader.outputs[0],output.inputs['Surface'])
   continue
  sep=N.new('ShaderNodeSeparateColor');L.new(tex.outputs['Color'],sep.inputs['Color'])
  strength=sep.outputs['Red']
  mix=N.new('ShaderNodeMixRGB');L.new(strength,mix.inputs[0]);mix.inputs[2].default_value=tint
  if bs.inputs['Base Color'].is_linked:L.new(bs.inputs['Base Color'].links[0].from_socket,mix.inputs[1])
  else:mix.inputs[1].default_value=bs.inputs['Base Color'].default_value
  L.new(mix.outputs[0],bs.inputs['Base Color'])
  mul=N.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.75 if weapon=='ue_frost_crystal_sword' and oid=='erosion_rune' else 1.25
  L.new(strength,mul.inputs[0]);L.new(mul.outputs[0],bs.inputs['Emission Strength']);bs.inputs['Emission Color'].default_value=tint
  for link in list(bs.inputs['Emission Color'].links):L.remove(link)

def tool_part(slot):
 kind='axe' if weapon=='tool_axe' else 'pickaxe';name='SM_BattleAxe' if kind=='axe' else 'SM_RusticPickaxe'
 file=f'ToolEnhance20260925/Icons/{kind}_upright.blend';obj=append(file,name)
 obj.data=obj.data.copy();mesh=obj.data
 # There are no separately modelled upgrades: extract the real stock region, without inventing alternatives.
 bm=bmesh.new();bm.from_mesh(mesh)
 wood={i for i,m in enumerate(mesh.materials) if m and 'Wood' in m.name}
 woodverts=[v.co.z for f in bm.faces if f.material_index in wood for v in f.verts]
 low,high=min(woodverts),max(woodverts);length=high-low
 if slot in ['grip','shaft']:
  remove=[f for f in bm.faces if f.material_index not in wood]
  bmesh.ops.delete(bm,geom=remove,context='FACES')
  if slot=='grip':
   bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,
    plane_co=(0,0,low+length*.36),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
 else:
  # Head and fitting both use the actual factory head/joint; these options are numerical only.
  remove=[f for f in bm.faces if f.material_index in wood]
  bmesh.ops.delete(bm,geom=remove,context='FACES')
 loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bm.to_mesh(mesh);bm.free();mesh.update()
 return [obj],[{'source_blend':str(SRC/file),'source_object':name,'numeric_only':True,
    'selection':slot,'fitting_note':'Actual stock head and joint reused; no independent fitting mesh exists.'}]

rows=[r for r in baseline['icons'] if r['weapon']==weapon]
keep={'ue_highland_claymore_pommel_highland_thorn_crown',
      'ue_rune_sword_pommel_ballast_hardened','ue_rune_sword_pommel_ballast_rune','ue_rune_sword_pommel_ballast_magic_orb'}
receipt_path=P/('render_'+weapon+('_sample' if only else '')+'.json')
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else []
finished={r['key']:r for r in receipt}
cache={}
def record(row):
 finished[row['key']]=row
 receipt_path.write_text(json.dumps(list(finished.values()),ensure_ascii=False,indent=2),encoding='utf-8')
for row in rows:
 key=row['key'];oid=row['id'];slot=row['slot']
 if only and only not in key:continue
 if key in keep:
  record(dict(row,action='retain',reason='Current authored model, level left-facing RGBA icon.'));continue
 cachekey=(slot,'false' if oid=='category' else oid)
 if weapon.startswith('tool_'):cachekey=(slot,'factory')
 if key in finished and (OUT/(key+'.png')).exists() and not only:
  cache[cachekey]=OUT/(key+'.png');continue
 if cachekey in cache:
  shutil.copy2(cache[cachekey],OUT/(key+'.png'))
  record(dict(row,action='copy',render_source=str(cache[cachekey])));continue
 for obj in list(scene.objects):
  if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
 if weapon.startswith('tool_'):objects,provenance=tool_part(slot)
 else:
  cat=runtime['catalogs'][weapon];partslot='blade_1' if slot=='blade_2' else slot
  partoid='factory' if oid in ['category','false'] or slot=='blade_2' else oid
  spec=cat['slots'][partslot][partoid]
  obj,origin=load_part(spec);objects=[obj];provenance=[origin]
  if 'adapter' in spec:
   ad,adsource=load_part(spec['adapter']);objects.append(ad);provenance.append(adsource)
  selected=oid if slot=='blade_2' and oid not in ['category','false'] else 'erosion_rune' if weapon=='ue_frost_crystal_sword' and partslot=='blade_1' else ''
  rune(obj,selected,spec)
 scene.view_layers[0].update()
 points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
 low=Vector(tuple(min(v[i] for v in points) for i in range(3)));high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
 center=(low+high)*.5;span=max(high.x-low.x,high.z-low.z)
 camera.location=center+Vector((0,-4*span,0));camera.data.ortho_scale=span/.83
 for lamp,offset,power,size in lights:
  lamp.location=center+offset*span;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
  lamp.data.energy=power*span*span;lamp.data.size=size*span
 scene.render.filepath=str(OUT/(key+'.png'))
 bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(SCENES/(key+'.blend')))
 bpy.ops.render.render(write_still=True)
 cache[cachekey]=OUT/(key+'.png')
 record(dict(row,action='render',source=provenance,resolution=[1024,1024],
     camera='-Y orthographic; +Z blade/head axis points left; +X up; no 2D mirroring',fill=.83,
     material_note='Authored PBR and runtime finish; rune animation frozen for the static icon.'))
 print('MELEE_ICON_RENDERED '+key,flush=True)
receipt_path.write_text(json.dumps(list(finished.values()),ensure_ascii=False,indent=2),encoding='utf-8')
print('MELEE_ICON_RENDER_COMPLETE '+weapon,flush=True)
