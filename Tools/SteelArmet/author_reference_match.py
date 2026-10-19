"""Detailed Blender armet reconstruction of Design/SteelArmet_Concept.png.

Individually editable forged skull, crown reinforcement, folded visor,
hinged cheek plates, rolled collar, working apertures, metal fasteners and liner.
All dimensions are authored in cm around Jason's anatomical eye height.
"""
import bpy,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SteelArmet20261019';O=R/'ReferenceMatchV5'
for k in ('Authored','Exports','Renders'):(O/k).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.unit_settings.system='METRIC';S.unit_settings.scale_length=1
parts=[]
def solid(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
def textured(name,family):
    m=solid(name,(.4,.4,.4),1,.4);nodes,links=m.node_tree.nodes,m.node_tree.links;bs=nodes.get('Principled BSDF')
    uv=nodes.new('ShaderNodeTexCoord');v=nodes.new('ShaderNodeVectorMath');v.operation='SCALE';v.inputs['Scale'].default_value=1 if family=='Steel' else 2.;links.new(uv.outputs['UV'],v.inputs[0])
    for ch in ('BaseColor','Normal','ORM'):
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'Textures'/f'T_Armet_{family}_{ch}.png'));links.new(v.outputs[0],tex.inputs['Vector'])
        if ch=='BaseColor':links.new(tex.outputs[0],bs.inputs['Base Color'])
        elif ch=='Normal':
            tex.image.colorspace_settings.name='Non-Color';n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.65 if family=='Steel' else 1.;links.new(tex.outputs[0],n.inputs['Color']);links.new(n.outputs[0],bs.inputs['Normal'])
        else:
            tex.image.colorspace_settings.name='Non-Color';n=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs[0],n.inputs[0]);links.new(n.outputs[1],bs.inputs['Roughness']);links.new(n.outputs[2],bs.inputs['Metallic'])
    return m
mats=[textured('ForgedSteel','Steel'),textured('CharcoalLining','Leather'),solid('WorkedEdges',(.40,.42,.44),1,.43),solid('DarkenedSteel',(.20,.22,.24),1,.48),solid('WaxedStitch',(.085,.065,.042),0,.84)]
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def uv(ob):
    active(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
def mesh(name,vs,fs,mat=0,thick=0,bevel=.035):
    me=bpy.data.meshes.new(name);me.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in vs],[],fs);me.update();ob=bpy.data.objects.new(name,me);S.collection.objects.link(ob);parts.append(ob)
    for m in mats:me.materials.append(m)
    for p in me.polygons:p.material_index=mat;p.use_smooth=True
    active(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');uv(ob)
    if thick:
        mod=ob.modifiers.new('Forged plate thickness','SOLIDIFY');mod.thickness=thick*.01;mod.offset=-1;mod.use_even_offset=True;mod.material_offset=0;mod.material_offset_rim=2 if mat==0 else 0;bpy.ops.object.modifier_apply(modifier=mod.name)
    if bevel:
        mod=ob.modifiers.new('Hand finished bevel','BEVEL');mod.width=bevel*.01;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.48;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob
def panel(name,rows,angles,fn,mat=0,thick=.22,bevel=.035):
    N=len(angles);vs=[fn(t,a) for t in rows for a in angles];fs=[(j*N+i,j*N+i+1,(j+1)*N+i+1,(j+1)*N+i) for j in range(len(rows)-1) for i in range(N-1)]
    return mesh(name,vs,fs,mat,thick,bevel)
def tube(name,points,r,mat=2,closed=False):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r*.01;cu.bevel_resolution=2
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for p,(x,y,z) in zip(sp.points,points):p.co=(x*.01,-y*.01,z*.01,1)
    sp.use_cyclic_u=closed;ob=bpy.data.objects.new(name,cu);S.collection.objects.link(ob);active(ob);bpy.ops.object.convert(target='MESH');ob=bpy.context.object
    for m in mats:ob.data.materials.append(m)
    for p in ob.data.polygons:p.material_index=mat;p.use_smooth=True
    uv(ob);parts.append(ob);return ob

# Explicit silhouette stations replace the previous spherical helmet shell.
zs=np.array([.65,3.,5.5,8.,10.3,11.8,12.8,13.5,13.8])
rx=np.array([11.35,11.5,11.25,10.65,9.2,7.4,5.25,2.6,.055])
front=np.array([13.0,12.3,11.2,9.6,7.35,5.2,3.4,1.5,.055])
rear=np.array([10.25,10.7,10.9,10.3,8.8,6.9,4.8,2.1,.055])
class PchipInterpolator:
    def __init__(self,x,y):
        self.x=np.array(x,dtype=float);self.y=np.array(y,dtype=float);h=np.diff(self.x);d=np.diff(self.y)/h;self.m=np.zeros(len(x));self.m[0]=d[0];self.m[-1]=d[-1]
        for i in range(1,len(x)-1):
            if d[i-1]*d[i]>0:
                w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1];self.m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    def __call__(self,v):
        i=int(np.clip(np.searchsorted(self.x,v)-1,0,len(self.x)-2));h=self.x[i+1]-self.x[i];t=float(np.clip((v-self.x[i])/h,0,1))
        return (2*t**3-3*t*t+1)*self.y[i]+(t**3-2*t*t+t)*h*self.m[i]+(-2*t**3+3*t*t)*self.y[i+1]+(t**3-t*t)*h*self.m[i+1]
