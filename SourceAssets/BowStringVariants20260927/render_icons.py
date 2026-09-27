"""Production icons only. Same anchors, axial pitch and fibre recipe as runtime."""
from pathlib import Path
import bpy,json,math,sys
from mathutils import Vector
P=Path(__file__).parent;ROOT=P.parents[1];OUT=P/'Icons';OUT.mkdir(exist_ok=True)
series=json.loads((P/'series.json').read_text(encoding='utf8'))
catalog=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8-sig'))
# Locate the host row without baking a stale copy of its string anchors.
def find_bow(value):
    if isinstance(value,dict):
        if 'nock_upper_cm' in value:return value
        for v in value.values():
            found=find_bow(v)
            if found:return found
    elif isinstance(value,list):
        for v in value:
            found=find_bow(v)
            if found:return found
    return None
bow=find_bow(catalog)
if bow is None:raise RuntimeError('Host string anchors missing')
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene

def finish(row):
    s=row['surface'];mat=bpy.data.materials.new(row['material']);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
    def mathnode(op,*values):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for i,v in enumerate(values):
            if isinstance(v,(float,int)):n.inputs[i].default_value=v
            else:links.new(v,n.inputs[i])
        return n.outputs[0]
    def blend(a,b,factor):
        n=nodes.new('ShaderNodeMixRGB');n.blend_type='MIX'
        for socket,value in [(n.inputs[0],factor),(n.inputs[1],a),(n.inputs[2],b)]:
            if isinstance(value,(tuple,list)):socket.default_value=(*value,1)
            elif isinstance(value,(float,int)):socket.default_value=value
            else:links.new(value,socket)
        return n.outputs[0]
    uv=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],sep.inputs[0])
    angle=mathnode('MULTIPLY',sep.outputs['X'],math.tau)
    axial=mathnode('MULTIPLY',sep.outputs['Y'],math.tau/s['PitchCM'])
    phase=mathnode('SUBTRACT',mathnode('MULTIPLY',angle,2),axial)
    opposite=mathnode('ADD',mathnode('MULTIPLY',angle,3),axial)
    ridge=mathnode('MULTIPLY_ADD',mathnode('COSINE',phase),.5,.5)
    cross=mathnode('MULTIPLY_ADD',mathnode('COSINE',opposite),.5,.5)
    pattern=mathnode('ADD',mathnode('MULTIPLY',ridge,1-s['Weave']*.5),mathnode('MULTIPLY',cross,s['Weave']*.5))
    micro=mathnode('COSINE',mathnode('SUBTRACT',mathnode('MULTIPLY',angle,18),mathnode('MULTIPLY',axial,7)))
    tracer=mathnode('MULTIPLY',mathnode('POWER',mathnode('MULTIPLY_ADD',mathnode('COSINE',mathnode('SUBTRACT',angle,axial)),.5,.5),16),.18*(1-s['Weave']))
    color=blend(s['Dark'],s['Light'],mathnode('MULTIPLY_ADD',pattern,.8,.2))
    color=blend(color,s['Tracer'],tracer)
    scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';links.new(color,scale.inputs[0])
    links.new(mathnode('MULTIPLY_ADD',micro,.055,1),scale.inputs['Scale']);links.new(scale.outputs[0],bsdf.inputs['Base Color'])
    rough=mathnode('SUBTRACT',mathnode('ADD',s['Roughness'],mathnode('MULTIPLY',mathnode('SUBTRACT',.5,pattern),.07)),mathnode('MULTIPLY',micro,.025))
    links.new(rough,bsdf.inputs['Roughness']);bsdf.inputs['Metallic'].default_value=0
    bsdf.inputs['Specular IOR Level'].default_value=.35
    return mat

def point(key):
    x,y,z=map(float,bow[key].split(','));return Vector((x,-y,z))*.01
objects=[]
for key in ['nock_upper_cm','nock_lower_cm']:
    a,b=point(key),point('draw_anchor_cm');direction=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=1,depth=1)
    obj=bpy.context.object;obj.name='DynamicString_'+key;obj.location=(a+b)*.5;obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=Vector((0,0,1)).rotation_difference(direction.normalized())
    obj.scale=(series['radius_cm']*.01,series['radius_cm']*.01,direction.length)
    # UV.y records actual axial centimetres (not a normalized 0..1 length).
    uv=obj.data.uv_layers.active
    for poly in obj.data.polygons:
        poly.use_smooth=True
        angles=[math.atan2(obj.data.vertices[obj.data.loops[i].vertex_index].co.y,
                           obj.data.vertices[obj.data.loops[i].vertex_index].co.x)/math.tau for i in poly.loop_indices]
        seam=max(angles)-min(angles)>.5
        for i,u in zip(poly.loop_indices,angles):
            v=obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv=(u+1 if seam and u<0 else u,v.z*direction.length*100)
    objects.append(obj)

data=bpy.data.cameras.new('StringIconCamera');data.type='ORTHO';data.clip_start=.001;data.clip_end=100
cam=bpy.data.objects.new('StringIconCamera',data);scene.collection.objects.link(cam);scene.camera=cam
cam.rotation_euler=Vector((0,-1,0)).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
pts=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
center=(lo+hi)*.5;cam.location=center+Vector((0,3,0));data.ortho_scale=max(hi.x-lo.x,hi.z-lo.z)/.84
for name,offset,power,size in [('Key',(-1,1.4,1.5),70,2),('Fill',(1,1.3,.2),38,1.5),('Edge',(0,-1,1.2),45,1)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=(1,1,1)
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=center+Vector(offset)
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('NeutralStudio');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.3,.3,.3,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.18
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='8';scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.use_sequencer=False;scene.view_settings.view_transform='AgX';scene.view_settings.look='None'
neutral_output(scene)
records=[]
for row in series['variants']:
    material=finish(row)
    for o in objects:o.data.materials.clear();o.data.materials.append(material)
    # Save editable true-width source, then apply icon-only grayscale/thickness.
    bpy.ops.wm.save_as_mainfile(filepath=str(P/(row['id']+'.blend')))
    apply_grayscale(objects)
    for o in objects:o.scale.x=o.scale.y=max(series['radius_cm']*.01,data.ortho_scale*1.2/64/2)
    icon='bow_dark_string_'+row['id'];scene.render.filepath=str(OUT/(icon+'.png'))
    bpy.ops.render.render(write_still=True)
    for o in objects:o.scale.x=o.scale.y=series['radius_cm']*.01
    records.append({'icon':icon,'source':'bows.json current dynamic anchors','runtime_radius_cm':series['radius_cm'],
                    'min_line_pixels_at_64':1.2,'ortho_scale_m':data.ortho_scale,'palette':'neutral-grayscale-20260927'})
    (P/'render-receipt.json').write_text(json.dumps({'icons':records,'gameplay_tested':False},indent=2),encoding='utf8')
    print('BOW_STRING_ICON_SAVED',icon,flush=True)
