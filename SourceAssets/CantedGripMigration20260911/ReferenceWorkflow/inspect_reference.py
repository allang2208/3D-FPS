import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent
BASE=O.parent
def setup_render(r, G, label, close=False):
    s=bpy.context.scene
    for ob in s.objects:
        ob.hide_render=not (ob.name.startswith(('VG_','PH_')) or (ob.type=='MESH' and ob.parent==r and not ob.name.startswith('Drum')))
    d=bpy.data.cameras.new('ErgonomicReview');c=bpy.data.objects.new('ErgonomicReview',d);s.collection.objects.link(c);s.camera=c
    d.type='ORTHO';d.clip_start=.001
    for pos in [(-.6,-.2,.9),(.8,.6,.7)]:
        ld=bpy.data.lights.new('Review','AREA');ld.energy=65;ld.size=1;l=bpy.data.objects.new('Review',ld);s.collection.objects.link(l);l.location=pos;l.rotation_euler=(G.translation-l.location).to_track_quat('-Z','Y').to_euler()
    s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100
    views=[('arm',(-.15,0,-.10),(-.05,-.8,.22),.62),('palm',(0,0,-.035),(0,-.4,.01),.25),('front',(0,0,-.035),(.4,0,.01),.25)]
    for view,center,offset,scale in views:
        focus=G@Vector(center);c.location=focus+G.to_3x3()@Vector(offset);c.rotation_euler=(focus-c.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale
        s.render.filepath=str(O/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    report={}
    sources=[('original_idle',BASE/'M4ContactImpact20260910/M4_Hand_MAT_Editable.blend','M4_idle',0,BASE/'VerticalGripRaised20260911/vertical'),
             ('original_reload146',BASE/'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend','M4_reload',146,BASE/'VerticalGripRaised20260911/vertical'),
             ('before_vertical',BASE/'VerticalGripRaised20260911/vertical/A_M4_Vertical_idle.blend','A_M4_Vertical_idle',0,BASE/'VerticalGripRaised20260911/vertical'),
             ('before_prism',BASE/'PrismGripContact20260911/prism/A_M4_Prism_idle.blend','A_M4_Prism_idle',0,BASE/'PrismGripContact20260911/prism')]
    for label,path,action,frame,config in sources:
        bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
        fit=json.loads((config/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);I=G.inverted()
        names=[b.name for b in r.pose.bones if b.name.endswith('_l') or b.name=='WPN_root']
        report[label]={'action':action,'frame':frame,'action_range':list(a.frame_range),'fps':s.render.fps,'rig_world':[list(x) for x in r.matrix_world], 'G':[list(x) for x in G],
            'bones':{n:{'pose':[list(x) for x in r.pose.bones[n].matrix],'basis':[list(x) for x in r.pose.bones[n].matrix_basis],'rest':[list(x) for x in r.data.bones[n].matrix_local],'parent':r.data.bones[n].parent.name if r.data.bones[n].parent else None} for n in names}}
        setup_render(r,G,label)
        print('REFERENCE_DONE',label,flush=True)
    (O/'references.json').write_text(json.dumps(report,indent=2))
