"""Refine the saved game model in its existing local frame and export the two changed meshes."""
from pathlib import Path
import bpy,bmesh,math,sys,json
from mathutils import Vector, Matrix
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from wheel_geometry import *
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'FrontierCompoundBow.blend'))
bpy.context.preferences.filepaths.save_version=0
sc=bpy.context.scene;sc.frame_set(1);rig=sc.objects['Armature']
rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for n in ['ControlCable1','ControlCable2','MainString_upper','MainString_lower']:
    bpy.data.objects.remove(sc.objects[n],do_unlink=True)
cord=bpy.data.materials['M_Frontier_Cord']
def select(objs,active):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=active
def join(base,extra):
    select([base]+extra,base);bpy.ops.object.join();return base
def make(name,verts,faces,binding=None):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.materials.append(cord);m.update()
    bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
    ob=bpy.data.objects.new(name,m);sc.collection.objects.link(ob)
    if binding:
        ob.parent=rig;mod=ob.modifiers.new('Track','ARMATURE');mod.object=rig
        groups={}
        for i,k in enumerate(binding):
            if k not in groups:groups[k]=ob.vertex_groups.new(name=k)
            groups[k].add([i],1.,'REPLACE')
    for face in m.polygons:face.use_smooth=True
    return ob
def pipe(name,points,radius,binding=None,loop=False):
    nv=10;verts=[];faces=[]
    for i,p in enumerate(points):
        prev=points[(i-1)%len(points)] if loop or i else points[0]
        nxt=points[(i+1)%len(points)] if loop or i+1<len(points) else points[-1]
        tangent_=(nxt-prev).normalized()
        up=Vector((0,1,0)) if abs(tangent_.y)<.90 else Vector((0,0,1))
        a=tangent_.cross(up).normalized();b=tangent_.cross(a)
        for j in range(nv):
            ang=math.tau*j/nv;verts.append(p+radius*(a*math.cos(ang)+b*math.sin(ang)))
    for i in range(len(points) if loop else len(points)-1):
        n=(i+1)%len(points)
        for j in range(nv):
            k=(j+1)%nv;faces.append([i*nv+j,i*nv+k,n*nv+k,n*nv+j])
    if not loop:faces+=[list(reversed(range(nv))),list(range(len(verts)-nv,len(verts)))]
    return make(name,verts,faces,[k for k in binding for j in range(nv)] if binding else None)

select([rig],rig);bpy.ops.object.mode_set(mode='EDIT')
eb=rig.data.edit_bones
def marker(name,pt,parent):
    b=eb.get(name) or eb.new(name)
    b.use_connect=False;b.parent=eb[parent];b.head=pt;b.tail=pt+Vector((0,0,1.5));b.roll=0
    return b
marker('compound_draw_end',DRAW,'bow_body_root')
marker('preview_nock',BRACE,'bow_body_root')
for i,g in enumerate(GUIDES):marker('guide_'+str(i),g,'bow_body_root')
rest_tips={};ends={}
for side,sign in [('upper',1),('lower',-1)]:
    for suffix,angle in [('_01',6),('_02',4),('_cam',96)]:
        ctrl=eb[side+suffix];goal=eb['draw_'+side+suffix]
        goal.matrix=Matrix.Translation(ctrl.head)@rotate_y(-sign*angle)@ctrl.matrix.to_3x3().to_4x4()
        goal.length=ctrl.length
    cam=side+'_cam';hub=eb[cam].head.copy()
    c,u,v=outline(side)
    for k,pos in [('center',c),('u',c+u),('v',c+v)]:marker(side+'_rim_'+k,pos,cam)
    tip=tangent(c,u,v,BRACE)
    marker(side+'_tip',tip,side+'_02');marker('draw_'+side+'_tip',tip,side+'_02')
    rest_tips[side]=tip
    for i,r in enumerate(REELS):
        cen=hub+Vector((0,GUIDES[i].y,0))
        pos=tangent(cen,u.normalized()*r,v.normalized()*r,GUIDES[i])
        ends[side,i]=pos;marker(side+'_cable'+str(i),pos,cam)
