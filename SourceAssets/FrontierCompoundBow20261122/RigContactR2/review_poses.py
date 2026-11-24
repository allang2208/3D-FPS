"""Sample both loaded strands and the actual project wood arrow. Render four locked cameras."""
from pathlib import Path
import bpy,sys,math,os,json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from wheel_geometry import *
out=Path(os.environ['FRONTIER_REVIEW'])
project=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(P/'FrontierCompoundBow_R2.blend'))
sc=bpy.context.scene;rig=sc.objects['Armature']
with bpy.data.libraries.load(str(project/'SourceAssets/DarkBow20260925/ArmsV2/WoodArrow_Editable.blend')) as (a,b):
    b.objects=['SM_Bow_WoodArrow']
arrow=b.objects[0];sc.collection.objects.link(arrow)
# Source is in metres; the runtime stretches only the longitudinal mesh axis.
local=[v.co.copy()*100 for v in arrow.data.vertices]
low=min(v.x for v in local);high=max(v.x for v in local)
for dst,co in zip(arrow.data.vertices,local):
    dst.co=Vector(((co.x-low)*76/(high-low),co.y,co.z))
arrow.data.update();arrow.matrix_world=Matrix.Identity(4);arrow.hide_render=False;arrow.hide_set(False)
def pose(f):
    sc.frame_set(f)
    nock=rig.pose.bones['preview_nock'].head.copy()
    direction=(SEAT-nock).normalized()
    arrow.matrix_world=Matrix.Translation(nock)@Vector((1,0,0)).rotation_difference(direction).to_matrix().to_4x4()
    sc.view_layers[0].update()
    return nock,direction
def contact_layer(name,fr,deps):
    ob=sc.objects[name].evaluated_get(deps)
    return BVHTree.FromObject(ob,deps)
rows=[]
for f in range(1,26):
    n,d=pose(f);deps=bpy.context.evaluated_depsgraph_get()
    trees={name:contact_layer(name,f,deps) for name in ['UpperCam','LowerCam','UpperLimb','LowerLimb','Riser','Rest','ControlCable1','ControlCable2']}
    check={'frame':f,'sides':{},'shaft_hits':[],'strand_hits':[],'rim_joins':[], 'nock':list(n)}
    def test_segment(a,b,skip,until,targets,label,own_wheel=None):
        delta=b-a
        if delta.length<=skip+until:return
        direction=delta.normalized()
        for name in targets:
            distance=skip
            for _ in range(32):
                if distance>=delta.length-until:break
                hit=trees[name].ray_cast(a+direction*distance,direction,delta.length-distance-until)
                if hit[0] is None:break
                distance=(hit[0]-a).length
                # A tangent strand and its rounded track share a small visible junction.
                field='rim_joins' if name==own_wheel and distance<1.75 else label
                check[field].append([name,round(distance,4),list(hit[0])])
                distance+=.005
    for side in SIDES:
        pb=rig.pose.bones
        cam=pb[side+'_cam'];body=cam.matrix @ cam.bone.matrix_local.inverted()
        c,u,v=outline(side);c=body@c;u=body.to_3x3()@u;v=body.to_3x3()@v
        tip=pb[side+'_tip'].head.copy();expect=tangent(c,u,v,n)
        obj=sc.objects['MainString_'+side].evaluated_get(deps)
        rings=[sum((obj.data.vertices[i].co for i in range(start,start+10)),Vector())/10 for start in (0,10)]
        tilt=abs(math.degrees(math.asin(min(1.,abs((body.to_3x3()@Vector((0,1,0))).normalized().z)))))
        check['sides'][side]={'tilt':tilt,'wheel_axle_drift':((body.to_3x3()@Vector((0,1,0)))-Vector((0,1,0))).length,
            'exit_error':(tip-expect).length,'strand_rim_gap':(rings[0]-tip).length,'strand_nock_gap':(rings[1]-n).length,
            'tip':list(tip),'cables':[]}
        test_segment(tip,n,.02,.10,trees.keys(),'strand_hits',side.title()+'Cam')
        for i,r in enumerate(REELS):
            actual=pb[side+'_cable'+str(i)].head.copy()
            center=body@(cam.bone.head_local+Vector((0,GUIDES[i].y,0)))
            reference=tangent(center,u.normalized()*r,v.normalized()*r,GUIDES[i])
            check['sides'][side]['cables'].append({'pos':list(actual),'error':(actual-reference).length})
            targets=[k for k in trees if k!='ControlCable'+str(i+1)]
            test_segment(actual,GUIDES[i],.02,.48,targets,'strand_hits',side.title()+'Cam')
    test_segment(n,n+d*76,.3,.3,trees.keys(),'shaft_hits')
    check['shaft_to_seat']=trees['Rest'].find_nearest(SEAT)[3]
    rows.append(check)
