"""Render the actual original bolt and carbon version in the existing M24 metal frame."""
import bpy,json,math,runpy
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;(O/'Icons').mkdir(exist_ok=True)
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
source=O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'
frame=(O.parent/'M24Modular20261027/author_icons.py').read_text(encoding='utf-8')
# Reuse exactly the existing modeled frame, neutral lighting and camera recipe.
frame=frame[frame.index('    def mat(name'):];frame='\n'.join(x[4:] if x.startswith('    ') else x for x in frame.splitlines())
records={}
for key in ('false','m24_carbon_light_bolt'):
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    keep=[bpy.data.objects[n] for n in ('M24_bolt','M24_boltrear')]
    for ob in keep:ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
    for ob in list(bpy.data.objects):
        if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
    s=bpy.context.scene
    m=bpy.data.materials.new('M24 current bolt finish '+key);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    p=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    def image(path,linear=False):
        z=n.new('ShaderNodeTexImage');z.image=bpy.data.images.load(str(path))
        if linear:z.image.colorspace_settings.name='Non-Color'
        return z
    def mix(f,a,b):
        z=n.new('ShaderNodeMixRGB')
        for i,v in enumerate((f,a,b)):
            if hasattr(v,'node'):l.new(v,z.inputs[i])
            else:z.inputs[i].default_value=v
        return z.outputs[0]
    def scalar(op,a,b):
        z=n.new('ShaderNodeMath');z.operation=op
        for i,v in enumerate((a,b)):
            if hasattr(v,'node'):l.new(v,z.inputs[i])
            else:z.inputs[i].default_value=v
        return z.outputs[0]
    orig=O.parent/'M24CustomScope20261026/Original/GLTF/textures'
    bc=image(orig/'sniper_baseColor.png');orm=image(orig/'sniper_metallicRoughness.png',True)
    parts=n.new('ShaderNodeSeparateColor');l.new(orm.outputs['Color'],parts.inputs['Color'])
    base=mix(.2,(.034,.036,.039,1),bc.outputs['Color']);metal=parts.outputs['Blue'];rough=.31
    if key!='false':
        mask=image(O/'Textures/T_M24_CarbonWeaveMask.png',True);sep=n.new('ShaderNodeSeparateColor');l.new(mask.outputs['Color'],sep.inputs['Color'])
        fiber=mix(sep.outputs['Green'],(.012,.014,.016,1),(.031,.034,.038,1))
        base=mix(sep.outputs['Red'],base,fiber);metal=scalar('MULTIPLY',metal,scalar('SUBTRACT',1,sep.outputs['Red']))
        carbonrough=scalar('ADD',scalar('SUBTRACT',.36,scalar('MULTIPLY',sep.outputs['Green'],.09)),scalar('MULTIPLY',sep.outputs['Blue'],.015))
        rough=mix(sep.outputs['Red'],(.31,.31,.31,1),carbonrough)
    l.new(base,p.inputs['Base Color']);l.new(metal,p.inputs['Metallic'])
    if hasattr(rough,'node'):l.new(rough,p.inputs['Roughness'])
    else:p.inputs['Roughness'].default_value=rough
    normal=image(O.parent/'M24Surface20261027/Textures/T_M24_Body_Refined_N.png',True)
    nm=n.new('ShaderNodeNormalMap');l.new(normal.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    for ob in keep:
        ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(m)
        for poly in ob.data.polygons:poly.material_index=0
    pts=[v.co for ob in keep for v in ob.data.vertices]
    lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
    center=(lo+hi)*.5;scale=1.23/max(hi.y-lo.y,hi.z-lo.z)
    for ob in keep:ob.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(-center));ob.location.x=-.17
    G['apply_grayscale'](keep)
    exec(compile(frame,'shared_m24_frame','exec'))
    records[key]={'objects':['M24_bolt','M24_boltrear'],'source':str(source),'forward':'+Y (screen left)','up':'+Z',
        'camera':[-3,0,0],'resolution':1024,'frame':'M24Modular20261027 modeled metal frame','asset_production_render':True}
(O/'icon_authoring.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
