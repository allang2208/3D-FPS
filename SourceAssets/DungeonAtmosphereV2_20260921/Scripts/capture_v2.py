"""User-requested real UE scene captures. No generated/repainted preview images.

The PowerShell wrapper retains the project bridge gate until this finite capture
job ends, while Slate ticks advance real rendering and Lumen history.
"""
import json
import time
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
OUT=Path('D:/FPS3D/FPSGAME/Docs/Gameplay/Previews/DungeonAtmosphereV2_20260921')
OUT.mkdir(parents=True,exist_ok=True)
STATE=ROOT/'Receipts/capture-state.json'
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
VIEWS=[
    ('01_corridor',[180,-210,165],[2050,-210,175],82),
    ('02_workshop',[475,-177,165],[685,220,150],78),
    ('03_machine_bay',[835,-165,165],[1105,-670,180],78),
    ('04_ruin_breach',[1760,-155,165],[1850,-900,192],84),
    ('05_turn_and_steps',[2350,-210,168],[2400,-1110,208],80),
]
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=UE.get_editor_world()
if UE.get_game_world():raise RuntimeError('Gameplay active; capture job did not alter it')
if world.get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Target dungeon is not loaded')
old=getattr(u,'_dungeon_v2_capture_job',None)
if old:
    if old.handle:raise RuntimeError('An owned capture job is still active')
    # Resume after the prior release API signature error, whose callback stopped.
    if old.actor:AA.destroy_actor(old.actor)
    if old.rt:u.RenderingLibrary.release_render_target2d(old.rt)
    u._dungeon_v2_capture_job=None

class CaptureJob:
    def __init__(self):
        self.index=0;self.actor=None;self.rt=None;self.handle=None;self.shots=[]
        self.write('running');self.prepare()
    def write(self,status,error=None):
        STATE.write_text(json.dumps({'status':status,'map':TARGET,'shots':self.shots,'error':error,
            'kind':'UE SceneCapture2D, actual saved level materials/lights, player-height cameras',
            'gameplay_test':False},indent=2),encoding='utf-8')
    def release_view(self):
        if self.actor:AA.destroy_actor(self.actor);self.actor=None
        if self.rt:u.RenderingLibrary.release_render_target2d(self.rt);self.rt=None
    def prepare(self):
        name,pos,target,fov=VIEWS[self.index]
        self.actor=AA.spawn_actor_from_class(u.SceneCapture2D,u.Vector(*pos),u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),transient=True)
        self.actor.set_actor_label('DGN_AV2_TransientCapture_'+name)
        self.c=self.actor.get_component_by_class(u.SceneCaptureComponent2D)
        self.rt=u.RenderingLibrary.create_render_target2d(world,1920,1080,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB,u.LinearColor(0,0,0,1),False)
        self.c.texture_target=self.rt;self.c.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        self.c.fov_angle=fov;self.c.capture_every_frame=False;self.c.capture_on_movement=False
        self.c.always_persist_rendering_state=True
        settings=self.c.get_editor_property('post_process_settings')
        for key,value in [('override_dynamic_global_illumination_method',True),('dynamic_global_illumination_method',u.DynamicGlobalIlluminationMethod.LUMEN),
            ('override_reflection_method',True),('reflection_method',u.ReflectionMethod.LUMEN),
            ('override_motion_blur_amount',True),('motion_blur_amount',0.0)]:settings.set_editor_property(key,value)
        self.c.set_editor_property('post_process_settings',settings)
        self.started=time.monotonic();self.frames=0
    def end(self,status,error=None):
        if self.handle:u.unregister_slate_post_tick_callback(self.handle);self.handle=None
        try:self.release_view()
        finally:
            self.write(status,error);u._dungeon_v2_capture_job=None
        print('V2_CAPTURE_'+status.upper())
    def tick(self,delta):
        try:
            if UE.get_editor_world()!=world:raise RuntimeError('Current world changed during capture')
            self.c.capture_scene();self.frames+=1
            if self.frames<24 or time.monotonic()-self.started<7: return
            name,pos,target,fov=VIEWS[self.index];filename=name+'.png'
            u.RenderingLibrary.export_render_target(world,self.rt,str(OUT),filename)
            path=OUT/filename
            if not path.exists() or path.stat().st_size<10000:raise RuntimeError('Capture did not produce an image: '+filename)
            self.shots.append({'file':str(path),'position_ue_cm':pos,'look_at_ue_cm':target,'fov':fov,'resolution':[1920,1080]})
            self.write('running');self.release_view();self.index+=1
            if self.index==len(VIEWS):self.end('complete')
            else:self.prepare()
        except Exception as exc:self.end('failed',str(exc))

try:
    job=CaptureJob();u._dungeon_v2_capture_job=job
    job.handle=u.register_slate_post_tick_callback(job.tick)
except Exception as exc:
    STATE.write_text(json.dumps({'status':'failed','error':str(exc)},indent=2),encoding='utf-8')
    raise
print('V2_CAPTURE_STARTED')
