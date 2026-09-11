"""Author and bake a green skin/wound pass without changing rig or mesh topology.
Fab inputs are NOT present: this pass uses existing Hunyuan maps and authored nodes.
"""
import bpy, json, sys, hashlib
from pathlib import Path
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910')
OUT=ROOT/'material_v03'; OUT.mkdir(exist_ok=True)
(OUT/'textures').mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'hunyuan_v01'))
import studio
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'death_v01/delivery/HandBrain_FiveActions.blend'))
s=bpy.context.scene
rig=bpy.data.objects['SK_HandBrain']
meshes=[o for o in s.objects if o.type=='MESH']
before={o.name:hashlib.sha256(b''.join(str(tuple(v.co)).encode() for v in o.data.vertices)).hexdigest() for o in meshes}
defs=json.loads((ROOT/'howl_rebuild_v02/delivery/ue_materials.json').read_text())
report={'fab_downloaded':False,'sources':'Existing Hunyuan textures plus locally authored procedural shading','materials':[]}

def pose(name,frame):
 a=bpy.data.actions[name];rig.animation_data.action=a
 if a.slots:rig.animation_data.action_slot=a.slots[0]
 s.frame_set(frame);bpy.context.view_layer.update()

pose('Idle',1)
cam=studio.setup(1024);s.cycles.samples=32
studio.aim(cam,(5,-3.8,2.7),(.1,0,1.1));cam.data.ortho_scale=2.65
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
 s.cycles.device='GPU'
except Exception as e:print('GPU fallback',str(e))
s.render.image_settings.file_format='PNG'
s.render.filepath=str(OUT/'Before.png');bpy.ops.render.render(write_still=True)

