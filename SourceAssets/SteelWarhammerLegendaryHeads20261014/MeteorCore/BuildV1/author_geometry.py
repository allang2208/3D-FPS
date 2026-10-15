"""Detailed paired legendary heads built against the retained factory connectors."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,noise
P=Path(__file__).resolve().parent;ROOT=P.parents[3];sys.path.insert(0,str(P))
from catalog import OPTION
for folder in ('Export','Textures'): (P/folder).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
factory=bpy.data.objects['SM_Warhammer_hammer_heads_factory'];source=factory.data.copy();source.update()
old_mat=source.materials[0]
with bpy.data.libraries.load(str(ROOT/'SourceAssets/CommonHammerHeads20261014/DesignBuildV2/CommonHammerHeads_DesignV2_Editable.blend'),link=False) as (src,dst):
    dst.materials=['M_CommonHammerHeadSteel']
steel=dst.materials[0]
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
parts=[];detail_counts={}

def pbr(name,prefix,emission=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF')
    uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap'
    samples={}
    for kind in ('BaseColor','Normal','ORM')+ (('Heat',) if emission else ()):
        im=bpy.data.images.load(str(P/'Textures'/(prefix+'_'+kind+'.png')),check_existing=True)
        im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';im.pack()
        node=n.new('ShaderNodeTexImage');node.image=im;l.new(uv.outputs[0],node.inputs['Vector']);samples[kind]=node
    l.new(samples['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
    sep=n.new('ShaderNodeSeparateColor');l.new(samples['ORM'].outputs['Color'],sep.inputs[0])
    l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    normal=n.new('ShaderNodeNormalMap');normal.uv_map='UVMap';l.new(samples['Normal'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
    if emission:
        heat=n.new('ShaderNodeSeparateColor');l.new(samples['Heat'].outputs['Color'],heat.inputs[0])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(1,.035,.001,1);ramp.color_ramp.elements[1].color=(1,.35,.025,1)
        l.new(heat.outputs['Red'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Emission Color'])
        power=n.new('ShaderNodeMath');power.operation='MULTIPLY';power.inputs[1].default_value=5.5;l.new(heat.outputs['Red'],power.inputs[0]);l.new(power.outputs[0],bs.inputs['Emission Strength'])
    return mat
bronze=pbr('M_MeteorBronze','T_MeteorBronze')
rune_bronze=pbr('M_MeteorRuneBand','T_MeteorRuneBand')
lava=pbr('M_MeteorLavaCore','T_MeteorCore',True)
heat_image=next(n.image for n in lava.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.filepath.endswith('_Heat.png'))
heat_pixels=np.empty(len(heat_image.pixels),dtype=np.float32);heat_image.pixels.foreach_get(heat_pixels)
heat_pixels=heat_pixels.reshape(heat_image.size[1],heat_image.size[0],4)

def clip(poly,limit,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0].x-limit)*(1 if positive else -1);db=(b[0].x-limit)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out
source.calc_loop_triangles();old_normals=[n.vector.copy() for n in source.corner_normals]
verts=[];faces=[];corners=[]
for tri in source.loop_triangles:
    poly=[(source.vertices[source.loops[i].vertex_index].co.copy(),source.uv_layers[0].data[i].uv.copy(),old_normals[i]) for i in tri.loops]
    poly=clip(clip(poly,-.075,True),.075,False)
    for k in range(1,len(poly)-1):
        triangle=[poly[0],poly[k],poly[k+1]]
        if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
        faces.append(tuple(range(len(verts),len(verts)+3)))
        for point in triangle:verts.append(point[0]);corners.append(point)
mesh=bpy.data.meshes.new('Preserved factory head connectors');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(old_mat)
uv=mesh.uv_layers.new(name='UVMap');uv1=mesh.uv_layers.new(name='SteelUV');col=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for f in mesh.polygons:
    f.use_smooth=True
    for i in f.loop_indices:
        uv.data[i].uv=corners[mesh.loops[i].vertex_index][1];uv1.data[i].uv=uv.data[i].uv;col.data[i].color=(0,0,0,1)
mesh.normals_split_custom_set([tuple(corners[loop.vertex_index][2].normalized()) for loop in mesh.loops])
neck=bpy.data.objects.new('Factory necks - retained UV and split normals',mesh);bpy.context.scene.collection.objects.link(neck);parts.append(neck)

def uv_project(obj,mode='box',lo=0,hi=1,sign=1):
    data=obj.data
    u0=data.uv_layers.get('UVMap') or data.uv_layers.new(name='UVMap')
    u1=data.uv_layers.get('SteelUV') or data.uv_layers.new(name='SteelUV')
    color=data.color_attributes.get('Color') or data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for face in data.polygons:
        mapped=[]
        dominant=max(range(3),key=lambda a:abs(face.normal[a]))
        for i in face.loop_indices:
            v=obj.matrix_world@data.vertices[data.loops[i].vertex_index].co
            if mode=='band':
                a=(math.atan2(v.z,v.y)-math.pi/8)%math.tau
                point=((abs(v.x)-lo)/(hi-lo),a/math.tau)
            elif mode=='core':
                t=(v.x-sign*.153)/.048
                point=(math.atan2(v.z,v.y)/math.tau+.5,math.acos(max(-1,min(1,t)))/math.pi)
            else:
                axes=((1,2),(0,2),(0,1))[dominant];point=(v[axes[0]]/.12+.5,v[axes[1]]/.12+.5)
            mapped.append((i,point))
        if mode in ('core','band'):
            channel=0 if mode=='core' else 1
            values=[p[channel] for _,p in mapped]
            if max(values)-min(values)>.5:
                mapped=[(i,tuple(value+(1 if k==channel and value<.5 else 0) for k,value in enumerate(p))) for i,p in mapped]
        for i,point in mapped:u0.data[i].uv=point;u1.data[i].uv=point;color.data[i].color=(1,0,0,1)

def finish(obj,mat,bevel=0,smooth=False,mode='box',**uvargs):
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Machined edge radius','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in obj.data.polygons:f.use_smooth=smooth or bool(bevel)
    if bevel:
        mod=obj.modifiers.new('Weighted hard surface normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.materials.clear();obj.data.materials.append(mat);uv_project(obj,mode,**uvargs)
    parts.append(obj);obj.select_set(False);return obj

def make_mesh(name,verts,faces,mat,bevel=0,**kwargs):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    return finish(obj,mat,bevel,**kwargs)

def profile(name,sign,sections,mat,n=8,bevel=.0005,phase=math.pi/8,inner=0,**kwargs):
    points=[(sign*x,r*math.cos(phase+j*math.tau/n),r*math.sin(phase+j*math.tau/n)) for x,r in sections for j in range(n)]
    faces=[]
    for k in range(len(sections)-1):
        for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    if inner:
        base=len(points)
        for x in (sections[0][0],sections[-1][0]):
            points.extend((sign*x,inner*math.cos(phase+j*math.tau/n),inner*math.sin(phase+j*math.tau/n)) for j in range(n))
        last=(len(sections)-1)*n
        for j in range(n):
            k=(j+1)%n
            faces.extend(((j,k,base+k,base+j),(last+j,base+n+j,base+n+k,last+k),(base+j,base+k,base+n+k,base+n+j)))
    else:faces.extend((tuple(reversed(range(n))),tuple((len(sections)-1)*n+j for j in range(n))))
    return make_mesh(name,points,faces,mat,bevel,**kwargs)

def octrect(x0,x1,t0,t1,c):
    return [(x0+c,t0),(x1-c,t0),(x1,t0+c),(x1,t1-c),(x1-c,t1),(x0+c,t1),(x0,t1-c),(x0,t0+c)]

def window(name,sign,x0,x1,theta):
    outer=octrect(x0,x1,-.0271,.0271,.0025)
    inner=octrect(x0+.004,x1-.004,-.0222,.0222,.004)
    radial=Vector((0,math.cos(theta),math.sin(theta)));tangent=Vector((0,-math.sin(theta),math.cos(theta)))
    points=[]
    for r in (.0625,.0665):
        for ring in (outer,inner):
            for x,t in ring:points.append(Vector((sign*x,0,0))+radial*r+tangent*t)
    faces=[]
    for j in range(8):
        k=(j+1)%8
        faces.extend(((j,k,8+k,8+j),(16+j,24+j,24+k,16+k),(j,16+j,16+k,k),(8+j,8+k,24+k,24+j)))
    return make_mesh(name,points,faces,steel,.00065)

def rivet(name,sign,x,theta,r=.070,radius=.0022):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=(sign*x,r*math.cos(theta),r*math.sin(theta)))
    obj=bpy.context.object;obj.name=name;obj.scale=(radius,radius,radius*.55);obj.rotation_euler.x=theta-math.pi/2
    return finish(obj,bronze,smooth=True)

def beam(name,sign,x,theta,length):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(sign*x,.0701*math.cos(theta),.0701*math.sin(theta)))
    obj=bpy.context.object;obj.name=name;obj.scale=(length,.0065,.005);obj.rotation_euler.x=theta-math.pi/2
    return finish(obj,steel,.0008)

def star_ray(name,sign,theta,length):
    radial=Vector((0,math.cos(theta),math.sin(theta)));tangent=Vector((0,-math.sin(theta),math.cos(theta)))
    ring=[radial*.009-tangent*.0031,radial*length,radial*.009+tangent*.0031,radial*.005]
    points=[Vector((sign*.2264,0,0))+p for p in ring]
    points.append(Vector((sign*.228,0,0))+radial*(length*.40))
    faces=[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)]
    return make_mesh(name,points,faces,bronze,.00012)

for sign,label in ((-1,'Left'),(1,'Right')):
    # Original connectors end inside these closed structural collars.
    profile(label+' collar',sign,[(.0735,.035),(.077,.0365),(.083,.0365),(.086,.035)],steel,n=64,inner=.0255)
    profile(label+' collar bronze seam',sign,[(.078,.0371),(.080,.0371)],bronze,n=64,inner=.0345,bevel=.00025)
    profile(label+' forged shoulder',sign,[(.082,.033),(.088,.038),(.097,.058),(.103,.066)],steel,n=16,bevel=.001)
    profile(label+' rear octagonal retainer',sign,[(.098,.067),(.102,.070),(.108,.070)],steel,bevel=.001)
    profile(label+' front backing retainer',sign,[(.195,.070),(.202,.071)],steel,inner=.053,bevel=.0007)
    for j in range(8):
        theta=j*math.tau/8
        window(label+' rear cage window '+str(j),sign,.105,.145,theta)
        window(label+' front cage window '+str(j),sign,.158,.199,theta)
        corner=theta+math.pi/8
        beam(label+' continuous cage rib '+str(j),sign,.152,corner,.097)
        for x in (.111,.152,.193):rivet(label+' structural pin',sign,x,corner,r=.0742 if x==.152 else .0720)
    profile(label+' engraved bronze rune belt',sign,[(.1435,.0736),(.1595,.0736)],rune_bronze,inner=.0687,bevel=.0006,mode='band',lo=.1435,hi=.1595)
    for x in (.1435,.1595):
        profile(label+' bronze belt edging',sign,[(x-.001,.0745),(x+.001,.0745)],bronze,inner=.071,bevel=.0005)
    profile(label+' layered striking cap',sign,[(.198,.070),(.203,.077),(.218,.077),(.224,.071)],steel,bevel=.0012)
    profile(label+' recessed striking field',sign,[(.223,.064),(.2258,.064)],steel,bevel=.0006)
    profile(label+' face bronze inlay rim',sign,[(.2243,.0654),(.225,.0654)],bronze,inner=.0642,bevel=.00015)
    for j in range(8):
        star_ray(label+' raised celestial ray '+str(j),sign,j*math.tau/8,.050 if j%2==0 else .035)
    profile(label+' celestial central ring',sign,[(.2256,.0105),(.228,.0105)],bronze,n=48,inner=.0078,bevel=.0003)
    profile(label+' dark star centre',sign,[(.2258,.0076),(.227,.0076)],steel,n=32,bevel=.0003)
    # Dense opaque rough core sits behind the real through-windows; cap hides the poles.
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5,radius=1)
    obj=bpy.context.object;obj.name=label+' cooled meteor and molten fissures'
    for v in obj.data.vertices:
        unit=v.co.normalized();seed=unit*6.5+Vector((sign*7.31,13.7,2.11))
        uv=(math.atan2(unit.z,unit.y)/math.tau+.5,math.acos(max(-1,min(1,unit.x)))/math.pi)
        fissure=float(heat_pixels[min(heat_image.size[1]-1,int(uv[1]*heat_image.size[1])),int(uv[0]*heat_image.size[0])%heat_image.size[0],2])
        relief=.105*noise.noise_vector(seed*.65)[0]+.050*noise.noise_vector(seed*2.4)[1]+.017*noise.noise_vector(seed*7)[2]-.035*fissure
        relief=max(-.17,min(.075,relief))
        radius=.056*(max(0,1-abs(unit.x)**6)**(1/6))*(1+relief)
        angle=math.atan2(unit.z,unit.y)
        v.co=Vector((sign*.153+unit.x*.048,radius*math.cos(angle),radius*math.sin(angle)))
    finish(obj,lava,smooth=False,mode='core',sign=sign)

# Retain named editable parts. Export a joined copy so assembly uses one component.
bpy.ops.object.select_all(action='DESELECT');copies=[]
for obj in parts:
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.scene.collection.objects.link(copy);copy.select_set(True);copies.append(copy)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();module=bpy.context.object
module.name='SM_WarhammerHeads_MeteorCore_V1';module.data.name=module.name
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
tri=module.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(module.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
 bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
module.data.calc_loop_triangles()
materials=list(dict.fromkeys(m.name for m in module.data.materials))
detail_collection=bpy.data.collections.new('Editable component layers - hidden under joined runtime copy');bpy.context.scene.collection.children.link(detail_collection)
for obj in parts:
    for collection in list(obj.users_collection):collection.objects.unlink(obj)
    detail_collection.objects.link(obj);obj.location.z+=.925;obj.hide_render=True;obj.hide_set(True)
module.location.z=.925
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'MeteorCore_Detailed_Editable.blend'))
row={'id':OPTION['id'],'name':OPTION['name'],'mesh':module.name,'triangles':len(module.data.loop_triangles),'location_cm':[0,0,92.5000011920929],'materials':materials}
(P/'exports.json').write_text(json.dumps({'parts':[row],'source_interface':'warhammer_factory_v1','design_reference':'../ConceptV1/meteor-core-design.png',
 'editable_components':len(parts),'rune_count':48,'cage_window_count':32,'core_material':'M_MeteorLavaCore','revision':'MeteorCoreV1','tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('METEOR_CORE_MODEL_AUTHORED '+json.dumps(row),flush=True)
