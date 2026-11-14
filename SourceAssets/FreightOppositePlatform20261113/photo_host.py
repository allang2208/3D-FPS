"""Edit the isolated station level and photograph the exact accepted opposite-platform angle."""
from pathlib import Path
import json,runpy,time,traceback
import unreal as u
R=Path(__file__).resolve().parent;S=R.parent/'FreightStationSurfaces20261113'
source=R.parent/'FreightCameraMatch20261113/capture.py'
wide=source.read_text('utf8').split('def main():')[0].replace('dims=1024','width,height=1920,1200').replace('world,dims,dims,','world,width,height,').replace('dims//2,dims//2','width//2,height//2').replace("'frame_width':dims","'frame_width':width,'frame_height':height")
ctx={'__file__':str(source)};exec(compile(wide,'read_station_camera','exec'),ctx)
ctx.update(ROOT=R,LABELS=('PlatformWallAndFloor',))
if Path(u.Paths.project_dir()).resolve()!=(R/'RenderHost').resolve():raise RuntimeError('Wrong render host')
w,_=ctx['open_world']()
api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def photo(stage):
    spec=next(s for s in json.loads((S/'Captures/review-capture.json').read_text('utf8')) if s['file']=='review_PlatformWallAndFloor.png')
    rot=u.Rotator(roll=spec['rotation'][0],pitch=spec['rotation'][1],yaw=spec['rotation'][2])
    cam=api.spawn_actor_from_class(u.CameraActor,u.Vector(*spec['eye']),rot,transient=True)
    try:
        cam.set_actor_label('PlatformWallAndFloor')
        fixed=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.CameraActor) if a.get_actor_label()=='REF_02_CartSurface')
        c=cam.get_component_by_class(u.CameraComponent);c.set_editor_property('post_process_settings',fixed.get_component_by_class(u.CameraComponent).get_editor_property('post_process_settings').copy());c.set_editor_property('field_of_view',spec['fov'])
        return ctx['take'](w,stage)
    finally:api.destroy_actor(cam)
for index in range(1,25):
    job=R/f'job-{index:02}.json';deadline=time.monotonic()+2400
    while not job.exists() and time.monotonic()<deadline:time.sleep(.4)
    if not job.exists():break
    req=json.loads(job.read_text('utf-8-sig'))
    if req.get('finish'):break
    try:
        result={}
        if 'script' in req:result['apply']=runpy.run_path(str(R/req['script']))['apply'](w,req)
        if req.get('save') and not u.EditorLoadingAndSavingUtils.save_map(w,ctx['TARGET']):raise RuntimeError('Cannot save station')
        if req.get('photo'):result['photo']=photo(req['photo'])
        (R/f'done-{index:02}.json').write_text(json.dumps(result,indent=1),'utf8')
    except Exception:(R/f'error-{index:02}.txt').write_text(traceback.format_exc(),'utf8')
