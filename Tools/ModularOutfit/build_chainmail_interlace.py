"""V2 chainmail production: separated four-neighbour rings, native cuffs and PBR.

Blender background authoring only. Rendering is limited to the delivered item icon.
No game, acceptance render, physics simulation or new animation is invoked.
"""
import json
import math
import sys
import shutil
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P/'Tools/ModularOutfit'))
import build_chainmail_relief as previous

R = P/'SourceAssets/ChainmailInterlace20260929'
T = R/'Textures'
OLD = P/'SourceAssets/ChainmailShirt20260928'
ITEM = 'ue_chainmail_shirt'
SIZE = 2048
NX = NY = 8
PITCH_X, PITCH_Y = .0060, .00220
TILE = (NX*PITCH_X, NY*PITCH_Y)
HEIGHT = .0056
REPEAT = (.25/TILE[0], .25/TILE[1])
write, active = previous.write, previous.active


def surface_material(metal, variant=0):
    """Colour is unlit intrinsic colour; polish/contact variation lives in ORM."""
    mat = bpy.data.materials.new(('ForgedRing_' if metal else 'Underlay_')+str(variant))
    mat.use_nodes = True
    n,l = mat.node_tree.nodes,mat.node_tree.links
    bs,out = n.get('Principled BSDF'),n.get('Material Output')
    geom=n.new('ShaderNodeNewGeometry')
    local=n.new('ShaderNodeAttribute');local.attribute_name='RingLocal'
    def noise(scale):
        t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=scale
        t.inputs['Detail'].default_value=2.;l.new(local.outputs['Vector'] if metal else geom.outputs['Position'],t.inputs['Vector'])
        return t
    broad,grain=noise(430 if metal else 2000),noise(18000 if metal else 7000)
    ramp=n.new('ShaderNodeValToRGB')
    shade=1.+(variant-3.5)*.016
    for e,c in zip(ramp.color_ramp.elements,[(.30,.32,.34),(.36,.38,.40)] if metal else [(.013,.016,.019),(.029,.032,.035)]):
        e.color=(*[x*shade for x in c],1.)
    l.new(broad.outputs['Fac'],ramp.inputs[0])
    ao=n.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=.0012;ao.samples=16
    rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.30 if metal else .83
    rough.inputs['To Max'].default_value=.45 if metal else .95
    l.new(broad.outputs['Fac'],rough.inputs['Value'])
    cavity=n.new('ShaderNodeMath');cavity.operation='MULTIPLY_ADD'
    l.new(ao.outputs['AO'],cavity.inputs[0]);cavity.inputs[1].default_value=-.13 if metal else 0
    cavity.inputs[2].default_value=.13 if metal else 0
    total=n.new('ShaderNodeMath');total.operation='ADD'
    l.new(rough.outputs[0],total.inputs[0]);l.new(cavity.outputs[0],total.inputs[1])
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.000006 if metal else .00002
    bump.inputs['Strength'].default_value=.16 if metal else .25
    l.new(grain.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    bs.inputs['Metallic'].default_value=1 if metal else 0
    l.new(ramp.outputs[0],bs.inputs['Base Color']);l.new(total.outputs[0],bs.inputs['Roughness'])
    orm=n.new('ShaderNodeCombineXYZ');l.new(ao.outputs['AO'],orm.inputs['X']);l.new(total.outputs[0],orm.inputs['Y'])
    orm.inputs['Z'].default_value=1 if metal else 0
    xyz=n.new('ShaderNodeSeparateXYZ');l.new(geom.outputs['Position'],xyz.inputs[0])
    height=n.new('ShaderNodeMath');height.operation='DIVIDE';height.inputs[1].default_value=HEIGHT
    l.new(xyz.outputs['Z'],height.inputs[0])
    relief=n.new('ShaderNodeCombineXYZ');l.new(height.outputs[0],relief.inputs['X'])
    relief.inputs[1].default_value=1 if metal else 0;l.new(ao.outputs['AO'],relief.inputs[2])
    return mat,{'BaseColor':ramp.outputs[0],'ORM':orm.outputs[0],'Relief':relief.outputs[0]},bs,out


def ring_tile():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials=[surface_material(True,k) for k in range(8)]+[surface_material(False)]
    segments,sides=256,32
    uu,vv=np.meshgrid(np.arange(segments)*2*math.pi/segments,np.arange(sides)*2*math.pi/sides,indexing='ij')
    ids=np.arange(segments*sides).reshape(segments,sides)
    faces=np.stack((ids,np.roll(ids,-1,axis=0),np.roll(np.roll(ids,-1,axis=0),-1,axis=1),np.roll(ids,-1,axis=1)),axis=-1).reshape(-1,4)
    vertices,polygons,slots,local_coords=[],[],[],[]
    count=0
    # Same-row rings are separated. Alternating inclined rows overlap only their
    # two upper and two lower neighbours. Previous 4.9 mm pitch cut adjacent rings.
    for row in range(-2,NY+3):
        for col in range(-1,NX+2):
            rng=np.random.default_rng(7291+(row%NY)*131+(col%NX)*7919)
            phase=float(rng.uniform(0,2*math.pi))
            a=.00250*(1+rng.uniform(-.012,.012));b=.00280*(1+rng.uniform(-.012,.012))
            tube=.00034*(1+.028*np.sin(3*uu+phase)+.010*np.cos(9*uu+phase))
            # A small flattened closure, not a dark painted gash or a second ring.
            delta=np.arctan2(np.sin(uu-phase),np.cos(uu-phase))
            closure=np.exp(-(delta/.12)**2)
            tube*=1+.10*closure
            radial=tube*np.cos(vv)
            base=np.stack(((a+radial)*np.cos(uu),(b+radial)*np.sin(uu),
                           tube*(.91-.10*closure)*np.sin(vv)),axis=-1).reshape(-1,3)
            angle=math.radians((52+rng.uniform(-1.0,1.0))*(1 if row%2 else -1))
            c,s=math.cos(angle),math.sin(angle)
            rot=np.array([[1,0,0],[0,c,-s],[0,s,c]])
            center=np.array([(col+.5*(row%2))*PITCH_X+rng.uniform(-.000025,.000025),
                             row*PITCH_Y+rng.uniform(-.000020,.000020),.00280])
            vertices.append(base@rot.T+center);polygons.append(faces+count*len(base))
            local_coords.append(base)
            slots.extend([int(rng.integers(0,8))]*len(faces));count+=1
    vertices=np.concatenate(vertices);polygons=np.concatenate(polygons)
    mesh=bpy.data.meshes.new('FourNeighbourForgedRings_HIGH')
    mesh.from_pydata(vertices.tolist(),[],polygons.tolist());mesh.update()
    attribute=mesh.attributes.new('RingLocal','FLOAT_VECTOR','POINT')
    attribute.data.foreach_set('vector',np.concatenate(local_coords).astype(np.float32).ravel())
    high=bpy.data.objects.new('InterlacedRingTile_HIGH_BakeOnly',mesh);bpy.context.collection.objects.link(high)
    for mat,*_ in materials[:-1]:mesh.materials.append(mat)
    mesh.polygons.foreach_set('material_index',slots)
    mesh.polygons.foreach_set('use_smooth',[True]*len(polygons))
    high['BakeOnly']=True;high['Construction']='Separated same-row links; alternating inclined four-neighbour weave'
    bpy.ops.mesh.primitive_plane_add(size=2,location=(TILE[0]/2,TILE[1]/2,.00005))
    backing=bpy.context.object;backing.name='DarkLinenBacking_HIGH';backing.scale=(TILE[0],TILE[1],1)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);backing.data.materials.append(materials[-1][0])
    lowmesh=bpy.data.meshes.new('InterlaceTile_LOW')
    lowmesh.from_pydata([(0,0,0),(TILE[0],0,0),(TILE[0],TILE[1],0),(0,TILE[1],0)],[],[(0,1,2,3)])
    low=bpy.data.objects.new('InterlaceTile_BakeTarget',lowmesh);bpy.context.collection.objects.link(low)
    uv=lowmesh.uv_layers.new(name='TileUV')
    for li,p in zip(lowmesh.polygons[0].loop_indices,[(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=p
    lowmat=bpy.data.materials.new('BakeTarget');lowmat.use_nodes=True;lowmesh.materials.append(lowmat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
    scene.cycles.use_denoising=False;scene.render.bake.margin=0;scene.render.bake.use_selected_to_active=True
    scene.render.bake.cage_extrusion=HEIGHT+.0002;scene.render.bake.max_ray_distance=HEIGHT+.0008
    for channel in ['BaseColor','ORM','Normal','Relief']:
        im=bpy.data.images.new('T_ChainmailRelief_'+channel,width=SIZE,height=SIZE,alpha=False)
        im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        target=lowmat.node_tree.nodes.new('ShaderNodeTexImage');target.image=im;lowmat.node_tree.nodes.active=target
        for mat,outputs,bs,out in materials:
            if channel=='Normal':mat.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
            else:
                emission=mat.node_tree.nodes.new('ShaderNodeEmission')
                mat.node_tree.links.new(outputs[channel],emission.inputs['Color']);mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface'])
        active(low);high.select_set(True);backing.select_set(True)
        print('CHAINMAIL_INTERLACE_BAKE',channel,flush=True)
        bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT',normal_space='TANGENT')
        im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();im.pack()
    for mat,outputs,bs,out in materials:mat.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    high.hide_render=True;backing.hide_render=True;high.hide_set(True);backing.hide_set(True)
    lowmesh.materials.clear();lowmesh.materials.append(baked_material(repeat=(1,1)))
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Chainmail_InterlacedRings_HIGH.blend'))
    return dict(rings_with_margin=count,polygons=len(polygons),triangles=len(polygons)*2,
                tile_meters=TILE,ring_centerline_mm=[5.,5.6],wire_diameter_mm=.68,lean_degrees=52,
                same_row_pitch_mm=6.,row_pitch_mm=2.2,texture_size=SIZE,height_meters=HEIGHT,bake_only=True)


def baked_material(repeat=REPEAT):
    previous.R,previous.T,previous.TILE,previous.HEIGHT,previous.REPEAT=R,T,TILE,HEIGHT,repeat
    mat=previous.baked_material()
    # Keep tile-view and garment materials distinct in the tile author file.
    mat.name='ChainmailInterlace_Tile' if repeat==(1,1) else 'ChainmailInterlace_PBR'
    return mat


def plain_material(name,color,metallic,roughness):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metallic;bs.inputs['Roughness'].default_value=roughness
    return mat


def native_profiles():
    import chainmail_interlace_native as author
    import author_chainmail_shirt as legacy
    manifest=[]
    master,master_detail=author.author(json.loads((OLD/'Authored/M4.json').read_text(encoding='utf-8-sig')))
    for row in json.loads((OLD/'manifest.json').read_text(encoding='utf-8-sig')):
        data=json.loads(Path(row['authored']).read_text(encoding='utf-8-sig'))
        if data['profile']=='Body':data,detail=author.author(data)
        elif data['profile']=='M4':data,detail=master,master_detail
        else:data,detail=author.retarget(master,data)
        path=R/'Authored'/(data['profile']+'.json');write(path,data)
        manifest.append(dict(profile=data['profile'],authored=str(path),source=data['binding_source'],
                             triangles=len(data['triangles']),details=detail))
        # Save each native author source with identical runtime material sections.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        legacy.R=R;legacy.editable(data,baked_material())
        mesh=next(o.data for o in bpy.context.scene.objects if o.type=='MESH')
        mesh.materials.append(plain_material('CuffForgedSteel',(.32,.34,.36),1,.34))
        mesh.materials.append(plain_material('CuffDarkBinding',(.023,.019,.016),0,.78))
        mesh.polygons.foreach_set('material_index',data['triangle_materials'])
        bpy.ops.wm.save_as_mainfile(filepath=str(R/'Editable'/(data['profile']+'_ChainmailShirt.blend')))
        print('CHAINMAIL_NATIVE_AUTHORED',data['profile'],len(data['triangles']),flush=True)
    write(R/'manifest.json',manifest)
    return manifest


def high_sleeves():
    previous.R,previous.T,previous.TILE,previous.HEIGHT,previous.REPEAT=R,T,TILE,HEIGHT,REPEAT
    # Produce HIGH only from the mail section; cuff rings already have true geometry.
    bpy.ops.wm.open_mainfile(filepath=str(R/'Editable/M4_ChainmailShirt.blend'))
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES')
    bm.to_mesh(obj.data);bm.free()
    envelope=R/'HighBase/Editable/M4_ChainmailShirt.blend';envelope.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(envelope))
    previous.OLD=R/'HighBase'
    result=previous.sleeve_author()
    previous.OLD=OLD
    return result


def inventory():
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'ChainmailShirt_Presentation.blend'))
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':obj.data.materials.clear();obj.data.materials.append(baked_material())
    # A narrower side key gives a readable metal reflection while keeping the
    # accepted shirt silhouette, camera, transparent background and 320 px size.
    for lamp in bpy.context.scene.objects:
        if lamp.type!='LIGHT':continue
        if 'Key' in lamp.name:lamp.data.energy=65.;lamp.data.size=.75
        elif 'Fill' in lamp.name:lamp.data.energy=16.;lamp.data.size=1.5
        elif 'Rim' in lamp.name:lamp.data.energy=55.;lamp.data.size=.65
    scene=bpy.context.scene;scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.render.resolution_x=scene.render.resolution_y=320;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA';scene.view_settings.exposure=0
    scene.render.filepath=str(R/(ITEM+'.png'));bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'ChainmailShirt_Presentation.blend'))
    return dict(icon=scene.render.filepath,size=320,preview=False)


