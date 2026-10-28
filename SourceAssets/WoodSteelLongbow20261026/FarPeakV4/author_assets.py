"""Production version of the approved Far Peak concept; centimetres and original rig."""
from pathlib import Path
import bpy, math, json, sys, runpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).parent; S=P.parent
(P/'Export').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'WoodSteelLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
body=bpy.data.objects['SK_WoodSteelLongbow_Original']; rig=body.parent
for o in list(bpy.data.objects):
    if o not in (body,rig):bpy.data.objects.remove(o,do_unlink=True)
body.hide_set(False);body.hide_render=False;rig.hide_set(False)
body.name='SK_HighlandLongbow_FarPeak';body.data=body.data.copy()
for im in bpy.data.images:
    path=S/'Textures'/(im.name.split('.')[0]+'.png')
    if path.exists():im.filepath=str(path);im.reload()
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01

def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m
steel=material('M_FarPeak_BlackenedSteel',(.15,.19,.21),.85,.36)
bronze=material('M_FarPeak_RubbedBronze',(.30,.18,.07),.75,.4)
wood=material('M_FarPeak_LaminateEdge',(.20,.085,.029),0,.65)

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
bins={}
for v in body.data.vertices:bins.setdefault(round(v.co.z),[]).append(v.co.x)
centers={k:(min(xs)+max(xs))*.5 for k,xs in bins.items()}
for v in body.data.vertices:
    z=abs(v.co.z);start=29 if v.co.z>0 else 22
    # The complete rigid grip/rest/optic seat and nocking tips keep their interfaces.
    q=smooth((z-start)/16)*(1-smooth((z-(78 if v.co.z>0 else 68))/8))
    v.co.y*=1+.60*q
    v.co.x=centers[round(v.co.z)]+(v.co.x-centers[round(v.co.z)])*(1+.4*q)
body.data.update()
bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons])
def profile(z):
    vs=[v.co for v in body.data.vertices if abs(v.co.z-z)<1.8]
    return (min(v.x for v in vs)+max(v.x for v in vs))*.5,min(v.y for v in vs)
def front(x,z):
    loc,_,_,_=bvh.ray_cast(Vector((x,-40,z)),Vector((0,1,0)),80)
    return loc.y if loc else profile(z)[1]

parts=[]
def mesh(name,verts,faces,mat,solid=False):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.materials.append(mat);d.update()
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);parts.append(o)
    if solid:
        m=o.modifiers.new('Real binding thickness','SOLIDIFY');m.thickness=.16;m.offset=0
    m=o.modifiers.new('Forged bevel','BEVEL');m.width=.055;m.segments=2
    o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    bpy.context.view_layer.objects.active=o
    for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    # Only new geometry is unwrapped; original source UVs and weights survive.
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    return o
def rib(name,z0,z1,offset,width,mat):
    verts=[];count=24
    for i in range(count):
        z=z0+(z1-z0)*i/(count-1);x,_=profile(z);x+=offset
        w=width*(.48+.52*max(0.,math.sin(math.pi*i/(count-1)))**.45)
        # Inset the inner face slightly so no light gap appears along the wooden seat.
        for dx,depth in [(-w,.035),(w,.035),(w*.85,-.36),(-w*.85,-.36)]:
            verts.append((x+dx,front(x+dx,z)+depth,z))
    faces=[]
    for i in range(count-1):
        for k in range(4):faces.append((i*4+k,i*4+(k+1)%4,(i+1)*4+(k+1)%4,(i+1)*4+k))
    faces.extend([(3,2,1,0),tuple(range((count-1)*4,count*4))])
    return mesh(name,verts,faces,mat)
for sign,segments in [(1,[(15,34),(36,57),(59,78)]),(-1,[(14,31),(33,50),(52,68)])]:
    for j,(a,b) in enumerate(segments):
        for side in (-1,1):rib('Steel_%s_%s_%s'%(sign,j,side),sign*a,sign*b,side*.46,.35,steel)
        rib('Laminate_%s_%s'%(sign,j),sign*a,sign*b,0,.17,wood)
        for z in (sign*(a+1),sign*(b-1)):
            x,_=profile(z)
            vertices=[(x+dx,front(x+dx,z+dz)-.42,z+dz) for dx,dz in [(-.9,-.24),(.9,-.24),(.82,.24),(-.82,.24)]]
            mesh('BronzeBinding',vertices,[(0,1,2,3)],bronze,True)
for z in (16.5,18.2,19.9):
    x,_=profile(z)
    vs=[(x+dx,front(x+dx,z+dz)-.57,z+dz) for dx,dz in [(-1.15,-.6),(0,.25),(1.15,-.6),(1.15,-.3),(0,.55),(-1.15,-.3)]]
    mesh('MountainChevron',vs,[(0,1,4,5),(1,2,3,4)],bronze,True)

heads=json.loads((S/'authoring.json').read_text())['bone_heads_blender_cm']
for o in parts:
    groups={n:o.vertex_groups.new(name=n) for n in ['bow_body_root']+list(heads)}
    for v in o.data.vertices:
        side='upper' if v.co.z>=0 else 'lower';sign=1 if side=='upper' else -1
        names=[side+'_%02d'%(j+1) for j in range(4)]+[side+'_tip']
        z=sign*v.co.z;zs=[sign*heads[n][2] for n in names]
        if z<=zs[0]:weights={'bow_body_root':1.}
        elif z<zs[0]+5:
            t=smooth((z-zs[0])/5);weights={'bow_body_root':1-t,names[0]:t}
        else:
            j=next((j for j in range(4) if z<zs[j+1]),4)
            if j==4:weights={names[4]:1.}
            else:
                start=zs[j]+(5 if j==0 else 0);t=smooth((z-start)/(zs[j+1]-start))
                weights={names[j]:1-t,names[j+1]:t}
        for n,w in weights.items():
            if w>1e-7:groups[n].add([v.index],w,'REPLACE')
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
tri=body.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(body.name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'HighlandLongbow_FarPeak_Production.blend'))
result={'mesh':body.name,'materials':[m.name for m in body.data.materials],
    'triangles':sum(len(f.vertices)-2 for f in body.data.polygons),'bones':[b.name for b in rig.data.bones],
    'concept':str(S/'HighlandV3/HighlandLongbow_FarPeak_Concept_v2.blend'),
    'retained_interfaces':['grip','arrow_rest','sight','nock_upper','nock_lower'],'gameplay_tested':False}
(P/'authoring.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('FAR_PEAK_AUTHORED '+json.dumps(result),flush=True)
runpy.run_path(str(P/'author_icon.py'),run_name='__main__')
