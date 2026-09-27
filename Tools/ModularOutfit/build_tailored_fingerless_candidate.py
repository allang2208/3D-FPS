"""Blender background authoring: one native candidate, shared baked PBR, icon.

The icon is a production deliverable. This script does not launch gameplay,
run animation acceptance, or publish the candidate over the equipped glove.
"""
import sys
import json
import math
from pathlib import Path
import numpy as np
import bpy
from mathutils import Matrix, Vector, Euler

P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import tailored_fingerless_candidate as author
import glove_icon_display as display
R=author.ROOT
T=R/'Textures';T.mkdir(exist_ok=True)
SCAN=P/'SourceAssets/HandEquipmentAppearance/Source'


def image(path,space='Non-Color'):
    im=bpy.data.images.load(str(path),check_existing=True);im.colorspace_settings.name=space
    return im


def design_image(palm):
    size=1536
    x,y=np.meshgrid((np.arange(size)+.5)/size*16-8,(np.arange(size)+.5)/size*18-5)
    relief,fine,thread,panel,polish=author.tailoring(x,y,palm)
    # Fine creasing supplements the sculpted medium folds; no whole-hand noise.
    fine+=.0025*np.sin(x*31+y*5)*np.sin(y*27-x*3)*np.exp(-((y-2)/4)**2)
    pixels=np.stack((fine*.01,thread,panel,polish),axis=-1).astype(np.float32)
    im=bpy.data.images.new('TailoringPalm' if palm else 'TailoringBack',width=size,height=size,alpha=True,float_buffer=True)
    im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(pixels.ravel())
    im.filepath_raw=str(T/(im.name+'.exr'));im.file_format='OPEN_EXR';im.save()
    return im


def authored_material():
    mat=bpy.data.materials.new('TailoredFingerless_Author');mat.use_nodes=True
    nt=mat.node_tree;nt.nodes.clear();ns=nt.nodes;links=nt.links
    def node(kind,**kw):
        n=ns.new(kind)
        for k,v in kw.items():setattr(n,k,v)
        return n
    def input(n,key,value):
        if isinstance(value,(float,int,tuple,list)):n.inputs[key].default_value=value
        else:links.new(value,n.inputs[key])
    def op(kind,a,b=None,c=None):
        n=node('ShaderNodeMath',operation=kind);input(n,0,a)
        if b is not None:input(n,1,b)
        if c is not None:input(n,2,c)
        return n.outputs[0]
    def mix(a,b,f):
        n=node('ShaderNodeMixRGB',blend_type='MIX');input(n,0,f);input(n,1,a);input(n,2,b)
        return n.outputs[0]
    def multiply(a,b):
        n=node('ShaderNodeMixRGB',blend_type='MULTIPLY');input(n,0,1.);input(n,1,a);input(n,2,b)
        return n.outputs[0]
    def uv(name):return node('ShaderNodeUVMap',uv_map=name).outputs[0]
    def split(v):
        n=node('ShaderNodeSeparateXYZ');input(n,0,v);return n.outputs
    def tex(im,v):
        n=node('ShaderNodeTexImage');n.image=im;input(n,'Vector',v);return n
    baseuv=uv('LeatherMetric25cm');fields=split(uv('PalmAndEdgeDistance'));details=split(uv('StitchArcAndLining'))
    palm=fields[0];edge=fields[1];inside=details[1]
    maps={}
    for suffix in ('BaseColor','Roughness','Normal','AO','Cavity'):
        maps[suffix]=tex(image(SCAN/f'Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_{suffix}.jpg','sRGB' if suffix=='BaseColor' else 'Non-Color'),baseuv).outputs[0]
    designuv=uv('TailoringCoordinates')
    back=tex(design_image(0.),designuv);front=tex(design_image(1.),designuv)
    design=mix(back.outputs['Color'],front.outputs['Color'],palm)
    channels=split(design)
    polish=op('ADD',op('MULTIPLY',back.outputs['Alpha'],op('SUBTRACT',1.,palm)),op('MULTIPLY',front.outputs['Alpha'],palm))
    # Edge binding and root stitching retain their existing geodesic fields.
    seam_dist=op('DIVIDE',op('SUBTRACT',edge,.28),.040)
    seam_band=op('EXPONENT',op('MULTIPLY',op('MULTIPLY',seam_dist,seam_dist),-1.))
    dash=op('LESS_THAN',op('ABSOLUTE',op('SUBTRACT',op('FRACT',op('DIVIDE',details[0],.30)),.5)),.29)
    thread=op('MINIMUM',1.,op('ADD',channels[1],op('MULTIPLY',seam_band,dash)))
    thread=op('MULTIPLY',thread,op('SUBTRACT',1.,inside))
    col=multiply(maps['BaseColor'],channels[2])
    col=multiply(col,op('MULTIPLY_ADD',maps['Cavity'],.12,.88))
    col=multiply(col,op('MULTIPLY_ADD',maps['AO'],.08,.92))
    col=multiply(col,op('MULTIPLY_ADD',inside,-.45,1.))
    col=mix(col,(.22,.132,.067,1),op('MULTIPLY',thread,.80))
    rough=op('MULTIPLY_ADD',maps['Roughness'],.30,.34)
    rough=op('ADD',rough,op('MULTIPLY',polish,-.10))
    rough=op('ADD',rough,op('MULTIPLY',inside,.19))
    rough=op('MAXIMUM',.32,op('MINIMUM',.82,rough))
    rough=op('ADD',rough,op('MULTIPLY',thread,.045))
    grain=node('ShaderNodeNormalMap',uv_map='LeatherMetric25cm');input(grain,'Color',maps['Normal'])
    input(grain,'Strength',op('MULTIPLY',op('MULTIPLY_ADD',palm,-.18,.58),op('MULTIPLY_ADD',inside,-.55,1.)))
    bump=node('ShaderNodeBump');input(bump,'Distance',1.);input(bump,'Strength',1.)
    fine=op('ADD',channels[0],op('MULTIPLY',op('MULTIPLY',seam_band,dash),.000065))
    input(bump,'Height',op('MULTIPLY',fine,op('SUBTRACT',1.,inside)));input(bump,'Normal',grain.outputs[0])
    bsdf=node('ShaderNodeBsdfPrincipled');input(bsdf,'Base Color',col);input(bsdf,'Roughness',rough)
    input(bsdf,'Normal',bump.outputs[0]);input(bsdf,'Specular IOR Level',.42)
    output=node('ShaderNodeOutputMaterial');links.new(bsdf.outputs[0],output.inputs['Surface'])
    return mat,col,rough,bsdf,output


