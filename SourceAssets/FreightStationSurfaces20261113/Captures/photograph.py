"""Photograph the published station in its isolated render host. No map saves."""
from pathlib import Path
import json,runpy,time,traceback
import unreal as u
OUT=Path(__file__).resolve().parent
SURFACE=OUT.parent
BASE=SURFACE.parent/'FreightCameraMatch20261113'
ctx=runpy.run_path(str(BASE/'capture.py'))
def main():
    if Path(u.Paths.project_dir()).resolve()!=(SURFACE/'RenderHost').resolve():raise RuntimeError('Unexpected render host')
    world,_=ctx['open_world']()
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    fixed=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='REF_02_CartSurface')
    # Keep the cart's saved transform, FOV, previous 1024-square format and capture settings exactly.
    standard=ctx['take']
    standard.__globals__.update(ROOT=OUT,LABELS=('REF_02_CartSurface',))
    standard(world,'station')
    # Same project capture routine and camera effects with a landscape render target.
    source=(BASE/'capture.py').read_text('utf8').split('def open_world():')[0]
    source=source.replace('dims=1024','width,height=1920,1200').replace('world,dims,dims,','world,width,height,').replace('dims//2,dims//2','width//2,height//2').replace("'frame_width':dims","'frame_width':width,'frame_height':height")
    wide={'__file__':str(BASE/'capture.py')}
    exec(compile(source,'station_wide_capture','exec'),wide)
    wide['ROOT']=OUT
    def views(listing,stage):
        cameras=[]
        try:
            for label,eye,target,fov in listing:
                pos=u.Vector(*eye);rot=u.MathLibrary.find_look_at_rotation(pos,u.Vector(*target))
                a=api.spawn_actor_from_class(u.CameraActor,pos,rot,transient=True)
                a.set_actor_label(label)
                camera=a.get_component_by_class(u.CameraComponent)
                camera.set_editor_property('post_process_settings',fixed.get_component_by_class(u.CameraComponent).get_editor_property('post_process_settings').copy())
                camera.set_editor_property('field_of_view',fov);cameras.append(a)
            wide['LABELS']=tuple(r[0] for r in listing)
            return wide['take'](world,stage)
        finally:
            for a in cameras:api.destroy_actor(a)
    views([('Concourse',[6430,-2350,310],[9400,-1390,167],82),('OppositePlatform',[8820,-2635,161],[7560,-2910,128],74)],'wide')
    (OUT/'ready.json').write_text(json.dumps({'world':world.get_path_name(),'mode':'offscreen'}),'utf8')
    for idx in range(1,9):
        job=OUT/f'framing-{idx}.json';deadline=time.monotonic()+500
        while not job.exists() and time.monotonic()<deadline:time.sleep(.4)
        if not job.exists():break
        request=json.loads(job.read_text('utf-8-sig'))
        if request.get('finish'):break
        try:views(request['views'],request['stage'])
        except Exception:(OUT/f'framing-{idx}-error.txt').write_text(traceback.format_exc(),'utf8')
try:main()
except Exception:
    (OUT/'capture-error.txt').write_text(traceback.format_exc(),'utf8')
    raise
