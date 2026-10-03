"""Author a game-only drum from the supplied photograph and the existing G18 seat."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent/'G18Integration20260929'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/G18_single_Editable.blend'))
r=bpy.data.objects['SK_G18_Manny'];root=r.data.bones['WPN_root'].matrix_local.copy()
mag=bpy.data.objects['G18_G18_mag'];neck=mag.copy();neck.data=mag.data.copy()
bpy.context.collection.objects.link(neck);neck.parent=None;neck.modifiers.clear();neck.matrix_world=Matrix.Identity(4)
neck.data.transform(root.inverted());neck.vertex_groups.clear();neck.name='Retained_G18_Feed_Neck'
bm=bmesh.new();bm.from_mesh(neck.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
cut=-.0815
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=True)
rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<.00001 for v in e.verts)]
for step in range(8):
    res=bmesh.ops.extrude_edge_only(bm,edges=rim);vs=[v for v in res['geom'] if isinstance(v,bmesh.types.BMVert)]
    for v in vs:v.co+=Vector((0,.00265,-.0084))
    rim=[e for e in res['geom'] if isinstance(e,bmesh.types.BMEdge) and all(v in vs for v in e.verts)]
bmesh.ops.holes_fill(bm,edges=[e for e in rim if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free()
for ob in list(bpy.data.objects):
    if ob!=neck:bpy.data.objects.remove(ob,do_unlink=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
parts=[];cy=.063;cz=-.203

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');bs.name='Principled BSDF';out=n.new('ShaderNodeOutputMaterial');out.name='Material Output';l.new(bs.outputs[0],out.inputs['Surface'])
    bs=n.get('Principled BSDF');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=240;tex.inputs['Detail'].default_value=3
    coord=n.new('ShaderNodeTexCoord');l.new(coord.outputs['Generated'],tex.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*[c*.76 for c in color],1);ramp.color_ramp.elements[1].color=(*[c*1.20 for c in color],1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
    roughmap=n.new('ShaderNodeMapRange');roughmap.inputs['To Min'].default_value=rough-.075;roughmap.inputs['To Max'].default_value=rough+.08
    l.new(tex.outputs['Fac'],roughmap.inputs['Value']);l.new(roughmap.outputs['Result'],bs.inputs['Roughness']);bs.inputs['Metallic'].default_value=metal
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.20;bump.inputs['Distance'].default_value=.000065
    l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m
poly=material('Drum_Black_Moulded',(.016,.019,.022),.12,.42)
steel=material('Drum_Blackened_Steel',(.020,.023,.027),.88,.34)
rubber=material('Drum_Recessed_Seal',(.008,.009,.010),0,.68)

def finish(ob,mat,bevel=0):
    ob.data.materials.clear();ob.data.materials.append(mat);select(ob)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=ob.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:p.use_smooth=True
    mod=ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
    bpy.ops.object.modifier_apply(modifier=mod.name);parts.append(ob);return ob

def box(name,loc,size,mat=poly,bevel=.0008,rot=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.dimensions=size;ob.rotation_euler.x=rot
    return finish(ob,mat,bevel)

def disk(name,x,radius,depth,mat=poly,segments=128):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=(x,cy,cz),rotation=(0,math.pi/2,0))
    ob=bpy.context.object;ob.name=name;return finish(ob,mat,.00055)

def lathe(name,profile,mat=poly,closed=False):
    n=128;verts=[(x,cy+rad*math.cos(a*2*math.pi/n),cz+rad*math.sin(a*2*math.pi/n)) for x,rad in profile for a in range(n)]
    faces=[]
    for row in range(len(profile) if closed else len(profile)-1):
        for a in range(n):faces.append((row*n+a,row*n+(a+1)%n,((row+1)%len(profile))*n+(a+1)%n,((row+1)%len(profile))*n+a))
    if not closed:faces.extend([tuple(range(n-1,-1,-1)),tuple((len(profile)-1)*n+a for a in range(n))])
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    return finish(ob,mat)

lathe('Moulded_drum_shell',[(-.037,.052),(-.036,.059),(-.033,.062),(-.028,.063),(.025,.063),(.032,.060),(.035,.054)])
lathe('Front_cover_shoulder',[(-.040,.054),(-.040,.059),(-.038,.061),(-.035,.061),(-.034,.058),(-.036,.054)],steel,True)
disk('Recessed_three_spoke_cover',-.0398,.054,.0028)
lathe('Cover_seal',[(-.0412,.052),(-.0412,.053),(-.0399,.053),(-.0399,.052)],rubber,True)
disk('Centre_lock_boss',-.0424,.0105,.0030,steel,64)
for k in range(3):
    angle=math.pi/2+k*2*math.pi/3
    box('Front_radial_pressing_%d'%k,(-.0424,cy+math.cos(angle)*.027,cz+math.sin(angle)*.027),(.0036,.0056,.038),steel,.0011,angle-math.pi/2)
for k in range(8):
    a=k*2*math.pi/8+math.pi/8
    box('Rim_latch_%d'%k,(-.033,cy+math.cos(a)*.061,cz+math.sin(a)*.061),(.011,.010,.005),poly,.0007,a)
for k in range(6):
    a=k*2*math.pi/6
    box('Shell_stiffener_%d'%k,(.002,cy+math.cos(a)*.0629,cz+math.sin(a)*.0629),(.042,.006,.0031),poly,.0007,a)
lathe('Rear_split_line',[(.026,.0595),(.028,.0615),(.030,.0615),(.029,.0595)],rubber,True)
disk('Rear_service_cover',.035,.050,.0028)
disk('Rear_hub',.0378,.017,.0030,steel,64)
for k in range(4):
    a=k*math.pi/2+math.pi/4
    box('Rear_moulding_rib_%d'%k,(.0378,cy+math.cos(a)*.030,cz+math.sin(a)*.030),(.0035,.004,.032),poly,.0008,a-math.pi/2)
box('Feed_neck_bridge',(0,.049,-.141),(.037,.050,.028),steel,.002)
box('Feed_neck_socket',(0,.046,-.125),(.030,.040,.009),poly,.0013)
for side in (-1,1):
    for y in (.031,.065):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0026,depth=.0011,location=(side*.019,y,-.14),rotation=(0,math.pi/2,0))
        ob=bpy.context.object;ob.name='Bridge_fastener';finish(ob,steel,.00025)
        box('Fastener_slot',(side*.0198,y,-.14),(.0003,.0032,.00065),rubber,.0001)
    box('Magazine_catch_relief',(side*.0138,.034,-.102),(.0008,.016,.003),steel,.0003)
for i in range(6):box('Rear_grip_step_%d'%i,(.0376,cy,cz-.029+i*.004),(.0028,.020,.0015),poly,.0005)
# The hidden back is a restrained inferred service lid; no replica internals.
bpy.ops.object.text_add(location=(.0375,cy-.004,cz+.022),rotation=(math.pi/2,0,math.pi/2))
label=bpy.context.object;label.data.body='50';label.data.size=.007;label.data.extrude=.00018;label.data.bevel_depth=.00006
bpy.ops.object.convert(target='MESH');finish(bpy.context.object,poly)

select(parts[0])
for ob in parts:ob.select_set(True)
bpy.ops.object.join();body=bpy.context.object;body.name='Drum50_AuthoredBody'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
# Keep both authored parts in the source's unchanged native skeletal frame.
body.data.transform(root);neck.data.transform(root)
for ob in (neck,body):ob.matrix_world=Matrix.Identity(4)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.bake_type='COMBINED'
scene.render.bake.margin=12;scene.render.bake.use_clear=True
scene.render.bake.use_selected_to_active=False
for collection in bpy.data.collections:collection.hide_render=False;collection.hide_viewport=False
body.hide_render=False;body.hide_viewport=False
channels={}
for channel in ('BaseColor','ORM','Normal_DirectX'):
    image=bpy.data.images.new('T_G18_Drum50_'+channel,width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
    originals=[]
    for m in body.data.materials:
        n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');out=n.get('Material Output')
        t=n.new('ShaderNodeTexImage');t.image=image;n.active=t
        if channel!='Normal_DirectX':
            em=n.new('ShaderNodeEmission');originals.append((m,bs,out,em))
            if channel=='BaseColor':l.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
            else:
                pack=n.new('ShaderNodeCombineColor');ao=n.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=.003
                l.new(ao.outputs['AO'],pack.inputs['Red']);l.new(bs.inputs['Roughness'].links[0].from_socket,pack.inputs['Green']);pack.inputs['Blue'].default_value=bs.inputs['Metallic'].default_value
                l.new(pack.outputs[0],em.inputs['Color'])
            l.new(em.outputs[0],out.inputs['Surface'])
    select(body);neck.hide_render=True
    scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_g='NEG_Y'
    bpy.ops.object.bake(type='NORMAL' if channel=='Normal_DirectX' else 'EMIT')
    image.filepath_raw=str(O/'Textures'/('T_G18_Drum50_'+channel+'.png'));image.file_format='PNG';image.save();channels[channel]=image.filepath_raw
    for m,bs,out,em in originals:m.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
neck.hide_render=False
mat=bpy.data.materials.new('M_G18_Drum50_PBR');mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
for ch,path in channels.items():
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(path,check_existing=True)
    if ch=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
    elif ch=='ORM':
        sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs[0],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    else:
        sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs[0],sep.inputs[0]);invert=n.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1;l.new(sep.outputs['Green'],invert.inputs[1])
        comb=n.new('ShaderNodeCombineColor');l.new(sep.outputs['Red'],comb.inputs['Red']);l.new(invert.outputs[0],comb.inputs['Green']);l.new(sep.outputs['Blue'],comb.inputs['Blue'])
        normal=n.new('ShaderNodeNormalMap');l.new(comb.outputs[0],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
body.data.materials.clear();body.data.materials.append(mat)
for p in body.data.polygons:p.material_index=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'G18_Drum50_Editable.blend'))
exports=[]
for lod,ratio in enumerate((1,.50,.24)):
    low=body.copy();low.data=body.data.copy();bpy.context.collection.objects.link(low);select(low)
    if lod:
        dec=low.modifiers.new('Distance LOD','DECIMATE');dec.ratio=ratio;bpy.ops.object.modifier_apply(modifier=dec.name)
    feed=neck.copy();feed.data=neck.data.copy();bpy.context.collection.objects.link(feed);feed.select_set(True);bpy.ops.object.join()
    low.name='SM_G18_Drum50_LOD'+str(lod);select(low)
    file=O/'Exports'/(low.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
    low.data.calc_loop_triangles();exports.append({'lod':lod,'source':str(file),'triangles':len(low.data.loop_triangles),'materials':[m.name for m in low.data.materials]})
    bpy.data.objects.remove(low,do_unlink=True)
(O/'authoring.json').write_text(json.dumps({'weapon':'ue_g18','option':'g18_drum_50','capacity':50,'frame':'unchanged G18 native skeletal reference; inverse magazine bind at runtime','root': [list(row) for row in root], 'exports':exports,'textures':channels,'reference':'Reference/user_drum.png','battery_and_wires':False,'back_side':'inferred service cover','runtime_tested':False},indent=2))
# Production source image for the required attachment icon, not an acceptance render.
for ob in (body,neck):ob.data.transform(root.inverted())
pts=[ob.matrix_world@v.co for ob in (body,neck) for v in ob.data.vertices];target=Vector((0,.037,-.12))
bpy.ops.object.camera_add(location=target+Vector((-.63,-.25,.11)));cam=bpy.context.object;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.34;scene.camera=cam
for loc,power,size in [((-.4,-.3,.35),38,.32),((.20,.13,.05),30,.22),((-.12,.4,-.1),25,.20)]:
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
if not scene.world:scene.world=bpy.data.worlds.new('Drum studio')
scene.world.color=(.20,.20,.20);scene.render.engine='CYCLES';scene.cycles.samples=64
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(O/'Icons/drum50_source.png');bpy.ops.render.render(write_still=True)
print('G18_DRUM50_AUTHORED',flush=True)
