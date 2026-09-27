"""Original single-element optics using the current V19 fitted seat and grain UVs.
Authoring coordinates are UE centimetres. Only final exports flip Y for Blender FBX.
Catalog icon rendering is production output; no gameplay or acceptance render.
"""
from pathlib import Path
import json, math, sys
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix
P=Path(__file__).parent
for folder in ['Export','Textures','Icons']: (P/folder).mkdir(exist_ok=True)
series=json.loads((P/'series.json').read_text(encoding='utf8'))
source=P.parent/'BowWoodBracket20260927/author_sight.py'
# Reuse the retained bow surface projection, fitted seat and UV construction.
# Stop before the old arm/ring: no old authoring outputs or assets are overwritten.
ns={'__file__':str(source),'__name__':'fitted_seat_source'}
exec(compile(source.read_text(encoding='utf8').split('rod_path = catmull',1)[0],str(source),'exec'),ns)
seat=ns['seat'];seat.hide_render=True;seat.hide_set(True)
mesh,sweep,catmull=ns['mesh'],ns['sweep'],ns['catmull']
materials=ns['materials'];pin=ns['PIN'];root=ns['root']
scene=bpy.context.scene

def image(name,pixels):
    h,w,_=pixels.shape;rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=pixels
    img=bpy.data.images.new(name,w,h,alpha=True);img.colorspace_settings.name='Non-Color'
    img.pixels.foreach_set(rgba.ravel());img.filepath_raw=str(P/'Textures'/(name+'.png'))
    img.file_format='PNG';img.save();return img
y,x=np.mgrid[0:512,0:512].astype(np.float32)/512
grain=np.sin(math.tau*(y*127+.12*np.sin(x*math.tau*3)))
height=grain*.006;dy,dx=np.gradient(height)
n=np.stack((-dx,-dy,np.ones_like(x)),axis=2);n/=np.linalg.norm(n,axis=2,keepdims=True)
normal=image('T_BowOptic_MetalNormal',n*.5+.5)
orm=image('T_BowOptic_MetalORM',np.stack((np.ones_like(x),.34+grain*.024,np.full_like(x,.94)),axis=2))

def material(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    materials.append(m);return len(materials)-1
steel=material('M_BowOptic_BlackSteel',(.055,.064,.073),.34,.94)
bronze=material('M_BowOptic_DarkBronze',(.23,.15,.071),.34,.94)
ink=material('M_BowOptic_Etching',(.009,.011,.013),.55)
for idx in [steel,bronze]:
    m=materials[idx];nodes=m.node_tree.nodes;links=m.node_tree.links;b=nodes.get('Principled BSDF')
    t=nodes.new('ShaderNodeTexImage');t.image=orm;s=nodes.new('ShaderNodeSeparateColor')
    links.new(t.outputs['Color'],s.inputs['Color']);links.new(s.outputs['Green'],b.inputs['Roughness'])
    t=nodes.new('ShaderNodeTexImage');t.image=normal;n=nodes.new('ShaderNodeNormalMap')
    links.new(t.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],b.inputs['Normal'])
glass={}
for power,color in [(2,(.80,.92,.95)),(4,(.88,.84,.96))]:
    idx=material('M_BowOptic_Glass'+str(power)+'x',color,.045)
    b=materials[idx].node_tree.nodes.get('Principled BSDF')
    b.inputs['Transmission Weight'].default_value=.98;b.inputs['IOR'].default_value=1.45
    glass[power]=idx

def lens(radius,power):
    # One continuous closed glass element, with two surfaces and an edge.
    verts=[];faces=[];rings=12;segments=96
    for side in [-1,1]:
        for j in range(rings+1):
            r=radius*j/rings
            depth=.05+(.065 if power==2 else .10)*(1-(r/radius)**2)
            for i in range(segments):
                a=math.tau*i/segments;verts.append((pin.x+side*depth,pin.y+r*math.cos(a),pin.z+r*math.sin(a)))
    count=(rings+1)*segments
    for side in [0,1]:
        offset=side*count
        for j in range(rings):
            for i in range(segments):
                a=offset+j*segments+i;b=offset+j*segments+(i+1)%segments
                faces.append((a,b,b+segments,a+segments))
    for i in range(segments):
        a=rings*segments+i;b=rings*segments+(i+1)%segments;faces.append((a,b,b+count,a+count))
    o=mesh('SingleGlassElement',verts,faces,[[(.5+(verts[v][1]-pin.y)/radius*.5,.5+(verts[v][2]-pin.z)/radius*.5) for v in f] for f in faces],glass[power])
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    return o

