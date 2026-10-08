"""Five continuous grip bodies fitted to the current XuanChi mounting rims."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
SHARED=P.parents[1]/'SharedSwordGrips20260927'
TAU=math.tau;N=128;ROWS=256;TOP=-.035;BOTTOM=-.225
OPTIONS=['shock_wrap','swift_grip','long_twohand','iron_spine_power_grip','lockweave_guard_grip']
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'SurfaceV2/XuanChi_SurfaceV2_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
factory=bpy.data.objects['SM_XuanChi_Grip_V2'];source=factory.data.copy();source.calc_loop_triangles()
normals=[n.vector.copy() for n in source.corner_normals];uv0=source.uv_layers[0].data
bvh=BVHTree.FromPolygons([v.co for v in source.vertices],[list(p.vertices) for p in source.polygons])
scene=bpy.context.scene
for ob in scene.objects:
    if ob.type=='MESH':ob.hide_render=True;ob.hide_set(True)

def smooth(t):
    t=max(0.,min(1.,t));return t*t*t*(t*(t*6.-15.)+10.)
def angle(p):return math.atan2(p.y,p.x)%TAU
def clip(poly,z,above):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0].z-z)*(1 if above else -1);db=(b[0].z-z)*(1 if above else -1)
        if da>=0:result.append(tuple(x.copy() for x in a))
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result
class Builder:
    def __init__(self):self.v=[];self.f=[];self.c=[];self.mi=[];self.lookup={}
    def vertex(self,p):
        key=tuple(round(x,7) for x in p)
        if key not in self.lookup:self.lookup[key]=len(self.v);self.v.append(tuple(p))
        return self.lookup[key]
    def polygon(self,points,mat):
        for i in range(1,len(points)-1):
            tri=[points[0],points[i],points[i+1]]
            if (tri[1][0]-tri[0][0]).cross(tri[2][0]-tri[0][0]).length<1e-12:continue
            ids=[self.vertex(x[0]) for x in tri]
            if len(set(ids))<3:continue
            self.f.append(ids);self.c.extend(tri);self.mi.append(mat)
def generated(p,a,t,normal=None):
    return (p,Vector((a/TAU,t)),normal if normal is not None else Vector((p.x,p.y,0)).normalized())
def bridge(b,upper,lower,material,uv_top,uv_bottom,t):
    upper=sorted(upper,key=lambda q:angle(q[0]));lower=sorted(lower,key=lambda q:angle(q[0]))
    i=j=0;nu=len(upper);nl=len(lower)
    def at(r,k,uv):
        q=r[k%len(r)];a=angle(q[0])+(TAU if k>=len(r) else 0)
        return generated(q[0],a,uv,q[2])
    while i<nu or j<nl:
        ua=angle(upper[(i+1)%nu][0])+(TAU if i+1>=nu else 0) if i<nu else 1e9
        la=angle(lower[(j+1)%nl][0])+(TAU if j+1>=nl else 0) if j<nl else 1e9
        if ua<=la:
            pts=[at(upper,i,uv_top),at(lower,j,uv_bottom),at(upper,i+1,uv_top)];i+=1
        else:
            pts=[at(upper,i,uv_top),at(lower,j,uv_bottom),at(lower,j+1,uv_bottom)];j+=1
        # Circular mean keeps the seam's small-angle material band continuous.
        a=math.atan2(sum(math.sin(angle(q[0])) for q in pts),sum(math.cos(angle(q[0])) for q in pts))%TAU
        b.polygon(pts,material(a,t))

def srgb(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def pbr(key):
    name='M_XuanChi_GripCopper' if key=='Copper' else 'M_SharedGrip_'+key
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Metallic'].default_value=.97 if key=='Copper' else 0.
    for suffix,pin in [('BaseColor','Base Color'),('Normal','Normal'),('Roughness','Roughness')]:
        sample=nodes.new('ShaderNodeTexImage')
        sample.image=bpy.data.images.load(str(SHARED/'Textures'/((('Steel' if key=='Copper' else key)+'_'+suffix)+'.png')),check_existing=True)
        sample.image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        output=sample.outputs['Color']
        if suffix=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(output,normal.inputs['Color']);output=normal.outputs['Normal']
        if suffix=='BaseColor' and key=='Copper':
            gray=nodes.new('ShaderNodeRGBToBW');links.new(output,gray.inputs[0])
            tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
            tint.inputs[2].default_value=tuple(srgb(c/255)*2.5 for c in [222,157,109])+(1,)
            links.new(gray.outputs[0],tint.inputs[1]);output=tint.outputs[0]
        links.new(output,bs.inputs[pin])
    return mat
materials=[source.materials[0],pbr('Leather'),pbr('Copper'),pbr('Textile')]

# The host's own radial surface is the sizing input. Remove old wrap noise
# before cutting the new wraps; the final body stays inside that grasp envelope.
raw=np.zeros((ROWS+1,N))
for row in range(ROWS+1):
    z=TOP+(BOTTOM-TOP)*row/ROWS
    for i in range(N):
        a=TAU*i/N;hit=bvh.ray_cast(Vector((0,0,z)),Vector((math.cos(a),math.sin(a),0)),.15)[0]
        if hit is None:raise RuntimeError(f'Current grip radial surface missing at {z}, {a}')
        raw[row,i]=math.hypot(hit.x,hit.y)
filtered=raw.copy();kernel=[1/16,4/16,6/16,4/16,1/16]
for _ in range(3):
    padded=np.pad(filtered,((2,2),(0,0)),mode='edge')
    filtered=sum(k*padded[i:i+ROWS+1] for i,k in enumerate(kernel))
    filtered=sum(k*np.roll(filtered,i-2,axis=1) for i,k in enumerate(kernel))
envelope=np.minimum(raw,filtered)

def weave(a,t):
    x=abs(math.sin(math.pi*(t*10+a/TAU*4)))
    y=abs(math.sin(math.pi*(t*10-a/TAU*4)))
    return max(math.exp(-((x/.48)**4)),math.exp(-((y/.48)**4)))
def length_z(z,extension):return z-extension*smooth((-z-.09)/.11)

records=[]
for option in OPTIONS:
    extension=.035 if option=='long_twohand' else 0.
    b=Builder();rings=[{},{}]
    for tri in source.loop_triangles:
        poly=[(source.vertices[source.loops[li].vertex_index].co.copy(),uv0[li].uv.copy(),normals[li].copy()) for li in tri.loops]
        for idx,(cut_z,above) in enumerate([(TOP,True),(BOTTOM,False)]):
            cropped=clip(poly,cut_z,above)
            for q in cropped:
                if idx:q[0].z-=extension
                if abs(q[0].z-(cut_z-extension*idx))<1e-7:
                    rings[idx][tuple(round(v,7) for v in q[0])]=tuple(x.copy() for x in q)
            b.polygon(cropped,0)
    def metal(a,t):
        if .025<t<.042 or .958<t<.975:return True
        if option=='iron_spine_power_grip':
            return abs(t-1/3)<.008 or abs(t-2/3)<.008 or (.042<t<.958 and abs(math.sin(a))<.14)
        if option=='swift_grip':return .08<t<.92 and abs(math.sin(2*a+.15*math.sin(math.pi*t)))<.06
        if option=='long_twohand':return abs(t-.55)<.008
        return False
    def mat(a,t):
        if metal(a,t):return 2
        return 3 if option=='lockweave_guard_grip' and weave(a,t)>.18 else 1
    grid=[list(rings[0].values())];uv_rows=[0.]
    for row in range(1,ROWS):
        t=row/ROWS;source_z=TOP+(BOTTOM-TOP)*t;z=length_z(source_z,extension)
        fade=smooth(t/.09)*smooth((1-t)/.09);ring=[]
        for i in range(N):
            a=TAU*i/N
            radius=raw[row,i]*(1-fade)+envelope[row,i]*fade
            if option=='shock_wrap':
                seam=min(abs(math.sin(math.pi*(t*11+a/TAU))),abs(math.sin(math.pi*(t*11-a/TAU))))
                depth=.00018+.0008*math.exp(-((seam/.15)**2))
            elif option=='swift_grip':
                channel=abs(math.sin(2*a+.15*math.sin(math.pi*t)))
                depth=.00040+.0005*math.exp(-((channel/.22)**2))
            elif option=='long_twohand':
                seam=abs(math.sin(math.pi*((TOP-z)/.014+a/TAU)))
                depth=.00022+.0007*math.exp(-((seam/.17)**2))
            elif option=='iron_spine_power_grip':depth=.0004+.0002*(1+math.cos(8*a))*.5
            else:depth=.00080-.00058*weave(a,t)
            if metal(a,t):depth=.00012
            radius-=depth*fade
            p=Vector((radius*math.cos(a),radius*math.sin(a),z))
            ring.append(generated(p,a,(TOP-z)/.13))
        grid.append(ring);uv_rows.append((TOP-z)/.13)
    grid.append(list(rings[1].values()));uv_rows.append((TOP-BOTTOM+extension)/.13)
    for row in range(ROWS):bridge(b,grid[row],grid[row+1],mat,uv_rows[row],uv_rows[row+1],(row+.5)/ROWS)
    name='SM_XuanChi_Grip_'+option+'_V1'
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(b.v,[],b.f);mesh.update()
    for material in materials:mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='UVMap')
    for fi,face in enumerate(mesh.polygons):
        face.material_index=b.mi[fi];face.use_smooth=True
        for li in face.loop_indices:uv.data[li].uv=b.c[li][1]
    mesh.update();custom=[n.vector.copy() for n in mesh.corner_normals]
    for face in mesh.polygons:
        for li in face.loop_indices:
            z=mesh.vertices[mesh.loops[li].vertex_index].co.z
            if face.material_index==0 or abs(z-TOP)<1e-7 or abs(z-(BOTTOM-extension))<1e-7:
                custom[li]=b.c[li][2]
    mesh.normals_split_custom_set(custom)
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    obj.hide_render=True;obj.hide_set(True)
    records.append({'option':option,'mesh':name,'length_cm':25+100*extension,
        'pommel_offset_cm':[0,0,-100*extension],'triangles':len(mesh.polygons),
        'retained_end_regions_m':[[TOP,0],[-.25,BOTTOM]],
        'materials':[m.name for m in materials],
        'animation_folder':'/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations' if extension else None})
    print('XUANCHI_GRIP_EXPORTED '+option,flush=True)
factory.hide_render=False;factory.hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_CommonGrips_Editable.blend'),compress=True)
(P/'exports.json').write_text(json.dumps({'weapon':'ue_xuanchi_zhenyue','options':records,
    'source':'../SurfaceV2/XuanChi_SurfaceV2_Editable.blend','factory_length_cm':25,
    'long_grip_extension_cm':3.5,'geometry':'Retained exact upper/lower rims and native UV/normals; continuous inset wraps inside the source hand envelope',
    'current_bone_mount':'unchanged; retain 4.5 cm grip clearance correction',
    'game_tested':False,'acceptance_render_run':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