def make_mesh(d,mat):
    mesh=bpy.data.meshes.new('M4_TailoredFingerless');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(mat)
    for key,name in [('uv','LeatherMetric25cm'),('uv1','PalmAndEdgeDistance'),('uv2','StitchArcAndLining'),('uv3','TailoringCoordinates')]:
        layer=mesh.uv_layers.new(name=name)
        for f,coords in zip(mesh.polygons,d[key]):
            for loop,(u,v) in zip(f.loop_indices,coords):layer.data[loop].uv=(u,1-v) if key=='uv' else (u,v)
    for f in mesh.polygons:f.use_smooth=True
    mesh.normals_split_custom_set([(n[0],-n[1],n[2]) for f in d['normals'] for n in f])
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    return obj


def bake(obj,mat,col,bsdf,output):
    mesh=obj.data
    layer=mesh.uv_layers.new(name='BakedTailoringUV');mesh.uv_layers.active=layer
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.25,island_margin=.008,area_weight=.25,correct_aspect=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Edit-mode UV operators replace the CustomData storage. Reacquire RNA.
    layer=mesh.uv_layers['BakedTailoringUV'];layer.active_render=True
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=False
    scene.render.bake.margin=12;scene.render.bake.use_selected_to_active=False
    outmaps={};nt=mat.node_tree
    for name,kind,space in [('BaseColor','EMIT','sRGB'),('Roughness','ROUGHNESS','Non-Color'),('Normal','NORMAL','Non-Color')]:
        im=bpy.data.images.new('T_TailoredFingerless_'+name,width=2048,height=2048,alpha=False)
        im.colorspace_settings.name=space
        target=nt.nodes.new('ShaderNodeTexImage');target.image=im;target.select=True;nt.nodes.active=target
        if kind=='EMIT':
            emission=nt.nodes.new('ShaderNodeEmission');nt.links.new(col,emission.inputs[0]);nt.links.new(emission.outputs[0],output.inputs[0])
        else:nt.links.new(bsdf.outputs[0],output.inputs[0])
        print('TAILORED_BAKE_BEGIN',name,flush=True)
        bpy.ops.object.bake(type=kind,uv_layer=layer.name,normal_space='TANGENT')
        im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();outmaps[name]=im
        target.select=False
    nt.links.new(bsdf.outputs[0],output.inputs[0])
    return layer,outmaps


def baked_material(maps):
    mat=bpy.data.materials.new('M_TailoredFingerless_Baked');mat.use_nodes=True
    nt=mat.node_tree;bsdf=nt.nodes.get('Principled BSDF');bsdf.inputs['Specular IOR Level'].default_value=.42
    uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='BakedTailoringUV'
    for name,socket in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=maps[name];nt.links.new(uv.outputs[0],tex.inputs['Vector'])
        if name=='Normal':
            nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='BakedTailoringUV';nm.inputs['Strength'].default_value=1.
            nt.links.new(tex.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],bsdf.inputs[socket])
        else:nt.links.new(tex.outputs[0],bsdf.inputs[socket])
    return mat


