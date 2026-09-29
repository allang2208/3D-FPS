"""Author interlaced steel rings, bake PBR/height, and save a sleeve high mesh.

Background production. The million-face objects are authoring sources only.
The existing shirt's runtime envelope, UVs, native weights and LODs stay intact.
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parents[2]
R = P/'SourceAssets/ChainmailRelief20260929'
OLD = P/'SourceAssets/ChainmailShirt20260928'
T = R/'Textures'
sys.path.insert(0, str(P/'Tools/ModularOutfit'))
ITEM = 'ue_chainmail_shirt'
SIZE = 2048
NX = NY = 8
PITCH_X, PITCH_Y = .0049, .0030
TILE = (NX*PITCH_X, NY*PITCH_Y)
HEIGHT = .0044
REPEAT = (.25/TILE[0], .25/TILE[1])


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def material_author(metal):
    mat = bpy.data.materials.new('ForgedGreyRings' if metal else 'DarkTextileUnderlay')
    mat.use_nodes = True
    n, l = mat.node_tree.nodes, mat.node_tree.links
    bs, out = n.get('Principled BSDF'), n.get('Material Output')
    geom = n.new('ShaderNodeNewGeometry')
    noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 11000 if metal else 3500
    noise.inputs['Detail'].default_value = 2
    l.new(geom.outputs['Position'], noise.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.24,.265,.29,1) if metal else (.008,.010,.013,1)
    ramp.color_ramp.elements[1].color = (.46,.48,.50,1) if metal else (.028,.032,.038,1)
    l.new(noise.outputs['Fac'], ramp.inputs[0])
    rough = n.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = .31 if metal else .83
    rough.inputs['To Max'].default_value = .52 if metal else .96
    l.new(noise.outputs['Fac'], rough.inputs['Value'])
    bs.inputs['Metallic'].default_value = 1 if metal else 0
    l.new(ramp.outputs[0], bs.inputs['Base Color'])
    l.new(rough.outputs[0], bs.inputs['Roughness'])
    bump = n.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = .000012 if metal else .000025
    bump.inputs['Strength'].default_value = .22 if metal else .3
    l.new(noise.outputs['Fac'], bump.inputs['Height'])
    l.new(bump.outputs[0], bs.inputs['Normal'])
    ao = n.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = .0018
    ao.samples = 8
    orm = n.new('ShaderNodeCombineXYZ')
    l.new(ao.outputs['AO'], orm.inputs['X'])
    l.new(rough.outputs[0], orm.inputs['Y'])
    orm.inputs['Z'].default_value = 1 if metal else 0
    xyz = n.new('ShaderNodeSeparateXYZ')
    l.new(geom.outputs['Position'], xyz.inputs[0])
    h = n.new('ShaderNodeMath'); h.operation = 'DIVIDE'
    l.new(xyz.outputs['Z'], h.inputs[0]); h.inputs[1].default_value = HEIGHT
    relief = n.new('ShaderNodeCombineXYZ')
    l.new(h.outputs[0], relief.inputs[0])
    relief.inputs[1].default_value = 1 if metal else 0
    l.new(ao.outputs['AO'], relief.inputs[2])
    return mat, {'BaseColor':ramp.outputs[0], 'ORM':orm.outputs[0], 'Relief':relief.outputs[0]}, bs, out


def ring_tile():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = [material_author(True), material_author(False)]
    segments, sides = 256, 32
    u = np.arange(segments)*2*math.pi/segments
    v = np.arange(sides)*2*math.pi/sides
    uu, vv = np.meshgrid(u, v, indexing='ij')
    # Elliptic forged rings, leaning in alternating staggered rows.
    # A periodic micro-undulation avoids perfectly machined torus highlights.
    radius = .00041*(1+.025*np.sin(3*uu)+.012*np.cos(7*uu+2*vv))
    base = np.stack(((.00250+radius*np.cos(vv))*np.cos(uu),
                     (.00280+radius*np.cos(vv))*np.sin(uu),
                     radius*np.sin(vv)),axis=-1).reshape(-1,3)
    ids = np.arange(segments*sides).reshape(segments,sides)
    faces = np.stack((ids, np.roll(ids,-1,axis=0),
                      np.roll(np.roll(ids,-1,axis=0),-1,axis=1),
                      np.roll(ids,-1,axis=1)),axis=-1).reshape(-1,4)
    vertices, polygons = [], []
    ring_count = 0
    for row in range(-1, NY+2):
        for col in range(-1, NX+2):
            angle = math.radians(35 if row%2 else -35)
            c,s = math.cos(angle),math.sin(angle)
            rot = np.array([[1,0,0],[0,c,-s],[0,s,c]])
            center = np.array([(col+.5*(row%2))*PITCH_X, row*PITCH_Y, .00208])
            coords = base@rot.T+center
            polygons.append(faces+ring_count*len(base)); vertices.append(coords)
            ring_count += 1
    vertices = np.concatenate(vertices); polygons = np.concatenate(polygons)
    mesh = bpy.data.meshes.new('InterlacedRings_HighGeometry')
    mesh.from_pydata(vertices.tolist(), [], polygons.tolist()); mesh.update()
    high = bpy.data.objects.new('Chainmail_RingTile_HIGH_BakeOnly',mesh)
    bpy.context.collection.objects.link(high); high.data.materials.append(mats[0][0])
    for p in mesh.polygons:p.use_smooth=True
    high['BakeOnly'] = True
    high['Design'] = 'Staggered alternate-lean forged rings; visual four-in-one reference; not a rigid-body simulation'
    bpy.ops.mesh.primitive_plane_add(size=2, location=(TILE[0]/2,TILE[1]/2,.00005))
    backing = bpy.context.object; backing.name='DarkUnderlay_HIGH'
    backing.scale=(TILE[0],TILE[1],1); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    backing.data.materials.append(mats[1][0])
    lowmesh=bpy.data.meshes.new('ProductionTile_LOW')
    lowmesh.from_pydata([(0,0,0),(TILE[0],0,0),(TILE[0],TILE[1],0),(0,TILE[1],0)],[],[(0,1,2,3)])
    low=bpy.data.objects.new('Chainmail_SeamlessBakeTarget',lowmesh);bpy.context.collection.objects.link(low)
    layer=lowmesh.uv_layers.new(name='TileUV')
    for loop,uv in zip(lowmesh.polygons[0].loop_indices,[(0,0),(1,0),(1,1),(0,1)]):layer.data[loop].uv=uv
    lowmat=bpy.data.materials.new('BakeTarget');lowmat.use_nodes=True;lowmesh.materials.append(lowmat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=8;scene.cycles.use_denoising=False
    scene.render.bake.margin=0;scene.render.bake.use_selected_to_active=True
    scene.render.bake.cage_extrusion=HEIGHT+.0002
    scene.render.bake.max_ray_distance=HEIGHT+.0008
    for channel in ['BaseColor','ORM','Normal','Relief']:
        image=bpy.data.images.new('T_ChainmailRelief_'+channel,width=SIZE,height=SIZE,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        target=lowmat.node_tree.nodes.new('ShaderNodeTexImage');target.image=image
        lowmat.node_tree.nodes.active=target
        for mat,outputs,bs,out in mats:
            if channel=='Normal':mat.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
            else:
                emit=mat.node_tree.nodes.new('ShaderNodeEmission')
                mat.node_tree.links.new(outputs[channel],emit.inputs['Color'])
                mat.node_tree.links.new(emit.outputs[0],out.inputs['Surface'])
        active(low);high.select_set(True);backing.select_set(True)
        print('CHAINMAIL_RELIEF_BAKE',channel,SIZE,flush=True)
        bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT', normal_space='TANGENT')
        image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
    for mat,outputs,bs,out in mats:mat.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    high.hide_render=True;backing.hide_render=True;high.hide_set(True);backing.hide_set(True)
    low.data.materials.clear();low.data.materials.append(baked_material())
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Chainmail_RingTile_HIGH.blend'))
    return dict(rings_in_authored_tile_with_margin=ring_count,ring_polygons=len(polygons),
                ring_vertices=len(vertices),tile_meters=TILE,ring_outer_mm=[5.82,6.42],
                wire_diameter_mm=.82,lean_degrees=35,texture_size=SIZE,height_meters=HEIGHT)


def baked_material():
    name='ChainmailRelief_ProductionPBR'
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    n,l=mat.node_tree.nodes,mat.node_tree.links;bs=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
    l.new(uv.outputs['UV'],scale.inputs[0]);scale.inputs[1].default_value=(*REPEAT,1)
    for channel in ['BaseColor','ORM','Normal','Relief']:
        image=bpy.data.images.load(str(T/('T_ChainmailRelief_'+channel+'.png')),check_existing=True)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.pack()
        tex=n.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';l.new(scale.outputs[0],tex.inputs['Vector'])
        if channel=='BaseColor':l.new(tex.outputs[0],bs.inputs['Base Color'])
        elif channel=='ORM':
            sep=n.new('ShaderNodeSeparateXYZ');l.new(tex.outputs[0],sep.inputs[0])
            l.new(sep.outputs[1],bs.inputs['Roughness']);l.new(sep.outputs[2],bs.inputs['Metallic'])
        elif channel=='Normal':
            nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
    mat['TileMeters']=list(TILE);mat['HeightMeters']=HEIGHT
    return mat


def sleeve_author():
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'Editable/M4_ChainmailShirt.blend'))
    mat=baked_material()
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    low=max(objects,key=lambda o:len(o.data.polygons))
    low.data.materials.clear();low.data.materials.append(mat)
    low['RuntimeGeometryUnchanged']=True
    # Split only UV boundaries for a well-defined displacement coordinate.
    low.data.calc_loop_triangles();lookup={};vertices=[];faces=[];uvs=[];bindings=[]
    layer=low.data.uv_layers.active
    for face in low.data.loop_triangles:
        row=[]
        for vi,li in zip(face.vertices,face.loops):
            uv=tuple(layer.data[li].uv);key=(vi,round(uv[0],7),round(uv[1],7))
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(tuple(low.data.vertices[vi].co));uvs.append(uv)
                bindings.append([(g.group,g.weight) for g in low.data.vertices[vi].groups])
            row.append(lookup[key])
        faces.append(row)
    mesh=bpy.data.meshes.new('Sleeves_HIGH_UVContinuous')
    mesh.from_pydata(vertices,[],faces);mesh.update()
    high=bpy.data.objects.new('M4_ChainmailSleeves_HIGH_BakeOnly',mesh)
    bpy.context.collection.objects.link(high);high.matrix_world=low.matrix_world.copy()
    for vg in low.vertex_groups:high.vertex_groups.new(name=vg.name)
    for vi,groups in enumerate(bindings):
        for group,weight in groups:high.vertex_groups[group].add([vi],weight,'REPLACE')
    uv=mesh.uv_layers.new(name='MailTileUV')
    for face in mesh.polygons:
        for li,vi in zip(face.loop_indices,face.vertices):
            uv.data[li].uv=(uvs[vi][0]*REPEAT[0],uvs[vi][1]*REPEAT[1])
    for face in mesh.polygons:face.use_smooth=True
    active(high)
    sub=high.modifiers.new('AuthorMicroSurface','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=3
    bpy.ops.object.modifier_apply(modifier=sub.name)
    # This author high surface physically follows the baked interlaced-ring height.
    tex=bpy.data.textures.new('MailBakedHeight',type='IMAGE')
    tex.image=bpy.data.images.load(str(T/'T_ChainmailRelief_Relief.png'),check_existing=True)
    tex.image.colorspace_settings.name='Non-Color'
    # Legacy displacement samples luminance, so use a dedicated R-channel image.
    pixels=np.empty(SIZE*SIZE*4,dtype=np.float32);tex.image.pixels.foreach_get(pixels)
    pixels=pixels.reshape(-1,4);pixels[:,1]=pixels[:,0];pixels[:,2]=pixels[:,0];pixels[:,3]=1
    height=bpy.data.images.new('ChainmailAuthorHeightR',width=SIZE,height=SIZE,alpha=False,float_buffer=True)
    height.colorspace_settings.name='Non-Color';height.pixels.foreach_set(pixels.ravel());height.pack();tex.image=height
    disp=high.modifiers.new('ActualRingReliefDisplacement','DISPLACE');disp.texture=tex
    disp.texture_coords='UV';disp.uv_layer='MailTileUV';disp.mid_level=0;disp.strength=HEIGHT
    bpy.ops.object.modifier_apply(modifier=disp.name)
    # Give the high object base metric UVs for the shared production shader.
    for entry in high.data.uv_layers['MailTileUV'].data:
        entry.uv=(entry.uv.x/REPEAT[0],entry.uv.y/REPEAT[1])
    high.data.materials.append(mat)
    for mod in low.modifiers:
        if mod.type=='ARMATURE':
            arm=high.modifiers.new('OriginalNativeRig','ARMATURE');arm.object=mod.object
    high['BakeOnly']=True;high['NoRuntimeExport']=True
    count=len(high.data.polygons)
    low.hide_render=True;low.hide_set(True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'M4_ChainmailSleeves_HIGH.blend'))
    print('CHAINMAIL_SLEEVE_HIGH_SAVED',count,flush=True)
    return dict(polygons=count,vertices=len(high.data.vertices),subdivision_levels=3,
                runtime_mesh_exported=False,source=str(OLD/'Editable/M4_ChainmailShirt.blend'))


def inventory():
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'ChainmailShirt_Presentation.blend'))
    mat=baked_material()
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            obj.data.materials.clear();obj.data.materials.append(mat)
            obj['Surface']='Interlaced ring geometry baked to new chainmail PBR'
    scene=bpy.context.scene;scene.cycles.samples=48
    scene.render.resolution_x=scene.render.resolution_y=320;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.exposure=0
    scene.render.filepath=str(R/(ITEM+'.png'))
    bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'ChainmailShirt_Presentation.blend'))
    return dict(icon=scene.render.filepath,size=320,preview=False)


def main():
    active_recipe=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['items'][ITEM]
    if active_recipe.get('appearance_family') in ('ChainmailInterlace20260929','ChainmailCloth20260929','ChainmailSharedSway20260929'):
        if '--presentation-only' in sys.argv:
            import build_chainmail_interlace as current
            current.write(current.R/'icon.json',current.inventory());return
        raise RuntimeError('Current chainmail uses build_chainmail_interlace.py; the first relief author is historical.')
    T.mkdir(parents=True,exist_ok=True);bpy.context.preferences.filepaths.save_version=0
    before=R/'before.json'
    if not before.exists():
        cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
        items=json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
        write(before,dict(recipe=cfg['items'][ITEM],item=items[ITEM]))
        shutil.copy2('C:/Users/allan/AppData/Local/Temp/codex-clipboard-6927b73f-b969-4dc3-a7d2-1f63a35cb6cb.png',R/'UserReference.png')
    if '--presentation-only' in sys.argv:
        write(R/'icon.json',inventory());return
    result=dict(tile=ring_tile(),sleeves=sleeve_author(),icon=inventory(),
                runtime_geometry_changed=False,new_animations=0,runtime_tested=False)
    write(R/'production.json',result)
    print('CHAINMAIL_RELIEF_PRODUCTION_COMPLETE',flush=True)


if __name__=='__main__':main()
