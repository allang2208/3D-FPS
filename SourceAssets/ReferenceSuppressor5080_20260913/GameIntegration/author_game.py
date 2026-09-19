"""Produce fitted game meshes and structural normal bake; no runtime/acceptance renders."""
import bpy
import bmesh
import math
import json
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
SOURCE=ROOT/'KnurlRefinedV1/Suppressor_KnurlRefinedV1.blend'
T=OUT/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
high=[o for o in s.objects if o.type=='MESH']
body=next(o for o in high if o.name=='geometry_0')
# Rear-facing cap surface is the mount datum; ornament bounds do not define it.
rear_faces=[p for p in body.data.polygons if p.normal.x<-.8 and p.center.x<-.47 and .025<math.hypot(p.center.y,p.center.z)<.085]
mount_x=float(np.median([p.center.x for p in rear_faces]))
front_x=max(v.co.x for o in high for v in o.data.vertices)

def select(objects,active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=active or objects[-1]

def material(name,color,rough=.5,metal=.9):
    m=bpy.data.materials.new(name);m.use_nodes=True
    m.node_tree.nodes.clear()
    bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    return m

shell=material('TacticalShell',(.025,.029,.033))
recess=material('TacticalRecess',(.006,.007,.009),.8,.1)
mount=material('TacticalMount',(.025,.029,.033))
low=[]
for ob in high:
    copy=ob.copy();copy.data=ob.data.copy();copy.name='GAME_'+ob.name;s.collection.objects.link(copy)
    select([copy]);copy.data.calc_loop_triangles()
    target=24000 if ob==body else 40000
    dec=copy.modifiers.new('Game silhouette reduction','DECIMATE');dec.ratio=min(1.,target/len(copy.data.loop_triangles));dec.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=dec.name)
    low.append(copy)
select(low,low[0]);bpy.ops.object.join();game=bpy.context.object;game.name='TacticalSuppressor_GameBase'
game.data.materials.clear();game.data.materials.append(shell);game.data.materials.append(recess)
for p in game.data.polygons:
    radial=Vector((0,p.center.y,p.center.z))
    p.material_index=1 if p.normal.dot(radial)<-.001 else 0
while game.data.uv_layers:game.data.uv_layers.remove(game.data.uv_layers[-1])
game.data.uv_layers.new(name='StructureUV')
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008,area_weight=.2,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
normal=bpy.data.images.new('T_TacticalSuppressor_Normal',width=2048,height=2048,alpha=False)
normal.colorspace_settings.name='Non-Color'
for m in [shell,recess]:
    node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=normal;m.node_tree.nodes.active=node
s.render.engine='CYCLES';s.cycles.samples=8
s.render.bake.use_selected_to_active=True;s.render.bake.use_clear=True;s.render.bake.margin=12
s.render.bake.cage_extrusion=.006;s.render.bake.max_ray_distance=.016
select(high+[game],game)
bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
normal.filepath_raw=str(T/(normal.name+'.png'));normal.file_format='PNG';normal.save()
print('TACTICAL_STRUCTURE_NORMAL_BAKED',flush=True)
for ob in high:ob.hide_render=True;ob.hide_set(True)
for m in [shell,recess]:
    n=m.node_tree.nodes;l=m.node_tree.links;tex=next(x for x in n if x.type=='TEX_IMAGE')
    uv=n.new('ShaderNodeUVMap');uv.uv_map='StructureUV';l.new(uv.outputs[0],tex.inputs['Vector'])
    nm=n.new('ShaderNodeNormalMap');nm.uv_map='StructureUV';l.new(tex.outputs['Color'],nm.inputs['Color'])
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');l.new(nm.outputs[0],bs.inputs['Normal'])
game.data.uv_layers.new(name='CoatingUV')
game.data.uv_layers.active_index=0;game.data.uv_layers[0].active_render=True
select([game]);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TacticalSuppressor_GameBase.blend'))

def add_collar(family,diameter):
    # Cosmetic mount reproduces the game's existing interface. No thread internals.
    rear=-.0124 if family=='M1911' else -.004
    inner=.0065 if family=='M1911' else .009
    neck=.0107 if family=='M1911' else min(.0155,diameter*.45)
    outer=diameter*.5
    profile=[(rear,neck),(rear+.001,neck),(-.0015,neck),(.0005,outer),(.002,outer),(.002,inner),(rear,inner)]
    count=96
    vertices=[(r*math.cos(i*2*math.pi/count),y,r*math.sin(i*2*math.pi/count)) for y,r in profile for i in range(count)]
    faces=[(j*count+i,j*count+(i+1)%count,((j+1)%len(profile))*count+(i+1)%count,((j+1)%len(profile))*count+i) for j in range(len(profile)) for i in range(count)]
    me=bpy.data.meshes.new('MountInterface');me.from_pydata(vertices,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new('TacticalMount_'+family,me);s.collection.objects.link(ob);me.materials.append(mount)
    for uvname in ['StructureUV','CoatingUV']:me.uv_layers.new(name=uvname)
    for p in me.polygons:
        p.use_smooth=True
        for li in p.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv=(math.atan2(co.z,co.x)/(2*math.pi)+.5,(co.y-rear)/.03)
            me.uv_layers[0].data[li].uv=uv;me.uv_layers[1].data[li].uv=uv
    return ob

report={}
for family in ['M4','AKM','QBZ191','M1911']:
    ob=game.copy();ob.data=game.data.copy();ob.name='SM_TacticalSuppressor_'+family;s.collection.objects.link(ob)
    ob.hide_render=False;ob.hide_set(False)
    length=.1302 if family=='M1911' else .186
    scale=length/(front_x-mount_x)
    # Original long +X becomes author +Y. Mount plane is author Y=0.
    transform=Matrix(((0,-scale,0,0),(scale,0,0,-mount_x*scale),(0,0,scale,0),(0,0,0,1)))
    ob.data.transform(transform)
    diameter=max(v.co.x for v in ob.data.vertices)-min(v.co.x for v in ob.data.vertices)
    collar=add_collar(family,diameter*.89)
    select([ob,collar],ob);bpy.ops.object.join()
    # UV1 is an independent physical coating channel; UV0 holds baked geometry.
    tile=(.1,.1) if family in ['QBZ191','M1911'] else (.12,.025 if family=='AKM' else .05)
    uv=ob.data.uv_layers[1]
    for p in ob.data.polygons:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=[i for i in range(3) if i!=axis]
        for li in p.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/tile[0]+.5,co[axes[1]]/tile[1]+.5)
    frame=Matrix.Identity(4)
    if family=='AKM':frame=Matrix.Translation((.0008,-.577,.0508883))@Matrix.Rotation(math.pi,4,'Z')
    if family=='QBZ191':frame=Matrix.Translation((.000759,-.500835,.060775))@Matrix.Rotation(math.pi,4,'Z')
    ob.data.transform(frame)
    folder=OUT/family;folder.mkdir(exist_ok=True)
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    select([ob]);fbx=folder/'SM_TacticalSuppressor.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    ob.data.calc_loop_triangles()
    report[family]={'fbx':str(fbx),'object':ob.name,'triangles':len(ob.data.loop_triangles),'length_m':length,'mount_surface_source_x':mount_x,'normal_uv':0,'coating_uv':1,'coating_tile_m':tile,'author_frame':[list(row) for row in frame],'materials':[m.name for m in ob.data.materials]}
    ob.hide_render=True;ob.hide_set(True)
game.hide_render=True;game.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TacticalSuppressor_FourWeapons_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TACTICAL_SUPPRESSOR_FOUR_WEAPONS_EXPORTED',json.dumps(report),flush=True)
