"""Bake three static ornamental masks on the accepted blade UVs and make icon sources."""
import bpy,json,sys,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from asset_tools import *
plans=[p for p in json.loads((P/'design-prompts.json').read_text(encoding='utf-8'))['plans'] if p['slot']=='blade_2']
runpy.run_path(str(P.parent/'KukriRuneNatural20261027/prepare_layout.py'),run_name='__main__')
runpy.run_path(str(P.parent/'KukriRuneNatural20261027/bake_runes.py'),run_name='__main__')
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'KukriModules20261026/Kukri_Modules_Editable.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
blade=bpy.data.objects['SM_Kukri_Blade_Factory']
for o in scene.objects:o.hide_render=True;o.hide_set(True)
activate(blade)
receipt=json.loads((P/'runes.json').read_text(encoding='utf-8'))
icons=[]
for plan in plans:
    # Icon is the emblem itself, with a shallow metallic emboss, no blade slice.
    iconmat,it,ibs,iout=make_mat('Icon_'+plan['kind'])
    g=tex(it,P/'Concepts'/(plan['id']+'.png'));g.extension='CLIP'
    lum=node(it,'ShaderNodeRGBToBW');it.links.new(g.outputs[0],lum.inputs[0])
    mask=op(it,'GREATER_THAN',op(it,'MULTIPLY',lum.outputs[0],g.outputs['Alpha']),.92)
    ibs.inputs['Base Color'].default_value=(.5,.5,.5,1);ibs.inputs['Metallic'].default_value=.9;ibs.inputs['Roughness'].default_value=.3
    bump=node(it,'ShaderNodeBump');bump.inputs['Distance'].default_value=.00015;it.links.new(mask,bump.inputs['Height']);it.links.new(bump.outputs[0],ibs.inputs['Normal'])
    transparent=node(it,'ShaderNodeBsdfTransparent');blend=node(it,'ShaderNodeMixShader')
    it.links.new(mask,blend.inputs[0]);it.links.new(transparent.outputs[0],blend.inputs[1]);it.links.new(ibs.outputs[0],blend.inputs[2]);it.links.new(blend.outputs[0],iout.inputs['Surface'])
    mesh=bpy.data.meshes.new('Icon_'+plan['kind']);mesh.from_pydata([(-.02,0,-.02),(.02,0,-.02),(.02,0,.02),(-.02,0,.02)],[],[(0,1,2,3)])
    layer=mesh.uv_layers.new(name='UVMap')
    for item,value in zip(layer.data,[(0,0),(1,0),(1,1),(0,1)]):item.uv=value
    mesh.materials.append(iconmat);obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj);obj.hide_render=True;obj.hide_set(True);icons.append(obj)
    entry=next(e for e in receipt['runes'] if e['id']==plan['id'])
    entry.update(icon_key='blade_2_'+plan['id'],
        icon=str(P/'Icons'/('blade_2_'+plan['id']+'.png')),object=obj.name)
    print('RUNE_MASK_AUTHORED '+plan['id'],flush=True)
blade.hide_render=True;blade.hide_set(True)
(P/'runes.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Rune_Icons_Editable.blend'))