RX=PchipInterpolator(zs,rx);FR=PchipInterpolator(zs,front);BK=PchipInterpolator(zs,rear)
def crown(t,a):
    z=.65+13.15*t;sn,cs=math.sin(a),math.cos(a);width=float(RX(z));x=width*sn
    # A shallow forged median arris, split at the centre for a crisp fold normal.
    y=(float(FR(z)) if cs>=0 else float(BK(z)))*cs
    if cs>=0:
        blend=max(0.,1-(abs(a)/1.3)**4)
        planar=float(FR(z))*(1-.39*abs(sn))
        y=y*(1-blend)+planar*blend
        y+=.50*(1-t)*math.exp(-abs(x)/1.25)
    z+=(.25*cs*cs if cs>0 else 0)*(1-t)
    return [x,y,z]
for side in (-1,1):
    panel(('L' if side<0 else 'R')+' forged skull',np.linspace(0,1,49),np.linspace(0,side*math.pi,97),crown)
tip=crown(1,0);mesh('Crown finite closure',[crown(1,a) for a in np.linspace(-math.pi,math.pi,96,endpoint=False)]+[[0,0,13.84]],[(i,(i+1)%96,96) for i in range(96)],0,.13,.025)

Z=np.array([-15.3,-13.,-10.,-7.,-4.,0.,4.]);W=PchipInterpolator(Z,[7.4,8.15,9.25,10.3,10.9,11.35,11.45]);F=PchipInterpolator(Z,[11.6,12.1,12.9,13.7,13.7,12.8,12.0]);B=PchipInterpolator(Z,[7.3,7.8,8.9,9.6,10.1,10.25,10.8]);N=PchipInterpolator(Z,[.15,.3,.6,1.4,1.0,.75,.4])
def envelope(z,a,offset=0):
    sn,cs=math.sin(a),math.cos(a);x=float(W(z))*sn;y=(float(F(z)) if cs>=0 else float(B(z)))*cs
    if cs>0:
        aa=abs(math.atan2(sn,cs));blend=max(0.,1-(aa/1.32)**4)
        planar=float(F(z))*(1-.39*abs(sn))
        y=y*(1-blend)+planar*blend+float(N(z))*(1-abs(sn))**1.1
    radial=Vector((x,y,0)).normalized();return [x+radial.x*offset,y+radial.y*offset,z]
limit=math.radians(79)
def vlow(a):return -6.25+5.78*(abs(a)/limit)**1.10
def vtop(a):return -.37+.09*math.cos(a)**2
def visor(t,a):return envelope((1-t)*vlow(a)+t*vtop(a),a,.34)
visor_parts=[]
for side in (-1,1):
    ob=panel(('L' if side<0 else 'R')+' folded lifting visor',np.linspace(0,1,33),np.linspace(0,side*limit,65),visor,0,.25,.055);visor_parts.append(ob)
    # Deliberate curved bottom plate seam, made by the real thickness over the cheek.
    tube('Visor lower worked bevel '+str(side),[visor(0,a) for a in np.linspace(0,side*limit,110)],.07)
tube('Upper rolled eye lip',[crown(0,a) for a in np.linspace(-limit,limit,150)],.09)
tube('Lower rolled eye lip',[visor(1,a) for a in np.linspace(-limit,limit,150)],.085)

