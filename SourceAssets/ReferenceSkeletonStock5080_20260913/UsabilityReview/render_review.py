"""Actual candidate renders for the authorized usability review; source stays unchanged."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector, Matrix

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
source=ROOT/'seed_91379/SkeletonStock_5080_Candidate_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene
obs=[ob for ob in s.objects if ob.type=='MESH']
pts=[ob.matrix_world@Vector(v) for ob in obs for v in ob.bound_box]
lo=Vector([min(v[i] for v in pts) for i in range(3)])
hi=Vector([max(v[i] for v in pts) for i in range(3)])
center=(lo+hi)*.5;extent=hi-lo
axes=sorted(range(3),key=lambda i:extent[i],reverse=True)
along=Vector([float(i==axes[0]) for i in range(3)])
up=Vector([float(i==axes[1]) for i in range(3)])
side=along.cross(up).normalized();span=max(extent)
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1500;s.render.resolution_y=1100;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
s.view_settings.view_transform='AgX';s.view_settings.exposure=0
world=bpy.data.worlds.new('Review_Studio');world.use_nodes=True
world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs[0])
bg.inputs['Color'].default_value=(.09,.11,.14,1);bg.inputs['Strength'].default_value=.6;s.world=world

def area(name,direction,power,size):
    bpy.ops.object.light_add(type='AREA',location=center+direction*span)
    ob=bpy.context.object;ob.name=name;ob.data.energy=power*span*span;ob.data.size=size*span
    ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key',side*1.7+up*1.8-along*.5,100,1.8)
area('Fill',side*1.3-up*.2+along*1.2,40,2.0)
area('BackKey',-side*1.6+up*1.3,100,1.6)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';s.camera=cam
renders=[]

def render(name,direction):
    f=-direction.normalized();r=f.cross(up).normalized();u=r.cross(f).normalized()
    cam.location=center+direction.normalized()*span*3
    cam.rotation_euler=Matrix((r,u,-f)).transposed().to_euler()
    px=[(p-center).dot(r) for p in pts];py=[(p-center).dot(u) for p in pts]
    cam.data.ortho_scale=max(max(px)-min(px),(max(py)-min(py))*s.render.resolution_x/s.render.resolution_y)*1.15
    s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);renders.append(name+'.png')

diagnose='--diagnose' in sys.argv
if diagnose:
    render('diagnostic_original_material',side-along*.6+up*.22)
    for m in bpy.data.materials:
        if not m.node_tree: continue
        for node in m.node_tree.nodes:
            if node.type!='TEX_IMAGE' or not node.image: continue
            old=node.image
            filename='00_Image_0.png' if old.name=='Image_0' else '01_Image_1.png'
            replacement=bpy.data.images.load(str(ROOT/'seed_91379/Textures'/filename),check_existing=False)
            replacement.colorspace_settings.name=old.colorspace_settings.name
            node.image=replacement
    render('diagnostic_external_same_textures',side-along*.6+up*.22)
else:
    render('side_textured',side)
    render('opposite_textured',-side)
    render('angle_textured',side-along*.6+up*.22)
    render('front_socket_textured',-along+side*.15+up*.1)
clay=bpy.data.materials.new('Review_Constant_Clay');clay.use_nodes=True
bs=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value=(.32,.32,.32,1);bs.inputs['Roughness'].default_value=.42;bs.inputs['Metallic'].default_value=0
s.view_layers[0].material_override=clay
if diagnose:
    render('diagnostic_constant_clay',side-along*.6+up*.22)
else:
    render('side_clay',side)
    render('angle_clay',side-along*.6+up*.22)
receipt='diagnostic_render_receipt.json' if diagnose else 'render_receipt.json'
(OUT/receipt).write_text(json.dumps({'source':str(source),'images':renders,'source_saved_or_modified':False,'blender_extents':list(extent),'along_axis':axes[0],'up_axis':axes[1],'source_materials':[m.name for ob in obs for m in ob.data.materials],'review_type':'Blender source geometry and shading; not UE gameplay','light_powers':[100,40,100],'exposure':0},indent=2),encoding='utf-8')
print('REVIEW_RENDERS_COMPLETE',flush=True)
