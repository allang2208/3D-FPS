"""Photograph the actual map with its saved cameras and post-process settings."""
from pathlib import Path
import json,time,uuid,traceback,runpy
import unreal as u
ROOT=Path(__file__).resolve().parent
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
LABELS=('REF_01_PackingSurface','REF_02_CartSurface')
def take(world,stage):
    if stage=='before' and (ROOT/'before-capture.json').exists():
        saved=json.loads((ROOT/'before-capture.json').read_text('utf8'))
        if saved and all((ROOT/row['file']).is_file() for row in saved):return saved
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    byname={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    dims=1024
    results=[]
    for camera_name in LABELS:
        source=byname[camera_name]; loc=source.get_actor_location(); rot=source.get_actor_rotation()
        origin=source.get_component_by_class(u.CameraComponent)
        capture=actors.spawn_actor_from_class(u.SceneCapture2D,loc,rot,transient=True)
        rt=None
        try:
            c=capture.capture_component2d
            c.capture_every_frame=False;c.capture_on_movement=False;c.always_persist_rendering_state=True
            rt=u.RenderingLibrary.create_render_target2d(world,dims,dims,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB,u.LinearColor(0.,0.,0.,1.),False)
            c.texture_target=rt;c.fov_angle=origin.field_of_view;c.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
            for k in ['scene_capture_cache_resolution_scale']:
                try:c.set_editor_property(k,1.)
                except Exception:pass
            pp=origin.get_editor_property('post_process_settings').copy()
            for k,v in [('override_dynamic_global_illumination_method',True),('dynamic_global_illumination_method',u.DynamicGlobalIlluminationMethod.LUMEN),('override_reflection_method',True),('reflection_method',u.ReflectionMethod.LUMEN),('override_motion_blur_amount',True),('motion_blur_amount',0.)]:
                pp.set_editor_property(k,v)
            c.set_editor_property('post_process_settings',pp);c.set_editor_property('post_process_blend_weight',1.)
            # Render-side streaming and shader warm-up. No generated cubemap is saved.
            cube=u.ApartmentExteriorAuthoringTools.bake_city_reflection(world,[byname['StationWorkshop_11_SM_SW_RepairCart']],'/Game/SceneTests/FreightMatchTransient/T_'+uuid.uuid4().hex,loc,64)
            if not cube:raise RuntimeError('Renderer warm-up failed')
            for i in range(32):
                c.capture_scene()
                u.RenderingLibrary.read_render_target_raw_pixel(world,rt,dims//2,dims//2,False)
            outfile=stage+'_'+camera_name+'.png'
            u.RenderingLibrary.export_render_target(world,rt,str(ROOT),outfile)
            if (ROOT/outfile).stat().st_size<1000:raise RuntimeError('Screenshot not written')
            results.append({'file':outfile,'eye':loc.to_tuple(),'rotation':rot.to_tuple(),'fov':c.fov_angle,'frame_width':dims})
        finally:
            actors.destroy_actor(capture)
            if rt:u.RenderingLibrary.release_render_target2d(rt)
    (ROOT/(stage+'-capture.json')).write_text(json.dumps(results,indent=2),encoding='utf8')
    return results
def open_world():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Active gameplay in this editor')
    w=editor.get_editor_world() if editor else None
    previous=w.get_path_name().split('.')[0] if w else ''
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if previous!=TARGET and dirty:raise RuntimeError('Active editor has unsaved level; use isolated read-only renderer')
    if previous!=TARGET:w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not w or w.get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Map not available')
    return w,previous
def main():
    world,prior=open_world()
    try:
        take(world,'before')
        if Path(u.Paths.project_dir()).resolve() == (ROOT/'RenderHost').resolve():
            started=time.monotonic()
            for step in range(1,20):
                job=ROOT/('request-%02d.json'%step)
                while not job.exists():
                    if time.monotonic()-started>2400:return
                    time.sleep(.5)
                row=json.loads(job.read_text('utf-8-sig'));started=time.monotonic()
                if row.get('action')=='finish':return
                try:
                    runpy.run_path(str(ROOT/row['script']))['run'](world,row)
                    if row.get('capture'):take(world,row['capture'])
                    if row.get('save'):
                        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Private map save failed')
                    (ROOT/('done-%02d.json'%step)).write_text(json.dumps(row),encoding='utf8')
                except Exception:(ROOT/('error-%02d.txt'%step)).write_text(traceback.format_exc(),encoding='utf8')
    finally:
        if prior and prior!=TARGET and not prior.startswith('/Temp/'):u.EditorLoadingAndSavingUtils.load_map(prior)
if __name__=='__main__':
    try:main()
    except Exception:
        (ROOT/'capture-error.txt').write_text(traceback.format_exc(),encoding='utf8');raise
