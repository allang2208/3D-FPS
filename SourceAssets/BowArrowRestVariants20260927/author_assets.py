"""Make fitted arrow-rest variants, editable sources, FBX and grayscale icons."""
from pathlib import Path
import bpy,bmesh,json,math,sys,numpy as np
from mathutils import Vector,Matrix
P=Path(__file__).parent;ROOT=P.parents[1];S=P.parent
for folder in ['Export','Textures','Icons']:(P/folder).mkdir(exist_ok=True)
series=json.loads((P/'series.json').read_text(encoding='utf8'))
bow=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8-sig'))['bow_dark']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01

def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=[name]
    obj=dst.objects[0]
    if not obj:raise RuntimeError('Source object missing '+name)
    scene.collection.objects.link(obj);obj.data=obj.data.copy()
    transform=obj.matrix_world.copy();obj.parent=None;obj.data.transform(transform);obj.matrix_world=Matrix.Identity(4)
    obj.modifiers.clear();obj.hide_set(False);obj.hide_viewport=False
    for mat in obj.data.materials:
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:
                    image=node.image;absolute=bpy.path.abspath(image.filepath,library=image.library)
                    if not Path(absolute).exists():absolute=str((path.parent/image.filepath.removeprefix('//')).resolve())
                    image.filepath=absolute
    return obj

base=append(S/'BowModular20260926/Bow_ModularParts.blend','SM_Bow_ArrowRestWood')
for mat in base.data.materials:
    if mat and mat.name=='ArrowRestWood':mat.name='AuthorPlaceholder_ArrowRestWood'
body=append(S/'BowSurfaceRepair20260927/Bow_ElasticBodies_Outward.blend','SK_Bow_Flex_Original')
wood=body.data.materials[0].copy();wood.name='ArrowRestWood'
nodes=wood.node_tree.nodes;links=wood.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for link in list(bsdf.inputs['Metallic'].links):links.remove(link)
bsdf.inputs['Metallic'].default_value=0
rough=bsdf.inputs['Roughness']
if rough.is_linked:
    source=rough.links[0].from_socket;minimum=nodes.new('ShaderNodeMath');minimum.operation='MAXIMUM'
    minimum.inputs[1].default_value=.42;links.new(source,minimum.inputs[0]);links.new(minimum.outputs[0],rough)
for node in nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.55
bpy.data.objects.remove(body,do_unlink=True);base.data.materials.clear();base.data.materials.append(wood)
base.hide_render=True

def texture(name,values,color=False):
    values=np.asarray(values,dtype=np.float32)
    if values.ndim==2:values=np.repeat(values[:,:,None],3,axis=2)
    rgba=np.ones((512,512,4),np.float32);rgba[:,:,:3]=np.clip(values,0,1)
    image=bpy.data.images.new(name,width=512,height=512,alpha=True,float_buffer=False,is_data=not color)
    image.colorspace_settings.name='sRGB' if color else 'Non-Color'
    image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(P/'Textures'/(name+'.png'));image.file_format='PNG';image.save()
    return image

def finish(label):
    y,x=np.mgrid[0:512,0:512].astype(np.float32)/512
    if label=='Horn':
        broad=np.sin(math.tau*(y*11+.24*np.sin(x*math.tau*2)))
        fine=np.sin(math.tau*(y*93+.7*np.sin(x*math.tau*3)))
        height=broad*.25+fine*.045
        rgb=np.array([.20,.15,.10])*(1+broad[:,:,None]*.17+fine[:,:,None]*.045)
        roughness=.37+broad*.04+fine*.018
    else:
        pore=np.sin(x*math.tau*61+.5*np.sin(y*math.tau*9))*np.sin(y*math.tau*67)
        broad=np.sin(x*math.tau*4)*np.sin(y*math.tau*3)
        height=pore*.13+broad*.04
        rgb=np.array([.29,.17,.10])*(1+pore[:,:,None]*.08+broad[:,:,None]*.05)
        roughness=.79+pore*.05
    dy,dx=np.gradient(height);normal=np.stack((-dx*1.2,-dy*1.2,np.ones_like(dx)),axis=2)
    normal/=np.linalg.norm(normal,axis=2,keepdims=True);normal=normal*.5+.5
    maps={'BaseColor':texture('T_BowRest_'+label+'_BaseColor',rgb,True),
          'ORM':texture('T_BowRest_'+label+'_ORM',np.stack((np.ones_like(x),roughness,np.zeros_like(x)),axis=2)),
          'Normal':texture('T_BowRest_'+label+'_Normal',normal)}
    mat=bpy.data.materials.new('M_BowRest_'+label);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
    samples={}
    for key,image in maps.items():
        n=nodes.new('ShaderNodeTexImage');n.image=image;samples[key]=n
    links.new(samples['BaseColor'].outputs['Color'],shader.inputs['Base Color'])
    sep=nodes.new('ShaderNodeSeparateColor');links.new(samples['ORM'].outputs['Color'],sep.inputs[0])
    links.new(sep.outputs['Green'],shader.inputs['Roughness'])
    n=nodes.new('ShaderNodeNormalMap');links.new(samples['Normal'].outputs['Color'],n.inputs['Color']);links.new(n.outputs[0],shader.inputs['Normal'])
    shader.inputs['Metallic'].default_value=0;shader.inputs['Specular IOR Level'].default_value=.35
    return mat