bpy.ops.object.mode_set(mode='OBJECT')
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
for side in SIDES:
    camname=side+'_cam';cam=sc.objects[side.title()+'Cam'];c,u,v=outline(side)
    # Clip only material protruding past the original wheel outline (old welded cord ends).
    bm=bmesh.new();bm.from_mesh(cam.data)
    for j in range(72):
        t=math.tau*j/72;pt=c+math.cos(t)*u+math.sin(t)*v
        n=(math.cos(t)*u/u.length_squared+math.sin(t)*v/v.length_squared).normalized()
        cut=bmesh.ops.bisect_plane(bm,geom=[*bm.verts,*bm.edges,*bm.faces],dist=.00001,
              plane_co=pt+n*.035,plane_no=n,clear_outer=True)
        border=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_valid and e.is_boundary]
        if border:bmesh.ops.holes_fill(bm,edges=border,sides=0)
    bm.to_mesh(cam.data);bm.free();cam.data.update()
    # New boundary vertices are also rigidly owned by this single wheel.
    group=cam.vertex_groups[camname];group.add(list(range(len(cam.data.vertices))),1.,'REPLACE')
    pieces=[]
    def orbit(center,a,b):
        return [center+math.cos(i*math.tau/96)*a+math.sin(i*math.tau/96)*b for i in range(96)]
    # A thin dark track bridges the original surface and the moving visual exit.
    pts=orbit(c,u,v);pieces.append(pipe('StringTrack',pts,.105,[camname]*len(pts),True))
    bed=[]
    for point in pts:
        radial=(point-c).normalized()
        for inward,y in ((.01,-.10),(.44,-.25),(.44,.25),(.01,.10)):
            bed.append(point-radial*inward+Vector((0,y,0)))
    strips=[[4*j+k,4*((j+1)%96)+k,4*((j+1)%96)+(k+1)%4,4*j+(k+1)%4]
            for j in range(96) for k in range(4)]
    pieces.append(make('GrooveBed',bed,strips,[camname]*len(bed)))
    hub=rig.data.bones[camname].head_local.copy()
    for i,r in enumerate(REELS):
        cen=hub+Vector((0,GUIDES[i].y,0))
        pts=orbit(cen,u.normalized()*r,v.normalized()*r)
        pieces.append(pipe('CableTrack',pts,.12,[camname]*len(pts),True))
        for j in range(3):
            vdir=(u.normalized()*math.cos(j*math.tau/3)+v.normalized()*math.sin(j*math.tau/3))
            pieces.append(pipe('CableSpoke',[cen,cen+vdir*r],.15,[camname]*2))
    pieces.append(pipe('HubCollar',[hub,hub+Vector((0,GUIDES[-1].y,0))],.46,[camname]*2))
    join(cam,pieces)
guides=[]
for i,g in enumerate(GUIDES):
    pts=[ends['upper',i],g,ends['lower',i]]
    pipe('ControlCable'+str(i+1),pts,.094,['upper_cable'+str(i),'guide_'+str(i),'lower_cable'+str(i)])
    guides.append(pipe('GuideShoe',[g-Vector((0,.16,0)),g+Vector((0,.16,0))],.21))
guides.append(pipe('GuideArm',[Vector((-5.,-.8,9.4)),Vector((-8,-2.8,9.15)),(GUIDES[0]+GUIDES[1])*.5],.19))
# The guide is fixed to the riser, independent of a removable arrow rest.
for ob in guides:
    grp=ob.vertex_groups.new(name='bow_body_root');grp.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
join(sc.objects['Riser'],guides)
# Keep the original rest mechanism; add an open, slightly crowned cradle on its left.
rest_obj=sc.objects['Rest'];extra=[]
extra.append(pipe('SaddleArm',[Vector((-5.85,.2,8.25)),Vector((-6.15,3.65,8.36)),SEAT+Vector((0,0,-.78))],.245))
forward=(SEAT-BRACE.lerp(DRAW,.5));forward.z=0;forward.normalize()
across=Vector((-forward.y,forward.x,0));verts=[];faces=[]
sections=[(-.55,-.15),(0.,0.),(.55,-.15)]
for along,drop in sections:
    for j in range(19):
        a=math.radians(-108+j*216/18)
        for outer in (False,True):
            r=.30+(1.-math.cos(a))*.20+(.20 if outer else 0)
            verts.append(SEAT+along*forward+r*math.sin(a)*across+Vector((0,0,drop-r*math.cos(a))))
for row in range(2):
    for j in range(18):
        k=row*38+j*2
        faces.extend([[k,k+38,k+40,k+2],[k+1,k+3,k+41,k+39]])
for row in (0,2):
    for j in range(18):
        k=row*38+j*2;faces.append([k,k+1,k+3,k+2])
for j in (0,18):
    for row in (0,1):
        k=row*38+j*2;faces.append([k,k+38,k+39,k+1])
extra.append(make('Saddle',verts,faces));join(rest_obj,extra)
# Export the same assembly and material-slot names used by every existing item.
def export(name,objs):
    select(objs,objs[0])
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bodies=[sc.objects[n] for n in ('Riser','UpperLimb','LowerLimb','UpperCam','LowerCam','ControlCable1','ControlCable2')]
copies=[]
for ob in bodies:
    dup=ob.copy();dup.data=ob.data.copy();sc.collection.objects.link(dup);copies.append(dup)
body=join(copies[0],copies[1:]);body.name='SK_Frontier_Assembly'
export(body.name,[rig,body]);bpy.data.objects.remove(body,do_unlink=True)
export('SM_Frontier_Rest',[rest_obj])
for side in SIDES:
    pipe('MainString_'+side,[rest_tips[side],BRACE],.09,[side+'_tip','preview_nock'])
animate(rig,sc)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'FrontierCompoundBow_R2.blend'))
def ue(v):return [round(v.x,5),round(-v.y,5),round(v.z,5)]
(P/'anchors.json').write_text(json.dumps({'upper':ue(rest_tips['upper']),'lower':ue(rest_tips['lower']),
       'rest':ue(SEAT),'brace':ue(BRACE),'draw':ue(DRAW)},indent=2),encoding='utf8')
