"""Cosmetic game props: closed shotshells and carton packaging, in centimetres.
No functional internal ammunition geometry. Authoring/baking/export only.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

OUT=Path(__file__).parent/'Models'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
scene.render.engine='CYCLES';scene.cycles.samples=8

def material(name,color,metal=0,rough=.8):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m

# Bake reusable paper fibres/grain from a native shader into a tileable mask.
# The exported mesh and UE materials share this generated surface, not a photo projection.
bpy.ops.mesh.primitive_plane_add(size=2)
plane=bpy.context.object; grain=material('GrainBake',(1,1,1));plane.data.materials.append(grain)
nodes=grain.node_tree.nodes;links=grain.node_tree.links
tex=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=180
noise.inputs['Detail'].default_value=2.;links.new(tex.outputs['UV'],noise.inputs['Vector'])
emit=nodes.new('ShaderNodeEmission');links.new(noise.outputs['Fac'],emit.inputs['Color']);links.new(emit.outputs[0],nodes.get('Material Output').inputs[0])
img=bpy.data.images.new('PaperGrain',width=512,height=512,alpha=False);img.colorspace_settings.name='Non-Color'
target=nodes.new('ShaderNodeTexImage');target.image=img;nodes.active=target
bpy.ops.object.bake(type='EMIT');img.filepath_raw=str(OUT/'PaperGrain.png');img.file_format='PNG';img.save()
bpy.data.objects.remove(plane,do_unlink=True)

M={
 'Carton':material('Carton',(.043,.048,.054),0,.89),
 'PaperEdge':material('PaperEdge',(.39,.25,.125),0,.94),
 'Brass':material('Brass',(.53,.31,.085),1,.28),
 'Primer':material('Primer',(.35,.32,.27),1,.4),
 'SlugMetal':material('SlugMetal',(.24,.25,.27),1,.4),
 'Ink':material('Ink',(.72,.67,.55),0,.9),
 'CrimpShadow':material('CrimpShadow',(.055,.025,.012),0,.72),
}
for key in ['Carton','PaperEdge']:
    mat=M[key];ns=mat.node_tree.nodes;ls=mat.node_tree.links;bs=ns.get('Principled BSDF')
    sample=ns.new('ShaderNodeTexImage');sample.image=img
    mult=ns.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=.28
    mult.inputs[1].default_value=bs.inputs['Base Color'].default_value
    ls.new(sample.outputs['Color'],mult.inputs[2]);ls.new(mult.outputs[0],bs.inputs['Base Color'])

def finish(obj,mat):
    obj.data.materials.append(mat)
    return obj
def box(name,loc,size,mat,bevel=.018,rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    ob=bpy.context.object;ob.name=name;ob.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if rotation:ob.rotation_euler=rotation
    finish(ob,mat)
    if bevel:
        mod=ob.modifiers.new('Fold edge','BEVEL');mod.width=bevel;mod.segments=2
        mod=ob.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return ob
def lathe(name,rings,mat,segments=64,ribs=0,cap_top=True):
    verts=[];faces=[]
    for radius,z in rings:
        for j in range(segments):
            t=2*math.pi*j/segments
            r=radius+(0.012*math.cos(t*24) if ribs and radius>.85 else 0)
            verts.append((r*math.cos(t),r*math.sin(t),z))
    for i in range(len(rings)-1):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    faces.append(tuple(reversed(range(segments))))
    if cap_top:faces.append(tuple((len(rings)-1)*segments+j for j in range(segments)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob);finish(ob,mat)
    for p in mesh.polygons:p.use_smooth=len(p.vertices)==4
    return ob
def label(text,loc,size,mat):
    curve=bpy.data.curves.new(text,'FONT');curve.body=text;curve.align_x='CENTER';curve.size=size;curve.extrude=.0005;curve.resolution_u=3
    ob=bpy.data.objects.new(text,curve);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(math.pi/2,0,0);curve.materials.append(mat)
    bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob.select_set(False)
    return ob
def crimp(mat):
    verts=[(0,0,6.16)];faces=[]
    for radius in [.55,.984]:
        for j in range(32):
            t=2*math.pi*j/32
            z=6.30 if radius>.9 else 6.20+.075*math.sin((j%4)*math.pi/4)
            verts.append((radius*math.cos(t),radius*math.sin(t),z))
    for j in range(32):
        a=j+1;b=(j+1)%32+1
        faces.append((0,a,b));faces.append((a,a+32,b+32,b))
    # Close this cap below the visible fold, so the item has no open tips.
    faces.append(tuple(reversed(range(33,65))))
    mesh=bpy.data.meshes.new('SealedCrimp');mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new('SealedCrimp',mesh);scene.collection.objects.link(ob);finish(ob,mat);return ob

def apply_join(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select_set(True);bpy.context.view_layer.objects.active=ob
        for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
    return ob

def export(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,use_mesh_modifiers=True)

report={'units':'centimetres','reference':'Existing ammo_556/ammo_762 open cartons; current 12g item icons',
        'scope':'Cosmetic external props only','materials':{},'meshes':[]}
variants=[('Buckshot','00 BUCK',(.36,.016,.012),(.085,.13,.065)),
          ('Flechette','FLECHETTE',(.115,.14,.055),(.035,.075,.125)),
          ('Slug','SLUG',(.015,.048,.22),(.035,.075,.125))]
all_objects=[]
for variant,caption,color,stripe in variants:
    hull=material('Hull_'+variant,color,0,.38);band=material('Band_'+variant,stripe,0,.87)
    parts=[lathe('PlasticHull',[(.985,.82),(1.,.98),(1.,6.22),(.97,6.3)],hull,96,1,False),
           lathe('BrassHead',[(1.055,0),(1.055,.09),(.992,.14),(.992,1.07),(.982,1.12)],M['Brass']),
           lathe('Primer',[(.285,-.003),(.30,.012),(.30,.035)],M['Primer'],32)]
    if variant=='Slug':
        parts.append(lathe('SolidVisibleSlug',[(.83,6.17),(.83,6.29),(.76,6.40),(.55,6.5),(.10,6.55)],M['SlugMetal'],64))
        parts.append(lathe('RolledHullLip',[(.94,6.23),(.99,6.29),(.97,6.35),(.87,6.35),(.84,6.28)],hull,64))
    else:parts.append(crimp(hull))
    shell=apply_join(parts,'SM_12G_'+variant+'_Shell');export(shell)
    report['meshes'].append({'name':shell.name,'slots':[m.name for m in shell.data.materials],'kind':'shell','triangles':sum(len(p.vertices)-2 for p in shell.data.polygons)})
    shell.hide_set(True);shell.hide_render=True;all_objects.append(shell)
    carton=[];width=11.9;depth=4.85;h=5.55;th=.12
    carton.append(box('Bottom',(0,0,th/2),(width,depth,th),M['PaperEdge']))
    carton.append(box('FrontWall',(0,-depth/2+th/2,h/2),(width,th,h),M['Carton']))
    carton.append(box('BackWall',(0,depth/2-th/2,3.15),(width,th,6.3),M['Carton']))
    for s in [-1,1]:carton.append(box('SideWall',(s*(width/2-th/2),0,3.0),(th,depth,6.0),M['Carton']))
    # Interior liners stop printed paper from appearing inside the carton.
    carton.append(box('FrontLiner',(0,-depth/2+.13,2.76),(width-.24,.014,5.3),M['PaperEdge'],.002))
    carton.append(box('BackLiner',(0,depth/2-.13,3.04),(width-.24,.014,5.96),M['PaperEdge'],.002))
    angle=math.radians(-115);hinge=Vector((0,depth/2-.12,6.24));v=Vector((0,-2.1,0));v.rotate(__import__('mathutils').Euler((angle,0,0)))
    carton.append(box('OpenLid',hinge+v,(width,4.2,.1),M['Carton'],.035,(angle,0,0)))
    v=Vector((0,-2.1,-.054));v.rotate(__import__('mathutils').Euler((angle,0,0)))
    carton.append(box('LidPaperInside',hinge+v,(width-.12,4.08,.008),M['PaperEdge'],.002,(angle,0,0)))
    carton.append(box('FrontBand',(0,-depth/2-.006,2.95),(width-.28,.016,3.5),band,.015))
    carton.append(label('12 GA',(0,-depth/2-.019,3.25),1.72,M['Ink']))
    carton.append(label(caption,(0,-depth/2-.020,1.75),.75 if variant=='Flechette' else 1.03,M['Ink']))
    for row in range(2):
        for col in range(5):
            duplicate=bpy.data.objects.new('PackedShell',shell.data.copy());scene.collection.objects.link(duplicate)
            reduction=duplicate.modifiers.new('Packed shell detail budget','DECIMATE');reduction.ratio=.5
            duplicate.location=(-4.36+2.18*col,-1.09+2.18*row,.18);carton.append(duplicate)
    # Small exposed fibre edges and folded seam emphasize real paper thickness.
    for s in [-1,1]:
        carton.append(box('FrontFold',(s*(width/2-.095),-depth/2-.012,h/2),(.055,.019,h-.04),M['PaperEdge'],.008))
    pack=apply_join(carton,'SM_12G_'+variant+'_Box');export(pack);all_objects.append(pack)
    report['meshes'].append({'name':pack.name,'slots':[m.name for m in pack.data.materials],'kind':'box','triangles':sum(len(p.vertices)-2 for p in pack.data.polygons),'dimensions_cm':list(pack.dimensions)})
    pack.hide_set(True);pack.hide_render=True

for mat in bpy.data.materials:
    if mat.name=='GrainBake':continue
    bs=mat.node_tree.nodes.get('Principled BSDF')
    report['materials'][mat.name]={'color':list(mat.diffuse_color),'metallic':bs.inputs['Metallic'].default_value,'roughness':bs.inputs['Roughness'].default_value,'paper_grain':mat.name in ['Carton','PaperEdge']}
for i,ob in enumerate(all_objects):ob.hide_set(False);ob.hide_render=False;ob.location.x=(i//2)*18;ob.location.y=-7 if i%2==0 else 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ShotgunAmmoModels.blend'))
(OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('AMMO_MODELS_EXPORTED '+str(OUT))
