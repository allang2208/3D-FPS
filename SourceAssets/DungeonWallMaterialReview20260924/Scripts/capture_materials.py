"""Temporary UE close-up inspection of existing wall materials; no asset saves."""
import json,time
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Images';OUT.mkdir(parents=True,exist_ok=True)
STATE=ROOT/'Receipts/capture-state.json'
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve active game; no diagnostic actors created')
world=UE.get_editor_world()
if getattr(u,'_wall_material_review_job',None):raise RuntimeError('Owned inspection already running')
MATERIALS=[('concrete','/Game/Dungeons/AtmosphereV2/Materials/M_Concrete'),
           ('mortar','/Game/Dungeons/WallDamage20260923/Materials/MI_FabExposedBed'),
           ('fab_section','/Game/Dungeons/WallDamage20260923/Materials/MI_FabBrokenConcrete')]

class Review:
    def __init__(self):
        self.actors=[];self.rt=None;self.handle=None;self.index=0;self.shots=[]
        self.write('preparing')
    def write(self,status,error=None):
        STATE.write_text(json.dumps({'status':status,'error':error,'shots':self.shots,
            'kind':'Actual UE materials on temporary 200cm plane, fixed neutral grazing lights; not a gameplay screenshot'},indent=2))
    def actor(self,cls,pos,rot=u.Rotator()):
        a=AA.spawn_actor_from_class(cls,pos,rot,transient=True)
        a.set_actor_label('Temporary_WallMaterialReview');self.actors.append(a);return a
    def setup(self):
        self.center=u.Vector(0,0,-50000)
        self.plane=self.actor(u.DynamicMeshActor,self.center,u.Rotator(0,0,90))
        self.mc=self.plane.get_dynamic_mesh_component()
        mesh=self.mc.get_dynamic_mesh()
        u.GeometryScript_Primitives.append_rectangle_xy(mesh,u.GeometryScriptPrimitiveOptions(),u.Transform(),200,200)
        self.mc.set_editor_property('lighting_channels',u.LightingChannels(channel0=False,channel1=True,channel2=False))
        self.normal=self.plane.get_actor_up_vector();self.axis_u=self.plane.get_actor_forward_vector();self.axis_v=self.plane.get_actor_right_vector()
        for offset,lumens in [((80,160,65),800),((170,-100,20),200)]:
            pos=self.center+self.normal*offset[0]+self.axis_u*offset[1]+self.axis_v*offset[2]
            light=self.actor(u.RectLight,pos,u.MathLibrary.find_look_at_rotation(pos,self.center))
            c=light.get_component_by_class(u.RectLightComponent)
            c.set_editor_property('lighting_channels',u.LightingChannels(channel0=False,channel1=True,channel2=False))
            c.set_editor_property('intensity',lumens);c.set_editor_property('attenuation_radius',1000)
            c.set_editor_property('source_width',40);c.set_editor_property('source_height',40)
        self.capture=self.actor(u.SceneCapture2D,self.center)
        self.cc=self.capture.get_component_by_class(u.SceneCaptureComponent2D)
        self.rt=u.RenderingLibrary.create_render_target2d(world,1200,1200,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB,u.LinearColor(0,0,0,1),False)
        self.cc.texture_target=self.rt;self.cc.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        self.cc.capture_every_frame=False;self.cc.capture_on_movement=False;self.cc.always_persist_rendering_state=True
        self.cc.primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
        self.cc.show_only_actor_components(self.plane);self.cc.fov_angle=55
        pp=self.cc.get_editor_property('post_process_settings')
        for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),
                    ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),
                    ('override_auto_exposure_bias',True),('auto_exposure_bias',-8.0),
                    ('override_motion_blur_amount',True),('motion_blur_amount',0.0),
                    ('override_dynamic_global_illumination_method',True),('dynamic_global_illumination_method',u.DynamicGlobalIlluminationMethod.NONE),
                    ('override_reflection_method',True),('reflection_method',u.ReflectionMethod.NONE)]:pp.set_editor_property(k,v)
        self.cc.set_editor_property('post_process_settings',pp)
        self.prepare();self.handle=u.register_slate_post_tick_callback(self.tick)
    def prepare(self):
        name,path=MATERIALS[self.index//2]
        mat=u.load_asset(path);self.mc.set_material(0,mat)
        distance=150 if self.index%2==0 else 55
        pos=self.center+self.normal*distance+self.axis_u*(distance*.5)+self.axis_v*5
        self.capture.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,self.center),False,True)
        self.started=time.monotonic();self.frames=0;self.write('running')
    def finish(self,status,error=None):
        if self.handle:u.unregister_slate_post_tick_callback(self.handle);self.handle=None
        for actor in reversed(self.actors):AA.destroy_actor(actor)
        self.actors=[]
        if self.rt:u.RenderingLibrary.release_render_target2d(self.rt);self.rt=None
        self.write(status,error);u._wall_material_review_job=None
        print('WALL_REVIEW_'+status.upper(),error or '',flush=True)
    def tick(self,delta):
        try:
            if UE.get_game_world() or UE.get_editor_world()!=world:raise RuntimeError('User changed editor/game state; cleaned up review')
            self.cc.capture_scene();self.frames+=1
            if self.frames<12 or time.monotonic()-self.started<3:return
            name,path=MATERIALS[self.index//2];view='150cm' if self.index%2==0 else '55cm'
            file=OUT/(name+'_'+view+'.png')
            u.RenderingLibrary.export_render_target(world,self.rt,str(OUT),file.name)
            if not file.exists():raise RuntimeError('No capture output')
            self.shots.append({'file':str(file),'material':path,'perpendicular_distance_cm':150 if self.index%2==0 else 55})
            self.index+=1
            if self.index==6:self.finish('complete')
            else:self.prepare()
        except Exception as e:self.finish('failed',str(e))

job=Review();u._wall_material_review_job=job
try:job.setup()
except Exception as e:job.finish('failed',str(e));raise
print('WALL_REVIEW_CAPTURE_STARTED',flush=True)