def rig(obj,d):
    arm=bpy.data.armatures.new('M4_NativeBinding');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
    obj.select_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    reflection=Matrix.Diagonal((1,-1,1));names={b['index']:n for n,b in d['bones'].items()}
    for n,b in d['bones'].items():
        bone=arm.edit_bones.new(n);axes=Matrix(b['axes']).transposed()
        for k in range(3):axes.col[k]=axes.col[k].normalized()
        transform=(reflection@axes@reflection).to_4x4();transform.translation=reflection@Vector(b['position'])*.01
        bone.matrix=transform;bone.length=.025
    for n,b in d['bones'].items():
        if b['parent'] in names:arm.edit_bones[n].parent=arm.edit_bones[names[b['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT');obj.parent=rig;mod=obj.modifiers.new('NativeBinding','ARMATURE');mod.object=rig
    for name in {n for w in d['weights'] for n in w}:obj.vertex_groups.new(name=name)
    for vi,w in enumerate(d['weights']):
        for n,value in w.items():obj.vertex_groups[n].add([vi],value,'REPLACE')
    return rig


def icon(d,material):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    anatomy=author.read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    pos,selected=display.posed_surface(d,d['bones'],anatomy,'r')
    faces=np.array(d['triangles'])[selected];used=np.unique(faces);remap={int(v):i for i,v in enumerate(used)}
    rotation=np.array(Euler(np.radians((25,28,-6)),'XYZ').to_matrix())
    q=((pos[used]-[0,7.5,0])*.01)@rotation.T
    mesh=bpy.data.meshes.new('SingleEmptyTailoredGlove');mesh.from_pydata(q.tolist(),[],[[remap[int(v)] for v in f] for f in faces]);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='BakedTailoringUV')
    for face,fi in zip(mesh.polygons,selected):
        face.use_smooth=True
        for loop,(u,v) in zip(face.loop_indices,d['uv'][fi]):layer.data[loop].uv=(u,1-v)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    world=bpy.data.worlds.new('TailoredStudio');world.use_nodes=True;world.node_tree.nodes.clear()
    bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld')
    bg.inputs[0].default_value=(.30,.34,.40,1);bg.inputs[1].default_value=.12
    world.node_tree.links.new(bg.outputs[0],out.inputs[0]);scene.world=world
    for name,loc,energy,size in [('Key',(-.45,.25,.55),18,.30),('Fill',(.45,-.05,.40),5,.40),('Rim',(.10,.4,.10),8,.20)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.size=size;light.shape='DISK'
        o=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    cam=bpy.data.cameras.new('IconCamera');cam.type='ORTHO';cam.clip_start=.01
    o=bpy.data.objects.new('IconCamera',cam);bpy.context.collection.objects.link(o)
    lo=q.min(0);hi=q.max(0);cam.ortho_scale=max(hi[0]-lo[0],hi[1]-lo[1])/.91
    o.location=((hi[0]+lo[0])/2,(hi[1]+lo[1])/2,.8);o.rotation_euler=(0,0,0);scene.camera=o
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.65
    scene.render.resolution_x=320;scene.render.resolution_y=320;scene.render.resolution_percentage=100;scene.render.film_transparent=True
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(R/'TailoredFingerless_Icon.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'TailoredFingerless_Icon.blend'))
    bpy.ops.render.render(write_still=True)
    print('TAILORED_ICON_SAVED',scene.render.filepath,flush=True)


def main():
    if '--icon-only' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(R/'M4_TailoredFingerless.blend'))
        icon(author.read(R/'M4_baked_fullshell.json'),bpy.data.materials['M_TailoredFingerless_Baked'])
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    d=author.read(R/'M4_fullshell.json');mat,col,rough,bsdf,output=authored_material();obj=make_mesh(d,mat)
    layer,maps=bake(obj,mat,col,bsdf,output)
    d['uv']=[[(layer.data[i].uv.x,1-layer.data[i].uv.y) for i in f.loop_indices] for f in obj.data.polygons]
    d.pop('uv3',None)
    (R/'M4_baked_fullshell.json').write_text(json.dumps(d,separators=(',',':')))
    outer=(np.array(d['uv2'])[:,:,1]==0).all(1);faces=np.array(d['triangles'])[outer];used=np.unique(faces);remap=np.full(len(d['positions']),-1,dtype=int);remap[used]=np.arange(len(used))
    worn=dict(d);worn.update(positions=np.array(d['positions'])[used].tolist(),weights=[d['weights'][i] for i in used],triangles=remap[faces].tolist(),triangle_materials=[0]*len(faces))
    for key in ('normals','uv','uv1','uv2'):worn[key]=np.array(d[key])[outer].tolist()
    (R/'M4_worn.json').write_text(json.dumps(worn,separators=(',',':')))
    final=baked_material(maps);obj.data.materials.clear();obj.data.materials.append(final)
    rig(obj,d);obj['CandidateOnly']=True;obj['AnimationContract']='Original M4 native bones and weights; no authored animation'
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'M4_TailoredFingerless.blend'))
    icon(d,final)
    (R/'production.json').write_text(json.dumps(dict(profile='M4',native_blend=str(R/'M4_TailoredFingerless.blend'),icon=str(R/'TailoredFingerless_Icon.png'),
        material='One shared baked BaseColor/Roughness/OpenGL Normal set for Blender and UE',normal_conversion='UE flips green on texture import',
        new_animations=0,active_equipment_changed=False,runtime_tested=False),indent=2)+'\n')
    print('TAILORED_PRODUCTION_FINISHED',flush=True)


if __name__=='__main__':main()
