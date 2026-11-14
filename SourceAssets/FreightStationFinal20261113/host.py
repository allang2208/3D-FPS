from pathlib import Path
import json,runpy,time,traceback
import unreal as u
R=Path(__file__).resolve().parent
source=R.parent/'FreightCameraMatch20261113/capture.py'
code=source.read_text('utf8').split('def main():')[0].replace('dims=1024','width,height=1920,1200').replace('world,dims,dims,','world,width,height,').replace('dims//2,dims//2','width//2,height//2').replace("'frame_width':dims","'frame_width':width,'frame_height':height")
ctx={'__file__':str(source)};exec(compile(code,'fixed_capture','exec'),ctx)
ctx.update(ROOT=R)
if Path(u.Paths.project_dir()).resolve()!=(R/'RenderHost').resolve():raise RuntimeError('Wrong host')
w,_=ctx['open_world']()
api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def photo(stage):
    specs=json.loads((R.parent/'FreightStationSurfaces20261113/Captures/review-capture.json').read_text('utf8'))
    fixed=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.CameraActor) if a.get_actor_label()=='REF_02_CartSurface')
    made=[]
    try:
        for s in specs:
            a=api.spawn_actor_from_class(u.CameraActor,u.Vector(*s['eye']),u.Rotator(roll=s['rotation'][0],pitch=s['rotation'][1],yaw=s['rotation'][2]),transient=True)
            a.set_actor_label(s['file'][7:-4]);c=a.get_component_by_class(u.CameraComponent)
            c.set_editor_property('post_process_settings',fixed.get_component_by_class(u.CameraComponent).get_editor_property('post_process_settings').copy())
            c.set_editor_property('field_of_view',s['fov']);made.append(a)
        ctx['LABELS']=tuple(a.get_actor_label() for a in made)+('REF_02_CartSurface',)
        return ctx['take'](w,stage)
    finally:
        for a in made:api.destroy_actor(a)
for i in range(1,21):
    job=R/f'job-{i:02}.json';end=time.monotonic()+3600
    while not job.exists() and time.monotonic()<end:time.sleep(.5)
    if not job.exists():break
    req=json.loads(job.read_text('utf-8-sig'))
    if req.get('finish'):break
    try:
        result={}
        if req.get('script'):result['apply']=runpy.run_path(str(R/req['script']))['apply'](w,req)
        if req.get('save') and not u.EditorLoadingAndSavingUtils.save_map(w,ctx['TARGET']):raise RuntimeError('Save failed')
        if req.get('photo'):result['photo']=photo(req['photo'])
        (R/f'done-{i:02}.json').write_text(json.dumps(result,indent=1),'utf8')
    except Exception:(R/f'error-{i:02}.txt').write_text(traceback.format_exc(),'utf8')