cheeks=[];cheek_limit=math.radians(108)
def bottom(a):return -15.3+2.1*abs(math.sin(a))**1.3
def cheek_top(a):
    aa=abs(a)
    if aa<=limit:return vlow(a)+.18
    return float(np.interp(aa,[limit,math.radians(87),cheek_limit],[vlow(limit)+.18,4.,2.3]))
def cheek(t,a):return envelope((1-t)*bottom(a)+t*cheek_top(a),a,-.03)
for side in (-1,1):
    angles=np.linspace(side*.002,side*cheek_limit,81)
    cheeks.append(panel(('L' if side<0 else 'R')+' hinged cheek plate',np.linspace(0,1,40),angles,cheek,0,.24,.045))
    tube('Cheek rear worked seam '+str(side),[cheek(t,side*cheek_limit) for t in np.linspace(0,1,110)],.075)
panel('Rear skull lower return',np.linspace(0,1,40),np.linspace(cheek_limit-.006,math.tau-cheek_limit+.006,110),lambda t,a:envelope((1-t)*bottom(a)+t*1.05,a,-.045),0,.23,.045)

# Exact breathing bores, perpendicular to the worked cheek; beveled inner walls.
for j in range(3):
    for i in range(3-j//2):
        a=.33+i*.13;z=-8.7-j*1.35;p=Vector(envelope(z,a));normal=Vector((.30,1,.02)).normalized()
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0026,depth=.10,location=(p.x*.01,-p.y*.01,p.z*.01))
        cut=bpy.context.object;axis=Vector((normal.x,-normal.y,normal.z));cut.rotation_euler=axis.to_track_quat('Z','Y').to_euler();ob=cheeks[1];active(ob)
        mod=ob.modifiers.new('Actual drilled breathing aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
active(cheeks[1]);mod=cheeks[1].modifiers.new('Vent deburring','BEVEL');mod.width=.00035;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.68;bpy.ops.object.modifier_apply(modifier=mod.name)

# A short flared, hollow collar with a rolled edge and inset stitched leather.
angles=np.linspace(.075,math.tau-.075,241)
def collar(t,a):
    p=np.array(envelope(bottom(a),a));p[:2]*=1+.075*t;p[2]-=1.25*t;return p.tolist()
panel('Flared steel neck flange',np.linspace(0,1,7),angles,collar,0,.22,.05)
tube('Collar rolled lower edge',[collar(1,a) for a in angles],.15,2,False)
tube('Charcoal collar padding',[(p[0]*.963,p[1]*.963,p[2]-.25) for p in [collar(1,a) for a in angles]],.39,1,False)
for a in np.arange(.09,math.tau-.12,.085):
    ps=[]
    for aa in (a,a+.035):p=np.array(collar(1,aa));p[:2]*=.968;p[2]-=.53;ps.append(p.tolist())
    tube('Collar waxed stitch',ps,.022,4)

# Reinforcement plate over the crown: a swept, tapered strip ending above brow.
def cap(u,v):
    # front to rear over the sagittal crest; width follows the dome.
    if u<=.5:t=.69+.075*v*v+(.309-.075*v*v)*(u/.5);a=v*.85
    else:t=.999-(.31-.075*v*v)*((u-.5)/.5);a=math.pi-v*.85
    p=np.array(crown(t,a));direction=np.array([p[0],p[1],(p[2]-1)*.7]);direction/=max(np.linalg.norm(direction),1e-8);return (p+direction*.14).tolist()
panel('Swept crown reinforcement',np.linspace(0,1,70),np.linspace(-1,1,19),cap,0,.12,.035)
for v in (-1,1):tube('Crown cap fine edge',[cap(u,v) for u in np.linspace(0,1,160)],.045,3)

def cylinder(name,p,normal,r,depth,mat=2):
    axis=Vector((normal[0],-normal[1],normal[2])).normalized();bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r*.01,depth=depth*.01,location=(p[0]*.01,-p[1]*.01,p[2]*.01));ob=bpy.context.object;ob.name=name;ob.rotation_euler=axis.to_track_quat('Z','Y').to_euler()
    for m in mats:ob.data.materials.append(m)
    for f in ob.data.polygons:f.material_index=mat;f.use_smooth=True
    active(ob);mod=ob.modifiers.new('Machined fastening edge','BEVEL');mod.width=min(depth*.24,.07)*.01;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name);uv(ob);parts.append(ob);return ob