horn=finish('Horn');leather=finish('Leather')

def ue(p):return Vector((p[0],-p[1],p[2]))
def part(obj,mat):
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.clear();obj.data.materials.append(mat)
    for poly in obj.data.polygons:poly.use_smooth=True
    obj.select_set(False);return obj
def cube(name,center,size,mat,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=ue(center));obj=bpy.context.object;obj.name=name;obj.scale=size
    part(obj,mat);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Rounded handcrafted edge','BEVEL');mod.width=bevel;mod.segments=4
    bpy.ops.object.modifier_apply(modifier=mod.name);obj.select_set(False);return obj
def capsule(name,a,b,r,mat):
    a,b=ue(a),ue(b);d=b-a;parts=[]
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=r,depth=d.length,location=(a+b)*.5)
    obj=bpy.context.object;obj.name=name;obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized());parts.append(part(obj,mat))
    for c in [a,b]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=r,location=c)
        parts.append(part(bpy.context.object,mat))
    return parts

assets=[];origin=Vector(tuple(map(float,bow['arrow_rest_cm'].split(','))))
for row in series['variants']:
    rest=bpy.data.objects.new(row['mesh'],base.data.copy());scene.collection.objects.link(rest);parts=[rest]
    x,y,z=origin
    if row['id']=='open_quick_rest':
        parts.append(cube('PolishedHornSlide',(x+.15,y,z-.35),(.95,.65,.10),horn,.045))
    else:
        for sign in [-1,1]:
            end=(x+.12,y+sign*.32,z-.30)
            parts+=capsule('WoodForkBranch',(x+.30,y,z-.57),end,.115,wood)
            parts+=capsule('WoodForkRail',(x-.33,end[1],end[2]),(x+.57,end[1],end[2]),.105,wood)
            parts+=capsule('LeatherForkContact',(x-.20,end[1],end[2]),(x+.44,end[1],end[2]),.12,leather)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=rest;bpy.ops.object.join();rest.name=row['mesh']
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # Preserve the original fitted wood UVs; unwrap only newly authored contact pieces.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
    original_count=len(base.data.polygons)
    for poly in rest.data.polygons:poly.select=poly.index>=original_count
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    bm=bmesh.new();bm.from_mesh(rest.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(rest.data);bm.free()
    mod=rest.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(rest.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
    assets.append(rest);rest.hide_render=True
bpy.data.objects.remove(base,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ArrowRestVariants.blend'))
info={'source_base':'SourceAssets/BowModular20260926/Bow_ModularParts.blend:SM_Bow_ArrowRestWood',
      'support_cm':list(origin),'assets':{o.name:{'triangles':len(o.data.polygons),'slots':[m.name for m in o.data.materials]} for o in assets},
      'gameplay_tested':False}
(P/'authoring.json').write_text(json.dumps(info,indent=2),encoding='utf8')

# Produce catalog PNGs from the exported part geometry, using the shared palette.
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
for obj in assets:obj.data.transform(Matrix.Scale(.01,4))
scene.unit_settings.scale_length=1
apply_grayscale(assets);neutral_output(scene)
data=bpy.data.cameras.new('RestIconCamera');data.type='ORTHO';data.clip_start=.001;data.clip_end=100
cam=bpy.data.objects.new('RestIconCamera',data);scene.collection.objects.link(cam);scene.camera=cam
direction=Vector((-.30,1,0)).normalized();cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
lights=[]
for name,offset,power,size in [('Key',(-1,1.4,1.5),70,2),('Fill',(1,1.3,.2),38,1.5),('Edge',(0,-1,1.2),45,1)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);lights.append((obj,Vector(offset)))
world=bpy.data.worlds.new('NeutralStudio');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.3,.3,.3,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.18
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='None';records=[]
for row,subject in zip(series['variants'],assets):
    for obj in assets:obj.hide_render=obj!=subject
    bpy.context.view_layer.update();rot=cam.matrix_world.to_3x3();axes=[rot@Vector(a) for a in [(1,0,0),(0,1,0),(0,0,1)]]
    pts=[subject.matrix_world@v.co for v in subject.data.vertices]
    lo=[min(p.dot(a) for p in pts) for a in axes];hi=[max(p.dot(a) for p in pts) for a in axes]
    center=sum((a*((l+h)*.5) for a,l,h in zip(axes,lo,hi)),Vector())
    cam.location=center+direction*3;data.ortho_scale=max(hi[0]-lo[0],hi[1]-lo[1])/.84
    for obj,offset in lights:obj.location=center+offset;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    icon='bow_dark_arrow_rest_'+row['id'];scene.render.filepath=str(P/'Icons'/(icon+'.png'));bpy.ops.render.render(write_still=True)
    records.append({'icon':icon,'mesh':subject.name,'palette':'neutral-grayscale-20260927'})
    (P/'render-receipt.json').write_text(json.dumps({'icons':records,'gameplay_tested':False},indent=2),encoding='utf8')
    print('BOW_REST_ICON_SAVED',icon,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ArrowRestIcons.blend'))
print('BOW_REST_AUTHORING_COMPLETE',flush=True)
