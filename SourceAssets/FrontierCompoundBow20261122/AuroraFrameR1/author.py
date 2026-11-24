"""Build the approved Aurora trim as closed, layered geometry on the shipping Frontier rig."""
from pathlib import Path
import json
import math
import os

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

src = Path(__file__).resolve().parent
family = src.parent
batch = Path(os.environ['AURORA_BATCH'])
wheel_master = Path(os.environ.get('FRONTIER_R11_MASTER',str(batch.parents[2]/'ArtReviews/FrontierCompoundBow/CamLinesR11_20261123/FactoryRevised.blend')))
bpy.ops.wm.open_mainfile(filepath=str(family/'EclipseFrameR1/Frontier_Eclipse.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
rig=scene.objects['Armature']
rig.data.pose_position='REST'
scene.frame_set(1)
with bpy.data.libraries.load(str(wheel_master),link=False) as (assets, incoming):
    incoming.objects=['UpperCam','LowerCam']
for name,donor in zip(('UpperCam','LowerCam'),incoming.objects):
    target=scene.objects[name]
    if [g.name for g in donor.vertex_groups] != [g.name for g in target.vertex_groups]:
        raise ValueError('R11 cam weights differ: '+name)
    target.data=donor.data.copy()
    for slot in target.material_slots:
        if slot.material.name.startswith('M_Frontier_Cord'):slot.material=bpy.data.materials['M_Frontier_Cord']
        if slot.material.name.startswith('M_Frontier_Surface'):slot.material=bpy.data.materials['M_Frontier_Surface']
    bpy.data.objects.remove(donor,do_unlink=True)

finish=bpy.data.materials.new('M_Aurora_Frame')
finish.use_nodes=True
nodes=finish.node_tree.nodes
link=finish.node_tree.links.new
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for key in ('Color','ORM','Normal','Glow'):
    texture=nodes.new('ShaderNodeTexImage')
    image=bpy.data.images.load(str(src/'Textures'/('T_Aurora_'+key+'.png')))
    if key in ('ORM','Normal'):image.colorspace_settings.name='Non-Color'
    if key=='ORM':image.alpha_mode='CHANNEL_PACKED'
    texture.image=image
    if key=='Color':link(texture.outputs['Color'],shader.inputs['Base Color'])
    if key=='ORM':
        sep=nodes.new('ShaderNodeSeparateColor');link(texture.outputs['Color'],sep.inputs[0])
        link(sep.outputs['Green'],shader.inputs['Roughness']);link(sep.outputs['Blue'],shader.inputs['Metallic'])
        link(texture.outputs['Alpha'],shader.inputs['Coat Weight']);shader.inputs['Coat Roughness'].default_value=.19
    if key=='Normal':
        split=nodes.new('ShaderNodeSeparateColor');link(texture.outputs[0],split.inputs[0])
        invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1;link(split.outputs['Green'],invert.inputs[1])
        rgb=nodes.new('ShaderNodeCombineColor')
        for label,sock in [('Red',split.outputs['Red']),('Green',invert.outputs[0]),('Blue',split.outputs['Blue'])]:link(sock,rgb.inputs[label])
        normal=nodes.new('ShaderNodeNormalMap');link(rgb.outputs[0],normal.inputs['Color']);link(normal.outputs['Normal'],shader.inputs['Normal'])
    if key=='Glow':
        link(texture.outputs['Color'],shader.inputs['Emission Color'])
        shader.inputs['Emission Strength'].default_value=1.0

shell=scene.objects['Riser']  # factory grip/pockets/accessory seats, with only the replaceable webs cut away
parts=[]
for obj in list(scene.objects):
    if not obj.name.startswith('Eclipse_'):continue
    if obj.name in ('Eclipse_SightSeat','Eclipse_CableGuideHeel'):
        obj.name=obj.name.replace('Eclipse','Aurora')
        obj.data.materials.clear();obj.data.materials.append(finish)
        for uv in obj.data.uv_layers.active.data:
            uv.uv=(.70+.08*uv.uv.x,.1+.76*uv.uv.y)
        parts.append(obj)
    else:
        bpy.data.objects.remove(obj,do_unlink=True)
hardware=[scene.objects[n] for n in ('UpperLimb','LowerLimb','UpperCam','LowerCam','ControlCable1','ControlCable2')]
profiles=json.loads((src/'traced_regions.json').read_text())

def in_loop(point, loop):
    # Even-odd winding, with the centroid always strictly inside its triangle.
    x,y=point; inside=False
    for a,b in zip(loop,loop[1:]+loop[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside

def place(px,high):
    a,b,p,q=((214+917j,502+34j,2+4.95j,12.3+38.9j) if high else (467+982j,535+464j,1.1-7.9j,10.8-28.8j))
    # Similarity transform preserves the elevation and apertures of the approved applique.
    t=(complex(*px)-a)/(b-a)
    mapped=p+(q-p)*(t.conjugate() if high else t)
    return mapped.real,mapped.imag

def build(profile):
    name=profile['name']; cell=name[-1].isdigit(); high=name.startswith('Upper')
    loops=profile['loops']; border=[]; edges=[]; chains=[]
    for loop in loops:
        first=len(border)
        border.extend(loop)
        ids=list(range(first,len(border)));chains.append(ids)
        edges.extend(zip(ids,ids[1:]+ids[:1]))
    raw=border+[p[:2] for p in profile['interior']]
    depths=[0.0]*len(border)+[p[2] for p in profile['interior']]
    points,_,faces,source,_,_=delaunay_2d_cdt([Vector(p) for p in raw],edges,[],0,.00002)
    triangles=[]
    for tri in faces:
        center=sum((points[i] for i in tri),Vector((0,0)))/len(tri)
        if in_loop(center,loops[0]) and not any(in_loop(center,hole) for hole in loops[1:]):
            triangles.append(tri)
    depths2=[max((depths[i] for i in srcids),default=0) for srcids in source]
    remap={old:new for new,old_list in enumerate(source) for old in old_list}
    coords=[place(pt,high) for pt in points]
    verts=[]; faces=[]; tex=[]; smooth=[]
    def face(idx,uvs,curved):
        faces.append(idx);tex.append(uvs);smooth.append(curved)
    def footprint(p,kind):
        if kind=='paint':return ((p.x+.5)/1024,1-(p.y+.5)/1024)
        return (.655+.14*p.x/640,.05+.9*p.y/1024)
    for front in (True,False):
        for (x,z),d in zip(coords,depths2):
            if cell:
                # Independent enamel with a rounded meniscus and skirts buried in its silver setting.
                y=1.49+.20*(1-math.exp(-d/6.7)) if front else 1.25
            elif front:
                y=1.23+.22*(1-math.exp(-d/3.1))
            else:
                y=-1.24-.12*(1-math.exp(-d/3.1))
            verts.append((x,y,z))
    count=len(points)
    for tri in triangles:
        for back in (False,True):
            ids=list(reversed(tri)) if back else list(tri)
            face([i+count*int(back) for i in ids],[footprint(points[i],'inside' if back else 'paint') for i in ids],True)
    for chain in chains:
        dist=0
        length=max(1,sum((points[remap[v]]-points[remap[w]]).length for v,w in zip(chain,chain[1:]+chain[:1])))
        for old_a,old_b in zip(chain,chain[1:]+chain[:1]):
            a,b=remap[old_a],remap[old_b]
            if a==b:continue
            step=(points[a]-points[b]).length
            lo=.05+.88*dist/length
            dist+=step
            hi=lo+.88*step/length
            face([a,b,b+count,a+count],[(.73,lo),(.73,hi),(.81,hi),(.81,lo)],False)
    mesh=bpy.data.meshes.new('Aurora_'+name)
    mesh.from_pydata(verts,[],faces);mesh.materials.append(finish);mesh.update()
    uv=mesh.uv_layers.new(name=shell.data.uv_layers.active.name)
    for poly,uvs,shade in zip(mesh.polygons,tex,smooth):
        poly.use_smooth=shade
        for idx,pair in zip(poly.loop_indices,uvs):uv.data[idx].uv=pair
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new('Aurora_'+name+('_Enamel' if cell else '_SilverFrame'),mesh)
    scene.collection.objects.link(obj);obj.parent=rig
    obj.vertex_groups.new(name='bow_body_root').add(list(range(len(verts))),1.0,'REPLACE')
    mod=obj.modifiers.new('Frontier rig','ARMATURE');mod.object=rig
    parts.append(obj)

for profile in profiles:build(profile)
def select(objects,active):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=active
copies=[]
for obj in [shell,*hardware,*parts]:
    ob=obj.copy();ob.data=obj.data.copy();scene.collection.objects.link(ob);copies.append(ob)
select(copies,copies[0]);bpy.ops.object.join()
export=copies[0];export.name='SK_Frontier_Aurora'
select([rig,export],rig)
bpy.ops.export_scene.fbx(filepath=str(src/'Export/SK_Frontier_Aurora.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.data.objects.remove(export,do_unlink=True)
for image in bpy.data.images:
    if image.source=='FILE' and not image.packed_file and Path(bpy.path.abspath(image.filepath)).is_file():image.pack()
rig.data.pose_position='POSE';scene.frame_set(1);select(parts,parts[0])
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(src/'Frontier_Aurora.blend'),compress=True)