assets=[];details=[]
for row in series['variants']:
    power=row['magnification'];rad=row['outer_diameter_cm']*.5-.14
    base=bpy.data.objects.new(row['mesh'],seat.data.copy());scene.collection.objects.link(base)
    ns['parts']=[base]
    for i,path in enumerate(ns['collars']):sweep('RecessedLinenBinding'+str(i),path,lambda t:(.039,.039),mat=1,sides=8)
    angle=math.radians(-50)
    end=Vector((pin.x,pin.y+rad*math.cos(angle),pin.z+rad*math.sin(angle)))
    path=catmull([(-.65,root.y+.12,15.9),(-.85,root.y-.60,16.04),(-1.55,-4.6,16.33),
                  (-2.65,-6.3,16.28),(-3.50,-7.30,15.37),tuple(end)])
    sweep('CurvedForgedSideArm',path,lambda t:(.20+.16*(1-t)**3,.17+.18*(1-t)**3),mat=steel,sides=16)
    if power==4:
        rib=[p+Vector((-.17,0,0)) for p in path[7:-5]]
        sweep('ShallowArmReinforcement',rib,lambda t:(.045,.068*math.sin(math.pi*t)+.015),mat=steel,sides=10)
    sweep('ThinSteelLensRim',[(pin.x,pin.y+rad*math.cos(math.tau*i/128),pin.z+rad*math.sin(math.tau*i/128)) for i in range(128)],
          lambda t:(.17,.14),mat=steel,sides=12,closed=True)
    for side in [-1,1]:
        sweep('NarrowBronzeRetainingLip',[(pin.x+side*.125,pin.y+(rad-.095)*math.cos(math.tau*i/128),pin.z+(rad-.095)*math.sin(math.tau*i/128)) for i in range(128)],
              lambda t:(.023,.027),mat=bronze,sides=8,closed=True)
    clear=rad-.125;lens(clear,power)
    def reticle_line(a,b):
        pts=[]
        for i in range(25):
            yz=Vector(a).lerp(Vector(b),i/24);r=yz.length
            depth=.05+(.065 if power==2 else .10)*(1-(r/clear)**2)+.004
            pts.append((pin.x-depth,pin.y+yz.x,pin.z+yz.y))
        sweep('GlassEtchedReticle',pts,lambda t:(.0035,.0035),mat=ink,sides=6)
    for axis in [Vector((1,0)),Vector((0,1))]:
        reticle_line(axis*(-clear*.98),axis*(-clear*.012));reticle_line(axis*(clear*.012),axis*(clear*.98))
    if power==4:
        for ymark in [.12,.24]:reticle_line(Vector((-.032*clear,-ymark*clear)),Vector((.032*clear,-ymark*clear)))
    dotdepth=.05+(.065 if power==2 else .10)+.006
    sweep('TinyEtchedCentrePoint',[(pin.x-dotdepth,pin.y+.009*math.cos(math.tau*i/24),pin.z+.009*math.sin(math.tau*i/24)) for i in range(24)],
          lambda t:(.0045,.0045),mat=ink,sides=6,closed=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in ns['parts']:obj.select_set(True)
    bpy.context.view_layer.objects.active=base;bpy.ops.object.join();base.name=row['mesh']
    for v in base.data.vertices:v.co.y=-v.co.y
    bm=bmesh.new();bm.from_mesh(base.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(base.data);bm.free()
    mod=base.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(base.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',colors_type='LINEAR')
    assets.append(base);base.hide_render=True
    details.append({'mesh':base.name,'triangles':len(base.data.polygons),'slots':[m.name for m in base.data.materials],
                    'single_glass':True,'outer_diameter_cm':row['outer_diameter_cm'],'rim_axial_depth_cm':.34})
bpy.data.objects.remove(seat,do_unlink=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_SingleLensOptics.blend'))
(P/'authoring.json').write_text(json.dumps({'assets':details,'aim_center_cm':list(pin),
    'fitted_seat_source':str(source),'unit':'UE cm; export Y reflected','gameplay_tested':False},indent=2),encoding='utf8')

# Model-derived transparent monochrome catalog icons, retaining lens transmission.
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
for obj in assets:obj.data.transform(Matrix.Scale(.01,4))
scene.unit_settings.scale_length=1;apply_grayscale(assets);neutral_output(scene)
data=bpy.data.cameras.new('OpticIconCamera');data.type='ORTHO';data.clip_start=.001;data.clip_end=100
cam=bpy.data.objects.new('OpticIconCamera',data);scene.collection.objects.link(cam);scene.camera=cam
direction=Vector((-math.sin(math.radians(35)),math.cos(math.radians(35)),0))
cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
lights=[]
for name,offset,power,size in [('Key',(-1,1.4,1.5),70,2),('Fill',(1,1.3,.2),38,1.5),('Edge',(0,-1,1.2),45,1)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);lights.append((obj,Vector(offset)))
world=bpy.data.worlds.new('NeutralStudio');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.3,.3,.3,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.18
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.cycles.film_transparent_glass=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
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
    icon='bow_dark_sight_'+row['id'];scene.render.filepath=str(P/'Icons'/(icon+'.png'));bpy.ops.render.render(write_still=True)
    records.append({'icon':icon,'mesh':subject.name,'palette':'neutral-grayscale-20260927','camera_side_to_rear_degrees':35})
    (P/'render-receipt.json').write_text(json.dumps({'icons':records,'gameplay_tested':False},indent=2),encoding='utf8')
    print('BOW_OPTIC_ICON_SAVED',icon,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_SingleLensOpticIcons.blend'))
print('BOW_OPTIC_AUTHORING_COMPLETE',flush=True)
