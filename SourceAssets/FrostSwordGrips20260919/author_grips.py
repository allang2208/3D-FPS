"""Precision-built interchangeable grips, retaining both original mounting rims.

The body is a continuous loft; wrap seams and channels are real geometry.
Only source geometry, editable models, FBX and UI icons are authored here.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
TAU=math.tau;N=128;ROWS=192;TOP=-.020;BOTTOM=-.157
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'))
source=bpy.data.objects['SM_FrostSword_Grip_factory'].data.copy()
source.calc_loop_triangles()
bvh=BVHTree.FromPolygons([v.co for v in source.vertices],[list(p.vertices) for p in source.polygons])
normals=[x.vector.copy() for x in source.corner_normals]
uv0=source.uv_layers[0].data;uv1=source.uv_layers.get('StockBronzeUV').data
col=source.color_attributes.get('GuardFinish').data
stock_material=source.materials[0]
for obj in list(bpy.data.objects):
    if obj.library is None:bpy.data.objects.remove(obj,do_unlink=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not p:
        p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');o=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs['BSDF'],o.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    return m
silver=material('M_Grip_Silver',(.48,.55,.62),.85,.32)
leather=material('M_Grip_Leather',(.032,.052,.072),0,.64)
ln=leather.node_tree.nodes;ll=leather.node_tree.links
uv=ln.new('ShaderNodeTexCoord');noise=ln.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=160;noise.inputs['Detail'].default_value=2
ll.new(uv.outputs['UV'],noise.inputs['Vector'])
bump=ln.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.00016
ll.new(noise.outputs['Fac'],bump.inputs['Height']);ll.new(bump.outputs['Normal'],next(n for n in ln if n.type=='BSDF_PRINCIPLED').inputs['Normal'])
materials=[stock_material,leather,silver]

def clip(poly,z,above):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0].z-z)*(1 if above else -1);db=(b[0].z-z)*(1 if above else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result

def angle(p):return math.atan2(p.y,p.x)%TAU
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)

def radial(z,a):
    d=Vector((math.cos(a),math.sin(a),0))
    hit=bvh.ray_cast(Vector((0,0,z)),d,.1)[0]
    if hit is None:raise RuntimeError('Source radial surface missing at '+str((z,a)))
    return hit

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
    return (p,Vector((a/TAU,t*1.5)),Vector((.97,.905)),Vector((1,1,1,1)),normal or Vector((p.x,p.y,0)).normalized())

def bridge(builder,upper,lower,mat,t0,t1):
    """Zipper unequal rings using their angular order, sharing exact end vertices."""
    upper=sorted(upper,key=lambda q:angle(q[0]));lower=sorted(lower,key=lambda q:angle(q[0]))
    i=j=0;nu=len(upper);nl=len(lower)
    def at(r,k,t):
        q=r[k%len(r)];a=angle(q[0])+(TAU if k>=len(r) else 0)
        return generated(q[0],a,t,q[4])
    while i<nu or j<nl:
        ua=angle(upper[(i+1)%nu][0])+(TAU if i+1>=nu else 0) if i<nu else 1e9
        la=angle(lower[(j+1)%nl][0])+(TAU if j+1>=nl else 0) if j<nl else 1e9
        if ua<=la:
            builder.polygon([at(upper,i,t0),at(lower,j,t1),at(upper,i+1,t0)],mat);i+=1
        else:
            builder.polygon([at(upper,i,t0),at(lower,j,t1),at(lower,j+1,t1)],mat);j+=1

def build(key,extension):
    out=P/key;out.mkdir(exist_ok=True);b=Builder();rings=[{},{}]
    for tri in source.loop_triangles:
        poly=[]
        for li in tri.loops:
            poly.append((source.vertices[source.loops[li].vertex_index].co.copy(),uv0[li].uv.copy(),uv1[li].uv.copy(),Vector(col[li].color),normals[li].copy()))
        for idx,(z,above) in enumerate([(TOP,True),(BOTTOM,False)]):
            cropped=clip(poly,z,above)
            for q in cropped:
                if abs(q[0].z-z)<1e-7:rings[idx][tuple(round(c,7) for c in q[0])]=tuple(c.copy() for c in q)
            if idx:
                for q in cropped:q[0].z-=extension
            b.polygon(cropped,0)
    top=list(rings[0].values());bottom=list(rings[1].values())
    for q in bottom:q[0].z-=extension
    # Blend from copied collars through exact source cross-sections; the body
    # fits inside the stock grasp envelope, including its ergonomic waist.
    grid=[top]
    for row in range(1,ROWS):
        t=row/ROWS;z=TOP+(BOTTOM-TOP-extension)*t
        # Long grip keeps the right hand region unchanged; extension is inserted
        # over the middle/lower zone instead of scaling the metal end ferrules.
        source_z=TOP+(BOTTOM-TOP)*t
        if extension:
            source_z=z+extension*smooth((-z-.060)/.092)
            source_z=max(BOTTOM+.00001,min(TOP-.00001,source_z))
        fade=smooth(t/.09)*smooth((1-t)/.09)
        ring=[]
        for i in range(N):
            a=TAU*i/N;p=radial(source_z,a);radius=math.hypot(p.x,p.y)
            if key=='shock_wrap':
                seam_a=abs(math.sin(math.pi*(t*7+a/TAU)))
                seam_b=abs(math.sin(math.pi*(t*7-a/TAU)))
                seam=min(seam_a,seam_b)
                depth=.00025+.0012*math.exp(-((seam/.14)**2))
            elif key=='swift_grip':
                channel=abs(math.sin(2*a+.32*math.sin(math.pi*t)))
                finger=math.exp(-((abs(math.sin(math.pi*t*6))/.2)**2))
                depth=.0004+.0008*math.exp(-((channel/.19)**2))+.00025*finger
            else:
                seam=abs(math.sin(math.pi*(t*10+a/TAU))) if t<.465 else abs(math.sin(math.pi*(t-.465)*23))
                depth=.00025+.00095*math.exp(-((seam/.16)**2))
            p*=max(.85,(radius-depth*fade)/radius);p.z=z
            ring.append(generated(p,a,t))
        grid.append(ring)
    grid.append(bottom)
    for row in range(ROWS):
        t=(row+.5)/ROWS
        mat=2 if .038<t<.060 or .94<t<.962 or (key=='long_twohand' and .447<t<.465) else 1
        bridge(b,grid[row],grid[row+1],mat,row/ROWS,(row+1)/ROWS)
    # Slender silver accent rails sit recessed inside the original envelope.
    if key=='swift_grip':
        for base in [.38,math.pi-.38,math.pi+.38,TAU-.38]:
            for row in range(12,ROWS-12):
                pts=[]
                for rr,side in [(row,-1),(row+1,-1),(row+1,1),(row,1)]:
                    t=rr/ROWS;a=base+.12*math.sin(math.pi*t)+side*.017
                    z=TOP+(BOTTOM-TOP)*t;p=radial(z,a);r=math.hypot(p.x,p.y);p*=max(.8,(r-.00022)/r);p.z=z
                    pts.append(generated(p,a,t))
                # Ensure outward orientation independently of the rail's winding.
                if (pts[1][0]-pts[0][0]).cross(pts[2][0]-pts[0][0]).dot(Vector((pts[0][0].x,pts[0][0].y,0)))<0:pts.reverse()
                b.polygon(pts,2)
    name='SM_FrostGrip_'+key;m=bpy.data.meshes.new(name);m.from_pydata(b.v,[],b.f);m.update()
    for mat in materials:m.materials.append(mat)
    uv=m.uv_layers.new(name='UVMap');uvb=m.uv_layers.new(name='StockBronzeUV');color=m.color_attributes.new(name='GuardFinish',type='FLOAT_COLOR',domain='CORNER')
    for fi,f in enumerate(m.polygons):
        f.material_index=b.mi[fi];f.use_smooth=True
        for li in f.loop_indices:
            q=b.c[li];uv.data[li].uv=q[1];uvb.data[li].uv=q[2];color.data[li].color=q[3]
    m.update()
    calculated=[n.vector.copy() for n in m.corner_normals]
    # Keep stock normals on the metal and exact shared cut ring. New body normals
    # follow the real channels, avoiding a flat-looking normal-only wrap.
    for f in m.polygons:
        for li in f.loop_indices:
            z=m.vertices[m.loops[li].vertex_index].co.z
            if f.material_index==0 or abs(z-TOP)<1e-7 or abs(z-(BOTTOM-extension))<1e-7:calculated[li]=b.c[li][4]
    m.normals_split_custom_set(calculated)
    obj=bpy.data.objects.new(name,m);scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'_Editable.blend')))
    print('GRIP_EXPORTED '+key,flush=True)
    bpy.data.objects.remove(obj,do_unlink=True)
    return {'id':key,'mesh':name,'length_cm':17.7+extension*100,'pommel_offset_cm':[0,0,-extension*100],'source':'original stock mounting rims retained; Blender precision loft'}

rows=[build(k,e) for k,e in [('shock_wrap',0),('swift_grip',0),('long_twohand',.028)]]
(P/'models.json').write_text(json.dumps(rows,indent=2))