def main():
    T.mkdir(parents=True,exist_ok=True);(R/'Editable').mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    before=R/'before.json'
    if not before.exists():
        cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
        items=json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
        write(before,dict(recipe=cfg['items'][ITEM],item=items[ITEM]))
        shutil.copy2(P/'SourceAssets/ChainmailRelief20260929/UserReference.png',R/'UserReference.png')
    if '--presentation-only' in sys.argv:
        write(R/'icon.json',inventory());return
    if '--profiles-only' in sys.argv:
        production=json.loads((R/'production.json').read_text(encoding='utf-8-sig'))
        production['profiles']=native_profiles();write(R/'production.json',production);return
    if '--from-native' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(R/'Chainmail_InterlacedRings_HIGH.blend'))
        high=bpy.data.objects['InterlacedRingTile_HIGH_BakeOnly']
        tile=dict(rings_with_margin=(NX+3)*(NY+5),polygons=len(high.data.polygons),triangles=len(high.data.polygons)*2,
                  tile_meters=TILE,ring_centerline_mm=[5.,5.6],wire_diameter_mm=.68,lean_degrees=52,
                  same_row_pitch_mm=6.,row_pitch_mm=2.2,texture_size=SIZE,height_meters=HEIGHT,bake_only=True)
    else:tile=ring_tile()
    write(R/'tile.json',tile)
    profiles=native_profiles();high=high_sleeves();icon=inventory()
    write(R/'production.json',dict(tile=tile,profiles=profiles,sleeves_high=high,icon=icon,
                                  new_animations=0,cloth_physics=False,high_poly_runtime=False,runtime_tested=False))
    print('CHAINMAIL_INTERLACE_PRODUCTION_SAVED',flush=True)


if __name__=='__main__':main()
