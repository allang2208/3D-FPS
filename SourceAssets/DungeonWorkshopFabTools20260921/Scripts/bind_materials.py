"""Retain original clean/worn PBR atlases, author per-tool service wear and pack sources."""
from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored'
manifest=json.loads((OUT/'manifest.json').read_text())
atlas=json.loads((ROOT/'Receipts/atlas-inputs.json').read_text())
textures={}
for variant,marker in [('Clean','_Material_New_'),('Worn','_Material_')]:
    textures[variant]={}
    for channel in ('BaseColor','Normal','Roughness','Metallic'):
        row=next(x for x in atlas['images'] if x['name'].endswith(marker+channel+'.png'))
        textures[variant][channel]=row['path']
wear={'Adjustable_Wrench':.48,'Bolt_Cutter':.62,'Chisel':.40,'Hand_Saw':.78,
      'Hammer':.57,'Nail_Puller':.72,'Pipe_Wrench':.66,'Pliers':.46,'Screwdriver':.36,'Wrench':.42}
bpy.ops.wm.open_mainfile(filepath=manifest['source_blend'])
variants={}
for zone in ('Wall','Bench'):
    for tool,amount in wear.items():
        if zone=='Bench':amount=max(.20,amount-.12)
        key=zone+'_'+tool
        m=bpy.data.materials.new('FabGarage_'+key);m.use_nodes=True;nt=m.node_tree
        p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Specular IOR Level'].default_value=.32
        for ch in ('BaseColor','Normal','Roughness','Metallic'):
            nodes=[]
            for v in ('Clean','Worn'):
                t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(textures[v][ch],check_existing=True)
                if ch!='BaseColor':t.image.colorspace_settings.name='Non-Color'
                nodes.append(t)
            mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[0].default_value=amount
            for i,t in enumerate(nodes):nt.links.new(t.outputs['Color'],mix.inputs[i+1])
            if ch=='Normal':
                n=nt.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.85
                nt.links.new(mix.outputs[0],n.inputs['Color']);nt.links.new(n.outputs[0],p.inputs['Normal'])
            elif ch=='Roughness':
                scale=nt.nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=.86
                bias=nt.nodes.new('ShaderNodeMath');bias.operation='ADD';bias.inputs[1].default_value=.055
                nt.links.new(mix.outputs[0],scale.inputs[0]);nt.links.new(scale.outputs[0],bias.inputs[0]);nt.links.new(bias.outputs[0],p.inputs['Roughness'])
            else:nt.links.new(mix.outputs[0],p.inputs['Base Color' if ch=='BaseColor' else 'Metallic'])
        variants[key]=m
for ob in bpy.data.objects:
    if ob.type!='MESH' or not any(m and m.name=='FabGarage_Atlas' for m in ob.data.materials):continue
    name=ob.name.removeprefix('SM_WSFab_').removeprefix('Source_')
    key=name if name in variants else 'Wall_'+name
    if key not in variants:continue
    for i,mat in enumerate(ob.data.materials):
        if mat and mat.name=='FabGarage_Atlas':ob.data.materials[i]=variants[key]
for e in manifest['objects']:
    if 'FabGarage_Atlas' not in e['materials']:continue
    name=e['name'].removeprefix('SM_WSFab_');key=name if name in variants else 'Wall_'+name
    e['garage_material']=key
    e['wear_blend']=max(.2,wear[key.removeprefix('Wall_').removeprefix('Bench_')]-(.12 if key.startswith('Bench_') else 0))
manifest.update(textures_ready=True,textures=textures,normal_convention='OpenGL; publisher Blender normal-map wiring',
                material_controls=dict(roughness_scale=.86,roughness_bias=.055,normal_strength=.85),
                material_strategy='Publisher clean/worn PBR atlas blend, varied by tool and working position; original UVs retained')
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=manifest['source_blend'])
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('FAB_MATERIALS_BOUND '+json.dumps(dict(texture_atlases=8,variants=len(variants),textures_ready=True)))
