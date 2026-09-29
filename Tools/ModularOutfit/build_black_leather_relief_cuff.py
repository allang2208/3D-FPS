"""Blender high-poly leather tailoring, production bake and native author source."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import black_leather_relief_cuff as lib
import build_tailored_fingerless_candidate as leather
import glove_icon_display as display
from render_steel_gauntlet_icon import production_color, measure

P,R = lib.P,lib.R
SCAN = P/'SourceAssets/HandEquipmentAppearance/Source'


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj


def attribute(mesh,name,values,kind='FLOAT_VECTOR'):
    attr=mesh.attributes.new(name,kind,'POINT')
    attr.data.foreach_set('color' if kind=='FLOAT_COLOR' else 'vector',np.asarray(values,dtype=np.float32).ravel())


def pattern_images():
    size=2048
    x,y=np.meshgrid((np.arange(size)+.5)/size*16-8,(np.arange(size)+.5)/size*26-5)
    f=lib.back_pattern(x,y)
    palm=lib.palm_pattern(x,y)
    images=[]
    for name,fields in [('TailoredPatternA',[f['fine']+.1,f['thread'],f['cloth'],f['crest']]),
                        ('TailoredPatternB',[f['panel'],f['wear'],f['cavity'],np.ones_like(x)]),
                        ('TailoredPalm',[palm['panel'],palm['thread'],palm['crease'],np.ones_like(x)])]:
        image=bpy.data.images.new(name,width=size,height=size,alpha=True,float_buffer=True)
        image.colorspace_settings.name='Non-Color'
        image.pixels.foreach_set(np.stack(fields,axis=-1).astype(np.float32).ravel())
        image.pack()
        images.append(image)
    return images


def authored_material():
    mat=bpy.data.materials.new('BlackLeather_CraftedHighPoly');mat.use_nodes=True
    nt=mat.node_tree;nt.nodes.clear();nodes,links=nt.nodes,nt.links
    def node(kind,**props):
        v=nodes.new(kind)
        for k,x in props.items():setattr(v,k,x)
        return v
    def put(n,k,v):
        if isinstance(v,(float,int,tuple,list)):n.inputs[k].default_value=v
        else:links.new(v,n.inputs[k])
    def op(kind,a,b=None):
        n=node('ShaderNodeMath',operation=kind);put(n,0,a)
        if b is not None:put(n,1,b)
        return n.outputs[0]
    def mix(a,b,f):
        n=node('ShaderNodeMixRGB',blend_type='MIX');put(n,0,f);put(n,1,a);put(n,2,b);return n.outputs[0]
    def split(v):
        n=node('ShaderNodeSeparateXYZ');put(n,0,v);return n.outputs
    def attr(name):return node('ShaderNodeAttribute',attribute_name=name)
    def gauss(value,center,width):
        q=op('DIVIDE',op('SUBTRACT',value,center),width)
        return op('EXPONENT',op('MULTIPLY',op('MULTIPLY',q,q),-1.))
    coords=attr('RestMetric').outputs['Vector']
    masks=attr('TailorMasks');channels=split(masks.outputs['Color'])
    backhand,backdigit,t=channels[0],channels[1],channels[2]
    digitfields=split(attr('FingerTailor').outputs['Vector'])
    finger_arc,finger_seam,digit_mass=digitfields[0],digitfields[1],digitfields[2]
    palmhand=op('MULTIPLY',op('SUBTRACT',1.,digit_mass),op('SUBTRACT',1.,attr('SurfaceBack').outputs['Fac']))
    uv=node('ShaderNodeUVMap',uv_map='TailoringCoordinates').outputs[0]
    design=[]
    for image in pattern_images():
        n=node('ShaderNodeTexImage',image=image,extension='EXTEND');put(n,'Vector',uv)
        design.append((split(n.outputs['Color']),n.outputs['Alpha']))
    first,crest=design[0];second,_=design[1]
    palm,_=design[2]
    dash=op('LESS_THAN',op('ABSOLUTE',op('SUBTRACT',op('FRACT',op('DIVIDE',finger_arc,.25)),.5)),.30)
    digit_stitch=op('MULTIPLY',op('MULTIPLY',op('ADD',gauss(finger_seam,-.10,.035),gauss(finger_seam,.09,.035)),dash),digit_mass)
    thread=op('MAXIMUM',op('MULTIPLY',first[1],backhand),op('MULTIPLY',palm[1],palmhand))
    thread=op('MAXIMUM',thread,digit_stitch)
    sidecloth=op('MULTIPLY',op('MULTIPLY',gauss(finger_seam,.4,.28),digit_mass),.65)
    fabric=op('MAXIMUM',op('MULTIPLY',first[2],backhand),sidecloth)
    crest=op('MULTIPLY',crest,backhand)
    wear=op('MULTIPLY',second[1],backhand)
    cavity=op('MULTIPLY',second[2],backhand)
    cavity=op('ADD',cavity,op('MULTIPLY',op('MULTIPLY',palm[2],palmhand),.20))
    scan={}
    for channel in ('BaseColor','Roughness','Bump'):
        image=leather.image(SCAN/('Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_'+channel+'.jpg'),
                             'sRGB' if channel=='BaseColor' else 'Non-Color')
        tex=node('ShaderNodeTexImage',image=image,projection='BOX',projection_blend=.25)
        put(tex,'Vector',coords)
        scan[channel]=tex.outputs['Color']
    gray=node('ShaderNodeRGBToBW');put(gray,0,scan['BaseColor'])
    tone=op('ADD',.014,op('MULTIPLY',gray.outputs[0],.048))
    base=node('ShaderNodeCombineColor',mode='RGB')
    for key,factor in [('Red',.88),('Green',.94),('Blue',1.0)]:put(base,key,op('MULTIPLY',tone,factor))
    color=mix(base.outputs[0],(.008,.010,.012,1),op('MULTIPLY',second[0],op('MULTIPLY',backhand,.25)))
    color=mix(color,(.017,.019,.022,1),fabric)
    color=mix(color,(.023,.024,.025,1),op('MULTIPLY',op('MULTIPLY',palm[0],palmhand),.7))
    color=mix(color,(.060,.057,.047,1),op('MULTIPLY',thread,.78))
    color=mix(color,(.155,.108,.048,1),crest)
    color=mix(color,(.030,.029,.027,1),op('MULTIPLY',wear,.22))
    color=mix(color,(.006,.007,.009,1),op('MULTIPLY',cavity,.35))
    rough=op('ADD',.39,op('MULTIPLY',scan['Roughness'],.31))
    rough=op('ADD',rough,op('MULTIPLY',fabric,.20))
    rough=op('ADD',rough,op('MULTIPLY',op('MULTIPLY',palm[0],palmhand),.09))
    rough=op('SUBTRACT',rough,op('MULTIPLY',wear,.075))
    rough=op('MAXIMUM',.32,op('MINIMUM',.86,rough))
    # Woven inserts have cross-direction fibres at sub-millimetre pitch.
    axes=split(coords)
    weave=op('MULTIPLY',op('SINE',op('MULTIPLY',axes[0],3600.)),op('SINE',op('MULTIPLY',axes[1],3900.)))
    micro=op('ADD',op('MULTIPLY',scan['Bump'],op('SUBTRACT',1.,op('MULTIPLY',fabric,.75))),
             op('MULTIPLY',op('MULTIPLY',weave,fabric),.16))
    bump=node('ShaderNodeBump');put(bump,'Height',micro);put(bump,'Distance',.00012);put(bump,'Strength',.65)
    # Registered physical micro-height for both the normal bake and POM.
    # The reference's rough nap comes from broken grain plus short fibres,
    # with stronger pile only on textile inserts, thread and the cuff binding.
    noise=node('ShaderNodeTexNoise');put(noise,'Vector',coords);put(noise,'Scale',580.)
    put(noise,'Detail',3.);put(noise,'Roughness',.72)
    fine_noise=node('ShaderNodeTexNoise');put(fine_noise,'Vector',coords);put(fine_noise,'Scale',1850.)
    put(fine_noise,'Detail',2.)
    fiber_phase=op('ADD',op('MULTIPLY',axes[0],9400.),op('MULTIPLY',noise.outputs['Fac'],9.))
    fibers=op('MULTIPLY',op('POWER',op('ABSOLUTE',op('SINE',fiber_phase)),7.),fine_noise.outputs['Fac'])
    cuff=op('SUBTRACT',1.,masks.outputs['Alpha'])
    fuzzy=op('MAXIMUM',fabric,op('MAXIMUM',op('MULTIPLY',thread,.72),op('MULTIPLY',cuff,.75)))
    grain_cm=op('ADD',op('MULTIPLY',op('SUBTRACT',noise.outputs['Fac'],.5),.035),
                op('MULTIPLY',op('SUBTRACT',fibers,.18),op('ADD',.009,op('MULTIPLY',fuzzy,.017))))
    grain_bump=node('ShaderNodeBump');put(grain_bump,'Height',grain_cm)
    put(grain_bump,'Distance',.01);put(grain_bump,'Strength',.85);put(grain_bump,'Normal',bump.outputs[0])
    rough=op('MINIMUM',.94,op('ADD',rough,op('ADD',.045,op('MULTIPLY',fuzzy,.055))))
    color=mix(color,(.043,.045,.047,1),op('MULTIPLY',op('MULTIPLY',fibers,.17),op('ADD',.35,fuzzy)))
    authored_height=op('MULTIPLY',op('SUBTRACT',first[0],.1),backhand)
    authored_height=op('ADD',authored_height,op('MULTIPLY',digit_stitch,.01))
    authored_height=op('ADD',authored_height,op('MULTIPLY',op('MULTIPLY',palm[2],palmhand),-.02))
    height=op('ADD',.5,op('DIVIDE',op('ADD',authored_height,grain_cm),.08))
    relief=node('ShaderNodeCombineColor',mode='RGB');relief.name='RegisteredRelief'
    put(relief,'Red',op('MINIMUM',1.,op('MAXIMUM',0.,height)))
    put(relief,'Green',op('ADD',.14,op('MULTIPLY',fuzzy,.68)))
    put(relief,'Blue',1.)
    bs=node('ShaderNodeBsdfPrincipled');put(bs,'Base Color',color);put(bs,'Roughness',rough)
    put(bs,'Metallic',0.);put(bs,'Specular IOR Level',.30);put(bs,'Normal',grain_bump.outputs[0])
    put(bs,'Sheen Weight',op('MULTIPLY',fuzzy,.26));put(bs,'Sheen Roughness',.78)
    orm=node('ShaderNodeCombineColor',mode='RGB')
    put(orm,'Red',op('SUBTRACT',1.,op('MULTIPLY',cavity,.8)));put(orm,'Green',rough);put(orm,'Blue',0.)
    out=node('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs['Surface'])
    mat.use_fake_user=True
    return mat,color,orm.outputs[0],bs,out


def mesh_data(name,data,positions,mat):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in positions],[],data['triangles']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    for face in mesh.polygons:face.use_smooth=True
    return obj


def transported_normals(data,positions):
    faces=np.asarray(data['triangles']);old=np.asarray(data['positions'])
    def geo(p):
        corners=p[faces];cross=np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0])
        out=np.zeros_like(p)
        for k in range(3):np.add.at(out,faces[:,k],cross)
        # Duplicate seam vertices get the same deformation rotation.
        _,inverse=np.unique(np.round(old,5),axis=0,return_inverse=True)
        summed=np.zeros((inverse.max()+1,3));np.add.at(summed,inverse,out)
        return lib.unit(summed[inverse])
    a,b=geo(old),geo(positions)
    axis=np.cross(a,b)[faces];dot=(a*b).sum(1)[faces,None]
    ns=np.asarray(data['normals'])
    return lib.unit(ns+np.cross(axis,ns)+np.cross(axis,np.cross(axis,ns))/np.maximum(1+dot,1.e-8))


def create_low(name,source,master,anatomy,mat):
    points,normals,delta=lib.to_canonical(source,master)
    fields=lib.design_fields(points,normals,source['weights'],master['bones'],anatomy)
    offset=normals*fields['low'][:,None]
    positions=np.asarray(source['positions'])+np.einsum('nij,nj->ni',delta,offset)
    obj=mesh_data(name+'_BlackLeather_Game',source,positions,mat)
    ns=transported_normals(source,positions)
    obj.data.normals_split_custom_set([(v[0],-v[1],v[2]) for row in ns for v in row])
    attribute(obj.data,'RestMetric',points/25.)
    attribute(obj.data,'TailorLocal',np.c_[fields['design'],np.zeros(len(points))])
    attribute(obj.data,'TailorMasks',np.c_[fields['back']*fields['hand'],fields['back']*fields['digit'],
                                        fields['digit_t'],fields['cuff_fade']], 'FLOAT_COLOR')
    attribute(obj.data,'FingerTailor',np.c_[fields['finger_arc'],fields['finger_seam'],fields['digit']])
    scalar=obj.data.attributes.new('SurfaceBack','FLOAT','POINT')
    scalar.data.foreach_set('value',fields['back'].astype(np.float32))
    layer=obj.data.uv_layers.new(name='TailoringCoordinates')
    design=(fields['design']+[8,5])/[16,26]
    for face in obj.data.polygons:
        for loop in face.loop_indices:layer.data[loop].uv=design[obj.data.loops[loop].vertex_index]
    active(obj)
    layer=obj.data.uv_layers.new(name='BakedLeatherUV')
    obj.data.uv_layers.active=layer
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.25,island_margin=.008,area_weight=.25,correct_aspect=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    layer=obj.data.uv_layers['BakedLeatherUV'];layer.active_render=True
    final=dict(source,positions=positions.tolist(),normals=ns.tolist(),
        uv=[[(layer.data[i].uv.x,1-layer.data[i].uv.y) for i in f.loop_indices] for f in obj.data.polygons],
        canonical_positions=points.tolist(),canonical_normals=normals.tolist(),
        contract='Black leather reference tailoring; original native contact envelope and bones; back-side soft panels; shared existing animations')
    return obj,final


def create_high(low):
    high=low.copy();high.data=low.data.copy();high.name=low.name.replace('_Game','_HighPoly')
    bpy.context.collection.objects.link(high);active(high)
    mod=high.modifiers.new('DetailSculptSubdivision','SUBSURF');mod.subdivision_type='SIMPLE';mod.levels=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh=high.data;count=len(mesh.vertices)
    p=np.empty(count*3,dtype=np.float32);mesh.vertices.foreach_get('co',p);p=p.reshape(-1,3)
    n=np.empty(count*3,dtype=np.float32);mesh.vertices.foreach_get('normal',n);n=lib.unit(n.reshape(-1,3))
    local=np.empty(count*3,dtype=np.float32);mesh.attributes['TailorLocal'].data.foreach_get('vector',local);local=local.reshape(-1,3)
    masks=np.empty(count*4,dtype=np.float32);mesh.attributes['TailorMasks'].data.foreach_get('color',masks);masks=masks.reshape(-1,4)
    pattern=lib.back_pattern(local[:,0],local[:,1])
    palm=lib.palm_pattern(local[:,0],local[:,1])
    digit=np.empty(count*3,dtype=np.float32);mesh.attributes['FingerTailor'].data.foreach_get('vector',digit);digit=digit.reshape(-1,3)
    back=np.empty(count,dtype=np.float32);mesh.attributes['SurfaceBack'].data.foreach_get('value',back)
    fine=pattern['fine']*masks[:,0]*masks[:,3]
    fine+=masks[:,1]*(-.014*lib.gauss(masks[:,2],.08,.055)-.010*lib.gauss(masks[:,2],.84,.050))
    fine+=palm['fine']*(1-digit[:,2])*(1-back)*masks[:,3]
    dash=1-lib.smooth(.068,.095,np.abs(np.mod(digit[:,0],.25)-.125))
    stitches=(lib.gauss(digit[:,1],-.10,.035)+lib.gauss(digit[:,1],.09,.035))*dash
    fine+=digit[:,2]*(.010*stitches-.007*lib.gauss(digit[:,1],0,.05))
    # Tiny physical irregularity supplements the scanned leather micro-normal.
    micro=.003*np.sin(local[:,0]*61.+np.sin(local[:,1]*19.))*np.sin(local[:,1]*71.+np.cos(local[:,0]*17.))
    fine+=micro*np.clip(masks[:,0]+masks[:,1],0,1)*masks[:,3]
    p+=n*(fine*.01)[:,None]
    mesh.vertices.foreach_set('co',p.astype(np.float32).ravel());mesh.update()
    # Normals must follow the sculpted surface after displacement.
    mesh.normals_split_custom_set_from_vertices([tuple(v.normal) for v in mesh.vertices])
    high['Construction']='Actual subdivided soft panels, stitch relief, channels and wrist binding; scanned leather material'
    high['SculptVertices']=count
    print('BLACK_LEATHER_HIGH_POLY',high.name,count,len(mesh.polygons),flush=True)
    return high


def bake(name,low,high,mat,color,orm,bs,out,size):
    folder=R/'Textures'/name;folder.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.device='CPU'
    scene.render.bake.margin=16;scene.render.bake.use_clear=True
    maps={};nt=mat.node_tree
    for label,space in [('BaseColor','sRGB'),('ORM','Non-Color'),('Normal','Non-Color'),('Relief','Non-Color')]:
        image=bpy.data.images.new('T_BlackLeather_'+name+'_'+label,width=size,height=size,alpha=False)
        image.colorspace_settings.name=space
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.nodes.active=tex
        active(low)
        if label=='Normal':
            nt.links.new(bs.outputs[0],out.inputs['Surface'])
            high.hide_render=False;high.select_set(True)
            scene.render.bake.use_selected_to_active=True
            scene.render.bake.cage_extrusion=.0010;scene.render.bake.max_ray_distance=.0018
            kind='NORMAL'
        else:
            high.hide_render=True
            scene.render.bake.use_selected_to_active=False
            emission=nt.nodes.new('ShaderNodeEmission')
            output=color if label=='BaseColor' else nt.nodes['RegisteredRelief'].outputs[0] if label=='Relief' else orm
            nt.links.new(output,emission.inputs['Color'])
            nt.links.new(emission.outputs[0],out.inputs['Surface']);kind='EMIT'
        print('BLACK_LEATHER_BAKE_BEGIN',name,label,size,flush=True)
        bpy.ops.object.bake(type=kind,uv_layer='BakedLeatherUV',normal_space='TANGENT')
        image.filepath_raw=str(folder/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
        maps[label]=image
    nt.links.new(bs.outputs[0],out.inputs['Surface'])
    high.select_set(False);high.hide_render=True;high.hide_set(True)
    return maps


def baked_material(name,maps):
    mat=bpy.data.materials.new('BlackLeather_Detail_'+name);mat.use_nodes=True
    nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.38
    uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='BakedLeatherUV'
    for label,image in maps.items():
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.links.new(uv.outputs[0],tex.inputs['Vector'])
        if label=='BaseColor':nt.links.new(tex.outputs[0],bs.inputs['Base Color'])
        elif label=='ORM':
            split=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex.outputs[0],split.inputs[0])
            nt.links.new(split.outputs['Green'],bs.inputs['Roughness']);nt.links.new(split.outputs['Blue'],bs.inputs['Metallic'])
        elif label=='Normal':
            normal=nt.nodes.new('ShaderNodeNormalMap');normal.uv_map='BakedLeatherUV'
            nt.links.new(tex.outputs[0],normal.inputs['Color']);nt.links.new(normal.outputs[0],bs.inputs['Normal'])
        elif label=='Relief':
            separate=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex.outputs[0],separate.inputs[0])
            scale=nt.nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=.30
            nt.links.new(separate.outputs['Green'],scale.inputs[0]);nt.links.new(scale.outputs[0],bs.inputs['Sheen Weight'])
            bs.inputs['Sheen Roughness'].default_value=.78
    return mat


def author(name):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    master=lib.read(R/'Sources/M4.json');source=lib.read(R/'Sources'/(name+'.json'))
    anatomy=lib.read(lib.ANATOMY)['anatomy']
    mat,color,orm,bs,out=authored_material()
    low,data=create_low(name,source,master,anatomy,mat)
    high=create_high(low)
    maps=bake(name,low,high,mat,color,orm,bs,out,4096 if name=='M4' else 2048)
    low.data.materials.clear();low.data.materials.append(baked_material(name,maps))
    rig=leather.rig(low,data);rig.name=name+'_NativeBinding'
    # Keep the high-poly as a static sculpt/bake source. The game mesh is fully
    # bound to the supplied native skeleton, with the original skin weights.
    low['EquipmentDefinition']='ue_field_gloves_black'
    low['SourceAsset']=source['source']
    high['BakeOnly']=True
    active(low);bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(R/(name+'_BlackLeather_HighPoly.blend')))
    lib.write(R/'Baked'/(name+'.json'),data)
    lib.write(R/(name+'-production.json'),dict(profile=name,game_vertices=len(low.data.vertices),
        game_triangles=len(low.data.polygons),high_vertices=len(high.data.vertices),high_polygons=len(high.data.polygons),
        texture_size=4096 if name=='M4' else 2048,new_animations=0,runtime_tested=False))
    print('BLACK_LEATHER_MASTER_SAVED',name,flush=True)


def presentation():
    bpy.ops.wm.open_mainfile(filepath=str(R/'M4_BlackLeather_HighPoly.blend'))
    mat=bpy.data.materials['BlackLeather_Detail_M4']
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    data=lib.read(R/'Baked/M4.json');anatomy=lib.read(lib.ANATOMY)['anatomy']
    positions,selected=display.posed_surface(data,data['bones'],anatomy,'r')
    faces=np.asarray(data['triangles'])[selected];used=np.unique(faces);remap={int(v):i for i,v in enumerate(used)}
    rotation=np.asarray(Euler(np.radians((18,20,-4)),'XYZ').to_matrix())
    q=((positions[used]-[0,7.5,0])*.01)@rotation.T
    mesh=bpy.data.meshes.new('SM_BlackLeatherDetail_Pickup');mesh.from_pydata(q.tolist(),[],[[remap[int(v)] for v in f] for f in faces]);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(mat)
    layer=mesh.uv_layers.new(name='BakedLeatherUV')
    for face,fi in zip(mesh.polygons,selected):
        face.use_smooth=True
        for loop,(u,v) in zip(face.loop_indices,data['uv'][fi]):layer.data[loop].uv=(u,1-v)
    active(obj)
    # The worn mesh already has a rolled cuff and inner wall; no duplicate Solidify.
    bpy.ops.export_scene.fbx(filepath=str(R/'SM_BlackLeatherDetail_Pickup.fbx'),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
    scene=bpy.context.scene
    center=(q.min(0)+q.max(0))*.5;span=q.max(0)-q.min(0)
    camdata=bpy.data.cameras.new('BlackLeatherInventoryCamera');camdata.type='ORTHO';camdata.clip_start=.01
    camdata.ortho_scale=float(max(span[:2])/.91)
    cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam)
    cam.location=(center[0],center[1],q[:,2].max()+1.);cam.rotation_euler=(0.,0.,0.);scene.camera=cam
    target=Vector(center)
    for name,offset,power,size in [('Key',(-.4,-.12,.7),15.,.55),('Fill',(.4,.15,.6),7.,.65),('Rim',(.08,.48,.45),12.,.45)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
        lamp=bpy.data.objects.new(name,light);scene.collection.objects.link(lamp)
        lamp.location=target+Vector(offset);lamp.rotation_euler=(target-lamp.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('BlackLeatherNeutralStudio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.35,.35,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12;scene.world=world
    scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.render.resolution_x=scene.render.resolution_y=320;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.gamma=1.;scene.view_settings.exposure=0.
    icon=R/'ue_field_gloves_black.png';scene.render.filepath=str(icon)
    target_color=production_color(obj);luma=np.array([.2126,.7152,.0722])
    for attempt in range(3):
        bpy.ops.render.render(write_still=True);pixels=measure(icon)
        correction=math.log2(float(target_color@luma)/max(float(np.array(pixels['mean_linear'])@luma),1.e-6))
        if abs(correction)<.08 or attempt==2:break
        scene.view_settings.exposure+=float(np.clip(correction,-1,1))
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'BlackLeatherDetail_Presentation.blend'))
    lib.write(R/'artwork.json',dict(icon=str(icon),pickup=str(R/'SM_BlackLeatherDetail_Pickup.fbx'),
        groups=['M4','Body'],reference='codex-clipboard-f7b8f329-5e93-4fc8-b6f8-0b0bece9cb4c.png',
        source_leather=str(SCAN/'xjghdgl.json'),icon_measurements=pixels,runtime_tested=False))
    print('BLACK_LEATHER_ARTWORK_COMPLETE',flush=True)


if __name__=='__main__':
    R.mkdir(parents=True,exist_ok=True)
    if '--presentation-only' in sys.argv:presentation()
    else:
        names=['Body'] if '--body-only' in sys.argv else ['M4'] if '--m4-only' in sys.argv else ['M4','Body']
        for name in names:author(name)
        if '--m4-only' not in sys.argv:presentation()