def rivet(name,p,normal,r=.35):
    p=np.array(p);normal=np.array(normal)/np.linalg.norm(normal);cylinder(name+' washer',p,normal,r*1.22,.09,3)
    p+=normal*.10;bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=1,location=(p[0]*.01,-p[1]*.01,p[2]*.01));ob=bpy.context.object;ob.name=name+' peened head';ob.scale=(r*.01,r*.01,min(.25,r*.55)*.01);ob.rotation_euler=Vector((normal[0],-normal[1],normal[2])).to_track_quat('Z','Y').to_euler();active(ob);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for m in mats:ob.data.materials.append(m)
    for f in ob.data.polygons:f.material_index=2;f.use_smooth=True
    parts.append(ob)
for side in (-1,1):
    a=side*math.radians(87);p=np.array(envelope(2.6,a,.24));normal=np.array([side,0,0])
    cylinder('Visor hinge base '+str(side),p,normal,.93,.22,3);cylinder('Concentric hinge plate '+str(side),p+normal*.15,normal,.78,.18);rivet('Hinge pin '+str(side),p+normal*.29,normal,.51)
    # Tapered riveted strap from pivot to the back skull.
    q=np.array(envelope(3.9,side*math.radians(101),.15));rivet('Upper hinge anchor '+str(side),q,[side,-.2,.05],.32)
    # The stepped side strap follows the reference's angular cheek hinge plate.
    strap=[]
    for angle,z in [(82,1.1),(86,3.1),(96,4.5),(91,6.1),(100,7.6),(106,7.0),(98,5.9),(103,4.1),(92,2.2),(88,.6)]:
        aa=side*math.radians(angle);p=np.array(crown((z-.65)/13.15,aa) if z>=.65 else envelope(z,aa));rad=np.array([p[0],p[1],0]);rad/=max(np.linalg.norm(rad),1e-8);strap.append((p+rad*.22).tolist())
    mesh('Stepped hinge cheek strap '+str(side),strap,[tuple(range(len(strap)))],0,.16,.06)
    for aa in (side*.72,side*1.33,side*2.1):
        p=np.array(collar(.6,aa));out=np.array([p[0],p[1],0]);out/=np.linalg.norm(out);rivet('Collar rivet',p+out*.11,out,.23)
peg=np.array(envelope(-8.3,-.60,.20));normal=np.array([-.35,.94,0]);rivet('Visor latch base',peg,normal,.39)
tube('Angled lifting peg',[peg.tolist(),(peg+normal*1.5+[0,0,.45]).tolist(),(peg+normal*1.65+[0,0,.85]).tolist()],.15)
rivet('Lifting peg rounded end',peg+normal*1.65+[0,0,.85],normal,.22)

# Real inner padding never fills intentional eye / vent openings.
panel('Crown charcoal lining',np.linspace(.03,.996,44),np.linspace(-math.pi,math.pi,137),lambda t,a:(np.array(crown(t,a))*[.952,.952,1]-[0,0,.35]).tolist(),1,.18,.025)
panel('Rear neck lining',np.linspace(0,1,28),np.linspace(cheek_limit,math.tau-cheek_limit,85),lambda t,a:envelope((1-t)*bottom(a)+t*.9,a,-.43),1,.18,.025)
# Leather seating strips behind each cheek edge preserve the actual front gap.
for side in (-1,1):
    tube('Cheek inner leather welt '+str(side),[(p[0]*.97,p[1]*.97,p[2]+.05) for p in [cheek(t,side*cheek_limit) for t in np.linspace(0,1,100)]],.20,1)

# Consistent physical UV density across steel plates, no tiny packed islands
# magnifying the surface noise into broad cloudy patches. Seam is at the rear.
for ob in parts:
    me=ob.data;layer=me.uv_layers.active or me.uv_layers.new(name='PhysicalSteelUV')
    for poly in me.polygons:
        coords=[]
        for li in poly.loop_indices:
            p=ob.matrix_world@me.vertices[me.loops[li].vertex_index].co
            coords.append([(math.atan2(p.x,-p.y)+math.pi)*11.4/12,p.z*100/12])
        if max(q[0] for q in coords)-min(q[0] for q in coords)>math.pi*11.4/12:
            for q in coords:
                if q[0]<math.pi*11.4/12:q[0]+=math.tau*11.4/12
        for li,q in zip(poly.loop_indices,coords):layer.data[li].uv=q

