"""User-requested offline GIF frames from the saved M24 profile data."""
from pathlib import Path
PREVIEW_TASK=Path(__file__).resolve().parent
__file__=str(PREVIEW_TASK/'common.py')
exec(compile(Path(__file__).read_text(),'native preview setup','exec'))
import re,sys
profile_file=PREVIEW_TASK/('candidate_profiles.json.gz' if '--candidate' in sys.argv else 'saved_profiles.json.gz')
D['profiles']=json.load(gzip.open(profile_file,'rt'))
D['clips'].update(json.load(gzip.open(PREVIEW_TASK/'input_clips.json.gz','rt')))
OUTPUT=PREVIEW_TASK/'GIF';OUTPUT.mkdir(exist_ok=True)
header=(PREVIEW_TASK.parent.parent/'Source/FPSGAME/Weapons/M24ReloadTiming.h').read_text()
def constants(name):
    text=re.search(r'constexpr float '+name+r'\[\]\s*=\s*\{([^}]+)',header).group(1)
    return [float(x.strip().removesuffix('f')) for x in text.split(',')]
src=constants('Source');paced=constants('Paced');extra=paced[-1]-src[-1]
def clock(seconds,length):
    t=seconds*30
    if t>=paced[-1]:return min(length*30,t-extra)/30
    i=0
    while i<len(src)-2 and t>paced[i+1]:i+=1
    def slope(k):
        if k in (0,len(src)-1):return 1.
        a=(src[k]-src[k-1])/(paced[k]-paced[k-1]);b=(src[k+1]-src[k])/(paced[k+1]-paced[k])
        return 2*a*b/(a+b)
    span=paced[i+1]-paced[i];u=(t-paced[i])/span
    return ((2*u**3-3*u*u+1)*src[i]+(u**3-2*u*u+u)*span*slope(i)+(-2*u**3+3*u*u)*src[i+1]+(u**3-u*u)*span*slope(i+1))/30

s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=800;s.render.resolution_y=560;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=.4
s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.show_shadows=True;s.display.shading.show_specular_highlight=True
s.display.shading.background_type='WORLD';s.world.color=(.075,.085,.10)
s.display.render_aa='16';s.render.image_settings.file_format='PNG';s.render.film_transparent=False
skin.color=(.67,.45,.31,1)
for name,ob in obs.items():ob.color=(.15,.19,.23,1) if name=='body' else (.28,.34,.39,1)
for ob in s.objects:
    if ob.type=='MESH':ob.hide_render=ob!=skin and ob not in obs.values()
reference_row,_=compose(entry('base','reload'),18/30)
vs,faces=weapon(reference_row,'base')['magazine'];center=Vector(vs[np.unique(np.array(faces).ravel())].mean(0))
root=reference_row['WPN_root'];cam_ref=center+root.to_quaternion()@Vector((.40,-.23,-.16))
target_ref=center+root.to_quaternion()@Vector((0,0,-.055))
cam.data.type='ORTHO';cam.data.ortho_scale=.55;cam.data.clip_start=.001
arm_target_ref=(reference_row['upperarm_l'].translation+reference_row['lowerarm_l'].translation+center*2)/4
arm_cam_ref=arm_target_ref+root.to_quaternion()@Vector((.65,-.4,-.3))

def draw(family,role,time,file,wide=False):
    row,_=compose(entry(family,role),time)
    skin_corrected(row);pose_row(row,'mag10' in family)
    for ob in s.objects:
        if ob.type=='MESH':ob.hide_render=ob!=skin and ob not in obs.values()
    for label,(vs,fs) in weapon(row,family).items():
        ob=obs[label];ob.data.clear_geometry();ob.data.from_pydata(vs.tolist(),[],fs);ob.data.update()
    # Follow the rigid weapon frame; do not chase the palm or hide its drift.
    transform_camera=row['WPN_root']@root.inverted()
    cam.data.ortho_scale=.9 if wide else .55
    cam.location=transform_camera@(arm_cam_ref if wide else cam_ref);target=transform_camera@(arm_target_ref if wide else target_ref)
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update();s.render.filepath=str(file)
    bpy.ops.render.render(write_still=True)

if '--layout' in sys.argv:
    for family in ('base','mag10'):
        for frame in (18,22,38):
            draw(family,'reload',frame/30,OUTPUT/f'layout_{family}_{frame}.png')
            draw(family,'reload',frame/30,OUTPUT/f'layout_{family}_{frame}_arm.png',True)
    print('M24_GIF_LAYOUT_READY',flush=True)
else:
    report={'fps':20,'camera':'weapon-relative oblique close view and left arm overview; offline studio','game_recording':False,'profile_source':profile_file.name,'profiles_sha256':hashlib.sha256(profile_file.read_bytes()).hexdigest(),'timing_header_sha256':hashlib.sha256(header.encode()).hexdigest(),'clips':{}}
    for family,role,wide in [('base','reload',False),('base','reload_empty',False),('mag10','reload',False),('mag10','reload_empty',False),('mag10','reload',True)]:
            key=family+'_'+role+('_arm' if wide else '');folder=OUTPUT/key;folder.mkdir(exist_ok=True)
            length=entry(family,role)['duration'];duration=length+extra/30
            count=math.ceil(duration*20)+1;rows=[]
            for i in range(count):
                t=min(i/20,duration);source_time=clock(t,length)
                draw(family,role,source_time,folder/f'{i:04d}.png',wide)
                rows.append({'frame':i,'runtime_seconds':t,'source_seconds':source_time})
                if i%20==0:print('M24_GIF_FRAME',key,i,count,flush=True)
            report['clips'][key]={'duration':duration,'frames':count,'samples':rows}
            (OUTPUT/'render_receipt.json').write_text(json.dumps(report,indent=2))
    report['complete']=True;(OUTPUT/'render_receipt.json').write_text(json.dumps(report,indent=2))
    print('M24_GIF_RENDER_COMPLETE',flush=True)
