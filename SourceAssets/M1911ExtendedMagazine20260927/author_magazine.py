"""Extend the accepted 1911 magazine below its hand contact area.

Factory triangles/UVs above the lower cut, mouth, catch and follower are kept.
The original lower shell and floorplate translate together; the new wall band
uses its own baked steel atlas, avoiding stretched witness holes or old UVs.
This produces game art, without preview rendering or gameplay tests.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;E=O/'Exports';E.mkdir(exist_ok=True)
T=O/'Textures';T.mkdir(exist_ok=True)
SOURCE=O.parent/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'
CUT=-.084;LENGTH=.030
# Lower front/back surface slopes measured from the accepted author mesh.
DELTA=Vector((0,.22405*LENGTH,-LENGTH))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;rig=bpy.data.objects['SK_M1911_Manny']
rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
source_names=['M1911_MagazineShell','M1911_MagazineFloorplate','M1911_MagazineFollower']
factory_material=bpy.data.materials['M_M1911_Hero_Magazine']
source_material=bpy.data.materials['AUTH_M1911_MagazineSteel']

def activate(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def lerp(a,b,t):return [x.lerp(y,t) for x,y in zip(a,b)]
def clip(poly,above):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[0].z-CUT;db=b[0].z-CUT
        ia=da>=-1e-10 if above else da<=1e-10
        ib=db>=-1e-10 if above else db<=1e-10
        if ia:out.append(a)
        if ia!=ib:out.append(lerp(a,b,da/(da-db)))
    return out

def polygons(ob):
    me=ob.data;xf=root.inverted()@ob.matrix_world;nr=xf.to_3x3().inverted().transposed()
    return [[[xf@me.vertices[me.loops[li].vertex_index].co,
              (nr@me.corner_normals[li].vector).normalized(),me.uv_layers.active.data[li].uv.copy()]
             for li in f.loop_indices] for f in me.polygons]

def moved(poly):
    return [[p+DELTA,n.copy(),uv.copy()] for p,n,uv in poly]

factory=[];retained=[];wall=[]
for name in source_names:
    for poly in polygons(bpy.data.objects[name]):
        factory.append(poly)
        if name.endswith('Follower'):retained.append(poly)
        elif name.endswith('Floorplate'):retained.append(moved(poly))
        else:
            upper=clip(poly,True);lower=clip(poly,False)
            if len(upper)>=3:retained.append(upper)
            if len(lower)>=3:retained.append(moved(lower))
            # Extrude each actual cut edge, including the inner wall. Opposite
            # edge winding preserves the original shell's facing direction.
            if len(upper)>=3 and len(lower)>=3:
                for a,b in zip(upper,upper[1:]+upper[:1]):
                    if abs(a[0].z-CUT)<1e-8 and abs(b[0].z-CUT)<1e-8:
                        wall.append([b,a,*moved([a,b])])

def mesh(name,polys,material):
    vertices=[];lookup={};indices=[];corners=[]
    for poly in polys:
        ids=[]
        for p,n,uv in poly:
            key=tuple(round(x,8) for x in p)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(p)
            ids.append(lookup[key])
        if len(set(ids))!=len(ids):continue
        indices.append(ids);corners.append(poly)
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],indices);me.update()
    uv=me.uv_layers.new(name='HeroUV');normals=[]
    for face,poly in zip(me.polygons,corners):
        face.use_smooth=True
        for li,c in zip(face.loop_indices,poly):uv.data[li].uv=c[2];normals.append(c[1].normalized())
    me.normals_split_custom_set(normals);me.materials.append(material)
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
    return ob

factory=mesh('SM_M1911_factory_magazine',factory,factory_material)
body=mesh('M1911_RetainedFactorySurface',retained,factory_material)
band=mesh('M1911_NewLowerWall',wall,source_material.copy())
activate([band]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.012,correct_aspect=True)
bpy.ops.object.mode_set(mode='OBJECT')
for ob in scene.objects:
    if ob.type=='MESH':ob.hide_render=ob!=band
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12
scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_g='POS_Y'
material=band.data.materials[0];nodes=material.node_tree.nodes;links=material.node_tree.links
out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
textures={};images={}
for kind in ['BaseColor','ORM','Normal']:
    image=bpy.data.images.new('T_M1911_ExtMag_Wall_'+kind,width=1024,height=1024,alpha=False)
    image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
    image.generated_color=(.5,.5,1,1) if kind=='Normal' else (1,.33,.96,1)
    target=nodes.get('EXTMAG_BAKE') or nodes.new('ShaderNodeTexImage');target.name='EXTMAG_BAKE';target.image=image;nodes.active=target
    if kind=='Normal':links.new(bs.outputs[0],out.inputs['Surface'])
    else:
        em=nodes.get('EXTMAG_EMIT') or nodes.new('ShaderNodeEmission');em.name='EXTMAG_EMIT'
        src=nodes[material['base_node']].outputs[material['base_socket']] if kind=='BaseColor' else nodes[material['orm_node']].outputs[0]
        links.new(src,em.inputs[0]);links.new(em.outputs[0],out.inputs['Surface'])
    activate([band]);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT')
    image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save()
    textures[kind]=image.filepath_raw;images[kind]=image
    print('M1911_EXTMAG_BAKED '+kind,flush=True)

wall_material=bpy.data.materials.new('M_M1911_ExtMag_Wall');wall_material.use_nodes=True
nodes=wall_material.node_tree.nodes;links=wall_material.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for kind,im in images.items():
    tx=nodes.new('ShaderNodeTexImage');tx.image=im
    if kind=='BaseColor':links.new(tx.outputs[0],bs.inputs['Base Color'])
    elif kind=='Normal':
        nm=nodes.new('ShaderNodeNormalMap');nm.uv_map='HeroUV';links.new(tx.outputs[0],nm.inputs['Color']);links.new(nm.outputs[0],bs.inputs['Normal'])
    else:
        sep=nodes.new('ShaderNodeSeparateColor');links.new(tx.outputs[0],sep.inputs[0]);links.new(sep.outputs[1],bs.inputs['Roughness']);links.new(sep.outputs[2],bs.inputs['Metallic'])
band.data.materials.clear();band.data.materials.append(wall_material)
activate([body,band]);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
body.name='SM_M1911_ext_mag'
for part in [body,factory]:
    part.data.transform(root);part.matrix_world=Matrix.Identity(4)
    activate([part])
    tri=part.modifiers.new('Final triangles','TRIANGULATE');tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(E/(part.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
for ob in list(scene.objects):
    if ob not in [body,factory]:bpy.data.objects.remove(ob,do_unlink=True)
body.hide_render=False;factory.hide_render=True;factory.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_ExtendedMagazine_Editable.blend'))
record={'source':str(SOURCE),'parts':source_names,'root_matrix':[list(row) for row in root],
    'mesh':'/Game/Weapons/M1911/ExtendedMagazine20260927/SM_M1911_ext_mag',
    'cut_z_m':CUT,'lower_translation_m':list(DELTA),'textures':textures,
    'method':'Actual shell cut-edge extrusion, independent atlas on new band; original lower collar/floorplate moved rigidly',
    'preserved':'Original upper geometry/UVs/normals, feed/catch, follower, magazine bone frame, separate animated ammunition',
    'reload':'Existing ordinary/empty M1911 and dual-pistol tracks; lower extension only, no change to upper side grasp',
    'triangles':len(body.data.polygons),'materials':[m.name for m in body.data.materials],
    'manufacturer_reference':'https://cmproducts.com/power-mag-full-size-1911-10-round-45-acp-stainless-magazine.html',
    'provenance':'Derivative game art from the locally accepted M1911 source; no downloaded geometry, logo or texture',
    'game_tested':False}
(O/'authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')

# LODs are production meshes, authored offline without running the game.
for ob in list(scene.objects):
    if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
group=bpy.data.objects.new('SM_M1911_ext_mag',None);scene.collection.objects.link(group);group['fbx_type']='LodGroup'
body.name='SM_M1911_ext_mag_LOD0';body.parent=group;levels=[body]
for i,ratio in [(1,.5),(2,.2)]:
    part=body.copy();part.data=body.data.copy();part.name='SM_M1911_ext_mag_LOD'+str(i);scene.collection.objects.link(part)
    activate([part]);mod=part.modifiers.new('Distant detail reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);levels.append(part);part.hide_render=True
activate([group]+levels)
bpy.ops.export_scene.fbx(filepath=str(E/'SM_M1911_ext_mag.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
    axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,use_custom_props=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_ExtendedMagazine_LODs.blend'))
record['lods']=[len(x.data.polygons) for x in levels]
(O/'authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('M1911_EXTMAG_AUTHORED '+json.dumps(record),flush=True)
