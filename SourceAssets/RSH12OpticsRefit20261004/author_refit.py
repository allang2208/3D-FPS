"""Compact the three 1x optics and restore PSO's original side bracket."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;OUT=O/'Exports';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
C=json.loads((S/'RSH12Optics20261004/inputs.json').read_text())
M=json.loads((S/'RSH12Optics20261004/mounts.json').read_text())
R=dict(compact={},pso={},meshes={},runtime_tested=False)
SCALE=.78;TOP=.003;OLD_TOP=.0065
centers={'holographic':[-.653782,0,5.175324],'panoramic_red_dot':[2.125,0,3.25]}
mountmat=None

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
def export(name,obs):
    select(obs)
    for ob in obs:
        bpy.context.view_layer.objects.active=ob
        tri=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    file=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    return str(file)
def finish(ob):
    select([ob]);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    ob.data.materials.clear();ob.data.materials.append(mountmat)
    bevel=ob.modifiers.new('Machined edge breaks','BEVEL');bevel.width=.00018;bevel.segments=2;bpy.ops.object.modifier_apply(modifier=bevel.name)
    uv=ob.data.uv_layers.new(name='RSHMountUV')
    for f in ob.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
        for li in f.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    return ob
def solid(name,verts,faces):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return finish(ob)
def extrude(name,x0,x1,section):
    n=len(section);verts=[(x,y,z) for x in (x0,x1) for y,z in section]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return solid(name,verts,faces)
def block(name,p,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);ob=bpy.context.object;ob.name=name;ob.scale=size;return finish(ob)

for key in ('holographic','panoramic_red_dot','eoth_holographic'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info=C['meshes'][key];bpy.ops.import_scene.fbx(filepath=info['fbx'],use_anim=False)
    parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
    offset=M['parts'][key]['body_offset_cm'][0]/100;anchor=Vector((-offset,0,0))
    tx=Matrix.Translation(anchor+Vector((0,0,TOP-OLD_TOP)))@Matrix.Scale(SCALE,4)@Matrix.Translation(-anchor)
    slots={s['material'].rsplit('.',1)[-1]:s['slot'] for s in info['slots']}
    for ob in parts:
        ob.data.transform(tx@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
        for mat in ob.data.materials:
            name=mat.name
            match=next((v for k,v in slots.items() if name==k or name.startswith(k+'.')),None)
            if match:mat.name=match
    sockets=info['sockets_cm'].copy()
    if key in centers:
        r=centers[key];sockets.update(AimCenter=r,SightRear=r,SightFront=[r[0]+10,r[1],r[2]],SightUp=[r[0],r[1],r[2]+1])
    transformed={}
    for name,p in sockets.items():
        v=tx@Vector((p[0]/100,-p[1]/100,p[2]/100));transformed[name]=[v.x*100,-v.y*100,v.z*100]
    file=export('SM_RSH12_'+key,parts)
    R['meshes'][key]=dict(fbx=file,asset='/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_'+key,sockets_cm=transformed)
    # Keep the lower jaws fitted to the original gun; shrink only the upper shoe.
    mountmat=bpy.data.materials.new('RSH_OpticMountSteel');rails=[]
    length=M['parts'][key]['rail_length_m']*SCALE
    rails.append(extrude('Low rail web',-length/2,length/2,[(-.0062,.00005),(.0062,.00005),(.0065,.0015),(-.0065,.0015)]))
    for x in np.arange(-length/2+.0024,length/2,.0078):
        rails.append(extrude('Compact rail tooth',max(-length/2,x-.0023),min(length/2,x+.0023),[(-.0062,.0007),(.0062,.0007),(.0089,.0017),(.0081,TOP),(-.0081,TOP),(-.0089,.0017)]))
    section=[(.0056,.00005),(.0084,-.00195),(.00715,-.00425),(.0105,-.00425),(.0105,.0014),(.0080,.0018)]
    for x in (-.0184012,.0184012):
        for sign in (-1,1):
            rails.append(extrude('Receiver jaw',x-.0045,x+.0045,[(sign*y,z) for y,z in section]))
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.002,depth=.0014,location=(x,sign*.0107,-.0008),rotation=(math.pi/2,0,0));ob=bpy.context.object;ob.name='Jaw screw';rails.append(finish(ob))
        rails.append(block('Recoil lug',(x,0,-.00205),(.00415,.0135,.0042)))
    rf=export('SM_RSH12_Rail_'+key,rails)
    R['meshes']['rail_'+key]=dict(fbx=rf,asset='/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_Rail_'+key)
    R['compact'][key]=dict(scale=SCALE,old_height_m=OLD_TOP,new_height_m=TOP,foot_anchor_m=list(anchor))
    for ob in parts:ob.hide_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'_Editable.blend')))

# The AKM source retains the original side clamp/lever and repaired opaque seams.
bpy.ops.wm.open_mainfile(filepath=str(S/'PSO1Russian20260923/PSO1_AKM_Editable.blend'))
for ob in list(bpy.context.scene.objects):
    if ob.name not in ('PSO_ScopeBody','PSO_ScopeLens','PSO_ScopeMount'):bpy.data.objects.remove(ob,do_unlink=True)
optic=list(bpy.context.scene.objects);rail_center=Vector(M['rail_center_canonical_m'])
def gun_point(p):return Vector((p.y-.0055,-p.x,p.z-.004))
def mount_point(g,optic=False):return Vector((-g.y+rail_center.y,g.x,g.z-rail_center.z-(OLD_TOP if optic else 0)))
for ob in optic:
    # Data is canonical +X-forward; the saved -90 display rotation is not baked twice.
    ob.matrix_world=Matrix.Identity(4)
    for v in ob.data.vertices:v.co=mount_point(gun_point(v.co),True)
    for mat in ob.data.materials:
        if 'Shell' in mat.name:mat.name='PSO1_RSH_Shell'
        elif 'OpticalGlass' in mat.name:mat.name='PSO1_OpticalGlass'
    ob.data.update()
markers=json.loads((S/'PSO1Russian20260923/authoring.json').read_text())['hosts']['AKM']['sockets_cm']
sockets={}
for name,source in [('AimCenter','AimCenter'),('SightRear','AimCenter'),('SightFront','AimFront')]:
    p=markers[source];v=mount_point(gun_point(Vector((p[0]/100,-p[1]/100,p[2]/100))),True);sockets[name]=[v.x*100,-v.y*100,v.z*100]
r=sockets['SightRear'];sockets['SightUp']=[r[0],r[1],r[2]+1]
R['meshes']['pso1_4x']=dict(fbx=export('SM_RSH12_PSO1',optic),asset='/Game/Weapons/RSH12/PSO20261004/Meshes/SM_RSH12_PSO1',sockets_cm=sockets)

# Receiver pads attach to the barrel shroud ahead of the moving cylinder.
raw=json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text());vertices=[];faces=[]
for p in raw:
    if p['name'] not in ('1_l','2_l','3_l'):continue
    offset=len(vertices);vertices.extend(p['verts']);faces.extend([tuple(i+offset for i in f) for f in p['faces']])
bvh=BVHTree.FromPolygons(vertices,faces);mountmat=bpy.data.materials.new('RSH_PSO_MountSteel');shoe=[];contacts=[]
outer=.0233-.0055;cy=-.0963;cz=.050-.004
cube_faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
for y in (cy-.027,cy+.027):
    pad=[]
    for yy,zz in [(y-.009,cz-.006),(y+.009,cz-.006),(y+.009,cz+.006),(y-.009,cz+.006)]:
        p,n,index,d=bvh.ray_cast(Vector((.2,yy,zz)),Vector((-1,0,0)),.4)
        if p is None:raise RuntimeError('No fixed RSH side contact '+str((yy,zz)))
        contacts.append(list(p));pad.append(p-Vector((.0001,0,0)))
    top=max(v.x for v in pad)+.0018
    points=pad+[Vector((top,p.y,p.z)) for p in pad]
    shoe.append(solid('Contoured receiver pad',[list(p) for p in points],cube_faces))
    shoe.append(block('Shallow bridge',((top+outer)/2,y,cz),(outer-top+.001,.010,.006)))
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0025,depth=.002,location=(outer+.002,y,cz),rotation=(0,math.pi/2,0));ob=bpy.context.object;ob.name='Side clamp bolt';shoe.append(finish(ob))
shoe.append(block('Original clamp dovetail',(outer,cy,cz),(.004,.078,.014)))
shoe.append(block('Side recoil stop',(outer+.001,cy-.039,cz),(.005,.003,.017)))
for ob in shoe:
    for v in ob.data.vertices:v.co=mount_point(v.co)
    ob.data.update()
R['meshes']['pso_side_shoe']=dict(fbx=export('SM_RSH12_PSOReceiverShoe',shoe),asset='/Game/Weapons/RSH12/PSO20261004/Meshes/SM_RSH12_PSOReceiverShoe')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RSH12_PSO_SideMount_Editable.blend'))
R['pso']=dict(source='PSO1_AKM_Editable.blend; original scope mount, body and lens',body_scale=1.,source_to_gun='(p.y-.0055,-p.x,p.z-.004)',contacts_gun_m=contacts,contact_parts=['1_l','2_l','3_l'],foot_cut=False)
(O/'authoring.json').write_text(json.dumps(R,indent=2));print('RSH_OPTIC_REFIT_AUTHORED',len(R['meshes']),flush=True)
