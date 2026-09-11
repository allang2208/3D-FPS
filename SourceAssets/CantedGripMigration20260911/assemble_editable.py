import bpy,json
from pathlib import Path
O=Path(__file__).parent
for weapon,variant in [('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]:
 d=O/weapon/variant;prefix=f'A_{weapon.upper()}_{"Canted" if weapon=="m4" else variant}_';build=json.loads((d/('animation_build.json' if weapon=='m4' else 'build.json')).read_text());bpy.ops.wm.open_mainfile(filepath=str(d/(prefix+'idle.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 for clip in build:
  if clip=='idle':continue
  name=prefix+clip
  with bpy.data.libraries.load(str(d/(name+'.blend')),link=False) as (src,dst):dst.actions=[name]
  dst.actions[0].use_fake_user=True
 a=bpy.data.actions[prefix+'idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);s.frame_end=build['idle']['frames'];r['grip_animation_family']=prefix;r['source_sample_rate']=60 if weapon=='m4' else 120
 for m in bpy.data.materials:
  if m.name.startswith('AKM_AdapterSteel'):
   m.use_nodes=True;n=next((x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
   if n is None:
    n=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=next((x for x in m.node_tree.nodes if x.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(n.outputs['BSDF'],out.inputs['Surface'])
   n.inputs['Base Color'].default_value=(.032,.04,.046,1);n.inputs['Metallic'].default_value=.85;n.inputs['Roughness'].default_value=.32
 bpy.ops.wm.save_as_mainfile(filepath=str(d/(weapon.upper()+'_'+variant+'_Family_Editable.blend')));print('EDITABLE_FAMILY',weapon,variant,len(build),flush=True)
