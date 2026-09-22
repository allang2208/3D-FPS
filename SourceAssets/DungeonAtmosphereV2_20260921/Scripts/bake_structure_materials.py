"""Bake authored periodic PBR surfaces for the precise Blender structure.

This is texture production, not a scene preview or acceptance render.
"""
import bpy
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='CUDA';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='CUDA']
    for d in prefs.devices:d.use=d in devices
    if devices:scene.cycles.device='GPU'
except TypeError:
    pass
bpy.ops.mesh.primitive_plane_add(size=2)
plane=bpy.context.object
scene.render.bake.margin=8
scene.render.bake.use_clear=True

def n(nodes,typ):return nodes.new(typ)
def mathnode(nodes,links,op,a,b=None):
    x=n(nodes,'ShaderNodeMath');x.operation=op
    if hasattr(a,'node'):links.new(a,x.inputs[0])
    else:x.inputs[0].default_value=a
    if b is not None:
        if hasattr(b,'node'):links.new(b,x.inputs[1])
        else:x.inputs[1].default_value=b
    return x.outputs[0]
def ramp(nodes,links,source,stops):
    x=n(nodes,'ShaderNodeValToRGB');links.new(source,x.inputs[0])
    x.color_ramp.elements.remove(x.color_ramp.elements[1])
    for i,(position,color) in enumerate(stops):
        e=x.color_ramp.elements[0] if i==0 else x.color_ramp.elements.new(position)
        e.position=position;e.color=(*color,1)
    return x.outputs[0]
def noise(nodes,links,vector,w,scale,detail=4):
    x=n(nodes,'ShaderNodeTexNoise');x.noise_dimensions='4D';x.inputs['Scale'].default_value=scale
    x.inputs['Detail'].default_value=detail;x.inputs['Roughness'].default_value=.72
    links.new(vector,x.inputs['Vector']);links.new(w,x.inputs['W']);return x.outputs['Fac']

recipes={
 'Concrete':{'colors':[(.22,(.095,.105,.10)),(.50,(.23,.245,.222)),(.76,(.38,.39,.355))],'rough':(.64,.92),'metal':0,'depth':.025},
 'IvoryTile':{'colors':[(.19,(.12,.105,.07)),(.41,(.38,.35,.26)),(.70,(.59,.565,.455))],'rough':(.22,.63),'metal':0,'depth':.004},
 'PaintedSteel':{'colors':[(.17,(.055,.038,.019)),(.31,(.14,.067,.023)),(.39,(.063,.075,.043)),(.80,(.16,.18,.102))],'rough':(.36,.82),'metal':.10,'depth':.008},
 'BareSteel':{'colors':[(.18,(.09,.044,.016)),(.40,(.06,.067,.064)),(.79,(.18,.19,.182))],'rough':(.30,.72),'metal':.78,'depth':.004},
 'AncientStone':{'colors':[(.17,(.075,.065,.040)),(.49,(.225,.205,.149)),(.78,(.39,.36,.28))],'rough':(.73,.95),'metal':0,'depth':.035}}
manifest={}
for name,r in recipes.items():
    paths={key:OUT/(name+'_'+key+'.png') for key in ('BaseColor','Roughness','Metallic','Normal')}
    manifest[name]={k:str(p) for k,p in paths.items()}
    if all(p.exists() for p in paths.values()):continue
    mat=bpy.data.materials.new('V2_'+name+'_Bake');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    uv=n(nodes,'ShaderNodeTexCoord');separate=n(nodes,'ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],separate.inputs[0])
    au=mathnode(nodes,links,'MULTIPLY',separate.outputs['X'],math.tau)
    av=mathnode(nodes,links,'MULTIPLY',separate.outputs['Y'],math.tau)
    xyz=n(nodes,'ShaderNodeCombineXYZ')
    links.new(mathnode(nodes,links,'COSINE',au),xyz.inputs['X']);links.new(mathnode(nodes,links,'SINE',au),xyz.inputs['Y'])
    links.new(mathnode(nodes,links,'COSINE',av),xyz.inputs['Z']);w=mathnode(nodes,links,'SINE',av)
    macro=noise(nodes,links,xyz.outputs[0],w,1.6)
    medium=noise(nodes,links,xyz.outputs[0],w,13)
    grain=noise(nodes,links,xyz.outputs[0],w,112,2)
    combined=mathnode(nodes,links,'ADD',mathnode(nodes,links,'MULTIPLY',macro,.72),mathnode(nodes,links,'MULTIPLY',medium,.28))
    color=ramp(nodes,links,combined,r['colors'])
    rough=ramp(nodes,links,medium,[(.14,(r['rough'][0],)*3),(.83,(r['rough'][1],)*3)])
    height=mathnode(nodes,links,'ADD',mathnode(nodes,links,'MULTIPLY',medium,.72),mathnode(nodes,links,'MULTIPLY',grain,.28))
    bump=n(nodes,'ShaderNodeBump');bump.inputs['Strength'].default_value=.55;bump.inputs['Distance'].default_value=r['depth']
    links.new(height,bump.inputs['Height'])
    bsdf=n(nodes,'ShaderNodeBsdfPrincipled');links.new(color,bsdf.inputs['Base Color']);links.new(rough,bsdf.inputs['Roughness'])
    bsdf.inputs['Metallic'].default_value=r['metal'];links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    out=n(nodes,'ShaderNodeOutputMaterial');emission=n(nodes,'ShaderNodeEmission')
    plane.data.materials.clear();plane.data.materials.append(mat)
    for key,path in paths.items():
        image=bpy.data.images.new(name+'_'+key,2048,2048,alpha=False,float_buffer=False)
        image.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
        tex=n(nodes,'ShaderNodeTexImage');tex.image=image;nodes.active=tex;tex.select=True
        if key=='Normal':
            links.new(bsdf.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='NORMAL')
        else:
            if key=='Metallic':
                for link in list(emission.inputs['Color'].links):links.remove(link)
                emission.inputs['Color'].default_value=(r['metal'],r['metal'],r['metal'],1)
            else:links.new(color if key=='BaseColor' else rough,emission.inputs['Color'])
            links.new(emission.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(path);image.file_format='PNG';image.save()
        nodes.remove(tex);bpy.data.images.remove(image)
        print('BAKED',name,key,flush=True)
    links.new(bsdf.outputs[0],out.inputs['Surface'])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/SurfaceMaterials_Source.blend'))
(ROOT/'Authored/material-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('PBR_SURFACES_AUTHORED',len(manifest),'no scene rendering')