(out/'mesh-contact.json').write_text(json.dumps(rows,indent=1),encoding='utf8')
# Fixed lights, exposure, object origin and camera coordinates across the three states.
sc.world=bpy.data.worlds.new('ReviewStudio');sc.world.use_nodes=True
bg=next(q for q in sc.world.node_tree.nodes if q.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.43,.46,.49,1);bg.inputs['Strength'].default_value=.74
for pos,power,size in [((60,100,125),260000,90),((-55,-85,55),210000,85),((40,22,-76),110000,65)]:
    l=bpy.data.lights.new('Softbox','AREA');l.energy=power;l.size=size
    ob=bpy.data.objects.new('Softbox',l);sc.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True
sc.render.film_transparent=False;sc.render.resolution_percentage=100;sc.render.image_settings.color_mode='RGB'
camdata=bpy.data.cameras.new('ReviewCamera');camdata.type='ORTHO';camdata.clip_end=900
cam=bpy.data.objects.new('ReviewCamera',camdata);sc.collection.objects.link(cam);sc.camera=cam
shots={'assembly':((-.8,0,5),(-.08,1,.06),118,740,760),
       'upper':((-16.5,0,46),(-.18,-1,.17),43,740,390),
       'lower':((-16.5,0,-36),(-.16,-1,-.12),43,740,390),
       'rest':((-6.0,4.6,9.5),(-1,.46,.25),10.5,740,380)}
for f,tag in [(1,'brace'),(13,'half'),(25,'full')]:
    batch=Path(os.environ['FRONTIER_BATCH']) if os.environ.get('FRONTIER_BATCH') else None
    if batch and (batch/'draw-clip-contacts.json').exists():
        # Frame selection uses actual wrist travel, rather than evenly spaced clip time.
        from wheel_geometry import local_from_world
        recording=json.loads((batch/'draw-clip-contacts.json').read_bytes())
        def blender_v(p):return Vector((p[0],-p[1],p[2]))
        first=blender_v(recording[0]['nock']);last=blender_v(recording[-1]['nock'])
        step={'brace':0.,'half':.5,'full':1.}[tag];wanted=first.lerp(last,step)
        sample=min(recording,key=lambda row:(blender_v(row['nock'])-wanted).length_squared)
        nock=blender_v(sample['nock'])
        progress=max(0.,min(1.,(nock-BRACE).dot(DRAW-BRACE)/(DRAW-BRACE).length_squared))
        frame=1+24*progress;sc.frame_set(int(frame),subframe=frame-int(frame))
        for name,point in [('preview_nock',nock),('upper_tip',blender_v(sample['upper'])),('lower_tip',blender_v(sample['lower']))]:
            rig.pose.bones[name].location=local_from_world(rig,name,point)
        arrow.matrix_world=Matrix.Translation(nock)@Vector((1,0,0)).rotation_difference((SEAT-nock).normalized()).to_matrix().to_4x4()
        sc.view_layers[0].update()
        errors=[(rig.pose.bones[name].head-point).length for name,point in [
            ('preview_nock',nock),('upper_tip',blender_v(sample['upper'])),('lower_tip',blender_v(sample['lower']))]]
        if max(errors)>.002:raise RuntimeError('Presentation diverged from registered component '+str(errors))
        (out/(tag+'_native.json')).write_text(json.dumps(sample,indent=1),encoding='utf8')
    else:pose(f)
    for shot,(target,view,scale,w,h) in shots.items():
        target=Vector(target);view=Vector(view).normalized()
        cam.location=target+view*180;cam.rotation_euler=(-view).to_track_quat('-Z','Y').to_euler()
        camdata.ortho_scale=scale;sc.render.resolution_x=w;sc.render.resolution_y=h
        sc.render.filepath=str(out/(tag+'_'+shot+'.png'));bpy.ops.render.render(write_still=True)