def export_json(obs,path,view=None):
    ps=[];fs=[];ns=[];uvs=[];slots=[];deps=bpy.context.evaluated_depsgraph_get()
    for ob in obs:
        ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();start=len(ps);matrix=ob.matrix_world
        for v in me.vertices:
            p=matrix@v.co
            if view:q=view@p;ps.append([-q.z*100,q.x*100,q.y*100])
            else:ps.append([p.x*100,-p.y*100,p.z*100])
        nm=matrix.to_3x3().inverted().transposed();layer=me.uv_layers.active
        for tri in me.loop_triangles:
            fs.append([start+i for i in tri.vertices]);name=ob.data.materials[tri.material_index].name;slots.append(next(i for i,m in enumerate(mats) if m.name==name));norm=[];uv=[]
            for li in tri.loops:
                n=(nm@me.corner_normals[li].vector).normalized()
                if view:q=view.to_3x3()@n;norm.append([-q.z,q.x,q.y])
                else:norm.append([n.x,-n.y,n.z])
                a,b=layer.data[li].uv if layer else (0,0);uv.append([a,1-b])
            ns.append(norm);uvs.append(uv)
        ev.to_mesh_clear()
    data=dict(profile='SteelArmetRefined',positions=ps,triangles=fs,normals=ns,uv=uvs,triangle_materials=slots,material_slots=[m.name for m in mats]);path.write_text(json.dumps(data,separators=(',',':')));return data

# Exact native reference retained as a hidden fit collection in the editable file.
head=json.loads((P/'SourceAssets/BlueMageHat20261019/native_head_jason.json').read_text());ref=bpy.data.collections.new('REFERENCE_NativeJasonHead');S.collection.children.link(ref);ref.hide_render=True;ref.hide_viewport=True
me=bpy.data.meshes.new('Native head at eye origin');me.from_pydata([((x)*.01,-(y-1.5)*.01,(z-164)*.01) for x,y,z in head['positions']],[],head['triangles']);ob=bpy.data.objects.new(me.name,me);ref.objects.link(ob);ob.display_type='WIRE'
S.render.engine='CYCLES';S.cycles.samples=128;S.cycles.use_denoising=True;S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA';S.render.resolution_percentage=100
S.render.threads_mode='FIXED';S.render.threads=10
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=-.65
world=bpy.data.worlds.new('Studio charcoal');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.20,.23,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;S.world=world
for name,pos,power,size in [('Broad key',(-.45,-.55,.55),24,.40),('Soft fill',(.55,-.1,.22),6,.65),('Skull edge',(.10,.45,.55),30,.40)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;lo=bpy.data.objects.new(name,ld);S.collection.objects.link(lo);lo.location=pos;lo.rotation_euler=(-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Design match camera');cd.type='ORTHO';cd.ortho_scale=.390;cd.clip_start=.001;cam=bpy.data.objects.new(cd.name,cd);S.collection.objects.link(cam);S.camera=cam
def camera(pos,target=(0,-.012,.004)):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
camera((.59,-.85,.22));S.render.film_transparent=True
d=export_json(parts,O/'Authored/helmet.json');export_json(parts,O/'Authored/display.json',cam.matrix_world.inverted())
active(parts[0])
for ob in parts:ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SteelArmet_Detailed.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Exports/SteelArmet_Detailed.blend'))
S.render.resolution_x=640;S.render.resolution_y=640;S.render.filepath=str(O/'ue_steel_armet.png');bpy.ops.render.render(write_still=True)
S.render.film_transparent=False;S.render.resolution_x=1320;S.render.resolution_y=1500;cd.ortho_scale=.41
for name,pos in [('ThreeQuarter',(.59,-.85,.22)),('Front',(0,-.9,.055)),('Side',(.9,-.012,.06)),('Rear',(.40,.85,.17))]:
    camera(pos);S.render.filepath=str(O/'Renders'/('SteelArmet_'+name+'.png'));bpy.ops.render.render(write_still=True)
result=dict(completed=True,triangles=len(d['triangles']),parts=len(parts),material_slots=d['material_slots'],source_reference='Design/SteelArmet_Concept.png',world_origin_cm=[0,1.5,164],editable=str(O/'Exports/SteelArmet_Detailed.blend'),fbx=str(O/'Exports/SteelArmet_Detailed.fbx'),finish_revision='worn-forged-steel-v5',geometry_revision='reference-profile-v5',runtime_tested=False,imported=False)
(O/'authored.json').write_text(json.dumps(result,indent=2));print('DETAILED_ARMET_AUTHORED',len(d['triangles']),len(parts),flush=True)