for obj in meshes:
 for slot,d in enumerate(defs[obj.name]):
  m=bpy.data.materials.new('Refined_'+obj.name+'_'+str(slot));m.use_nodes=True
  obj.data.materials[slot]=m;n=m.node_tree.nodes;links=m.node_tree.links;n.clear()
  def node(kind):return n.new(kind)
  def link(a,b):links.new(a,b)
  def math(op,a,b=None):
   q=node('ShaderNodeMath');q.operation=op
   for i,v in enumerate([a,b]):
    if v is None:continue
    if isinstance(v,(float,int)):q.inputs[i].default_value=v
    else:link(v,q.inputs[i])
   return q.outputs[0]
  def mix(a,b,f):
   q=node('ShaderNodeMixRGB');q.blend_type='MIX'
   for i,v in [(0,f),(1,a),(2,b)]:
    if isinstance(v,(tuple,list,float,int)):q.inputs[i].default_value=v
    else:link(v,q.inputs[i])
   return q.outputs[0]
  def mul(a,b):
   q=node('ShaderNodeMixRGB');q.blend_type='MULTIPLY';q.inputs[0].default_value=1
   for i,v in [(1,a),(2,b)]:
    if isinstance(v,(tuple,list)):q.inputs[i].default_value=v
    else:link(v,q.inputs[i])
   return q.outputs[0]
  def texture(sem):
   value=d.get(sem)
   if not isinstance(value,dict):return None
   img=bpy.data.images.load(str(ROOT/'howl_rebuild_v02/delivery'/value['file']),check_existing=False)
   img.colorspace_settings.name='sRGB' if sem=='BaseColor' else 'Non-Color'
   t=node('ShaderNodeTexImage');t.image=img
   return t.outputs['Color']
  out=node('ShaderNodeOutputMaterial');p=node('ShaderNodeBsdfPrincipled');link(p.outputs[0],out.inputs['Surface'])
  tc=node('ShaderNodeTexCoord')
  def noise(scale,detail):
   t=node('ShaderNodeTexNoise');t.inputs['Scale'].default_value=scale;t.inputs['Detail'].default_value=detail
   link(tc.outputs['Object'],t.inputs['Vector']);return t.outputs['Fac']
  broad=noise(17,3);fine=noise(180,2);pores=noise(950,2)
  bc=texture('BaseColor')
  oral='mucosa' in d['material'];teeth='teeth' in d['material']
  if oral:
   color=mix((.025,.003,.004,1),(.12,.017,.024,1),broad)
   rough=math('ADD',.22,math('MULTIPLY',fine,.12));bump_dist=.0006
  elif teeth:
   color=mix((.19,.14,.065,1),(.55,.46,.26,1),broad)
   rough=math('ADD',.32,math('MULTIPLY',fine,.12));bump_dist=.00015
  else:
   sep=node('ShaderNodeSeparateColor');link(bc,sep.inputs[0])
   wound=math('MULTIPLY',math('SUBTRACT',sep.outputs[0],math('MULTIPLY',sep.outputs[1],1.06)),16)
   wound=math('MINIMUM',1,math('MAXIMUM',0,wound))
   skin=mul(bc,(.40,.64,.28,1));blood=mul(bc,(.72,.29,.30,1))
   color=mix(skin,blood,wound)
   variation=mix((.70,.76,.64,1),(1.12,1.08,.94,1),broad);color=mul(color,variation)
   dry=math('ADD',.55,math('MULTIPLY',fine,.18));wet=math('ADD',.26,math('MULTIPLY',fine,.12))
   rough=math('ADD',math('MULTIPLY',dry,math('SUBTRACT',1,wound)),math('MULTIPLY',wet,wound));bump_dist=.0012
  link(color,p.inputs['Base Color']);link(rough,p.inputs['Roughness'])
  p.inputs['Subsurface Weight'].default_value=.035 if not teeth else .01
  p.inputs['Subsurface Radius'].default_value=(.7,.35,.18)
  p.inputs['Subsurface Scale'].default_value=.002
  p.inputs['Specular IOR Level'].default_value=.32
  bump=node('ShaderNodeBump');bump.inputs['Strength'].default_value=.5;bump.inputs['Distance'].default_value=bump_dist
  link(math('ADD',math('MULTIPLY',pores,.7),math('MULTIPLY',fine,.3)),bump.inputs['Height'])
  normal=texture('Normal_DirectX')
  if normal:
   sep=node('ShaderNodeSeparateColor');link(normal,sep.inputs[0]);combine=node('ShaderNodeCombineColor')
   link(sep.outputs[0],combine.inputs[0]);link(math('SUBTRACT',1,sep.outputs[1]),combine.inputs[1]);link(sep.outputs[2],combine.inputs[2])
   norm=node('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=1.2;link(combine.outputs[0],norm.inputs['Color']);link(norm.outputs[0],bump.inputs['Normal'])
  link(bump.outputs[0],p.inputs['Normal'])
  m['bake_base_node']=color.node.name;m['bake_base_socket']=color.name
  m['bake_rough_node']=rough.node.name;m['bake_rough_socket']=rough.name
  report['materials'].append({'object':obj.name,'slot':slot,'name':m.name,'semantic':'mouth' if oral else 'teeth' if teeth else 'skin_wound'})

pose('Idle',1);s.render.filepath=str(OUT/'After.png');bpy.ops.render.render(write_still=True)
studio.aim(cam,(4,-2.5,2.2),(.4,-.05,1.2));cam.data.ortho_scale=1.45
s.render.filepath=str(OUT/'Skin_closeup.png');bpy.ops.render.render(write_still=True)
pose('Attack_Howl',34);studio.aim(cam,(5,-2.4,2.3),(.4,0,1.1));cam.data.ortho_scale=2.7
s.render.filepath=str(OUT/'Howl.png');bpy.ops.render.render(write_still=True)
pose('Idle',1)
assert before=={o.name:hashlib.sha256(b''.join(str(tuple(v.co)).encode() for v in o.data.vertices)).hexdigest() for o in meshes}
report['topology_and_vertex_positions_unchanged']=True
report['bones']=len(rig.data.bones)
report['actions']={a.name:float((a.frame_range[1]-a.frame_range[0])/30) for a in bpy.data.actions}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HandBrain_Refined.blend'))
(OUT/'material_report.json').write_text(json.dumps(report,indent=2))
print('HANDBRAIN_REFINED_PREVIEW_COMPLETE')
