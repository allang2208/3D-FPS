"""Scoped on/off diagnosis requested for persistent Witch spawn slowdown.
Owns one temporary actor and ends only the PIE session it started. No asset saves.
"""
import unreal as u,json,time,statistics,traceback
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Revision06')
STAGES=['original','budget_4_6_1','no_ccd','cloth_off','cloth_off_flat_material','restored']

class Capture:
    def __init__(self,label):
        self.label=label;self.actor=None;self.mesh=None;self.interactor=None;self.index=-1
        self.handle=None;self.started=time.perf_counter();self.since=self.started;self.samples=[];self.results=[]
        self.owned_play=False;self.materials=[];self.original=None;self.error=None
        self.requested_spawn=False;self.previous_tick=self.started;self.world=None;self.background_setting=None;self.travel_requested=False
    def start(self):
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if world:raise RuntimeError('An existing play session is active; left untouched')
        settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
        self.background_setting=settings.get_editor_property('bThrottleCPUWhenNotForeground')
        settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
        self.owned_play=True
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        self.handle=u.register_slate_post_tick_callback(self.tick)
        print('Witch cloth capture scheduled; six scoped stages, no asset changes')
    def finish(self):
        if self.handle:u.unregister_slate_post_tick_callback(self.handle);self.handle=None
        if self.actor:
            try:self.actor.destroy_actor()
            except Exception:pass
        active=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if self.owned_play and active and active==self.world:u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        if self.background_setting is not None:u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')).set_editor_property('bThrottleCPUWhenNotForeground',self.background_setting)
        report={'label':self.label,'map':getattr(self,'map',None),'scenario':'One temporary Witch, fixed location/idle, 2 s settling + 5 s sampling per stage; unchanged camera, resolution and scalability','metrics':'Slate frame interval and Chaos interactor simulation time in ms; editor PIE, not packaged FPS','results':self.results,'error':self.error}
        (ROOT/('performance_'+self.label+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('WITCH_CLOTH_PROFILE '+json.dumps(report))
    def stage(self):
        name=STAGES[self.index];m=self.mesh;it=self.interactor
        m.set_editor_property('disable_cloth_simulation',name in ('cloth_off','cloth_off_flat_material'))
        for i,mat in enumerate(self.materials):m.set_material(i,u.load_asset('/Engine/EngineMaterials/DefaultMaterial') if name=='cloth_off_flat_material' else mat)
        if name in ('budget_4_6_1','no_ccd'):
            it=m.get_clothing_simulation_interactor();self.interactor=it
            it.set_num_iterations(8 if name=='restored' else 4);it.set_max_num_iterations(16 if name=='restored' else 6)
            it.set_num_substeps(3 if name=='restored' else 1)
            for c in self.mesh.get_editor_property('skeletal_mesh_asset').get_editor_property('mesh_clothing_assets'):
                ci=u.ChaosClothingInteractor.cast(it.get_clothing_interactor(c.get_name()))
                if ci:ci.set_collision(1.1,.2,name!='no_ccd',.45)
        m.force_cloth_next_update_teleport_and_reset()
        self.since=time.perf_counter();self.samples=[]
    def tick(self,dt):
        try:
            now=time.perf_counter();wall_dt=now-self.previous_tick;self.previous_tick=now
            if now-self.started>150:raise RuntimeError('Capture timeout')
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if self.world and world!=self.world:raise RuntimeError('Capture world ended or changed; no other session was altered')
            if not world:return
            if self.world is None:
                # Travel only this owned PIE; keep the user's editor map intact.
                if 'DayNight_Lighting' not in world.get_name():
                    if not self.travel_requested:
                        self.travel_requested=True;u.GameplayStatics.open_level(world,'/Game/GameMaps/DayNight_Lighting')
                    return
                self.world=world
            if self.actor is None:
                player=u.GameplayStatics.get_player_pawn(world,0)
                if not player:return
                if not self.requested_spawn:
                    if u.GameplayStatics.get_all_actors_of_class(world,u.WitchRebuiltMonster):raise RuntimeError('Unexpected pre-existing Witch; capture left actors untouched')
                    self.requested_spawn=True
                    u.SystemLibrary.execute_console_command(world,'summon FPSGAME.WitchRebuiltMonster',u.GameplayStatics.get_player_controller(world,0))
                    return
                found=u.GameplayStatics.get_all_actors_of_class(world,u.WitchRebuiltMonster)
                if not found:return
                self.actor=found[0]
                self.actor.set_actor_tick_enabled(False)
                movement=self.actor.get_component_by_class(u.CharacterMovementComponent);movement.disable_movement()
                controller=self.actor.get_controller()
                if controller:controller.set_actor_tick_enabled(False);controller.stop_movement()
                self.mesh=self.actor.get_component_by_class(u.SkeletalMeshComponent)
                self.interactor=self.mesh.get_clothing_simulation_interactor()
                self.materials=[self.mesh.get_material(i) for i in range(self.mesh.get_num_materials())]
                self.map=world.get_path_name();self.since=now
                return
            if self.original is None:
                if now-self.since<4:return
                it=self.interactor
                self.original={'iterations':it.get_num_iterations(),'substeps':it.get_num_substeps(),'dynamic_particles':it.get_num_dynamic_particles(),'kinematic_particles':it.get_num_kinematic_particles()}
                self.index=0;self.stage();return
            elapsed=now-self.since
            if not STAGES[self.index].startswith('cloth_off'):self.interactor=self.mesh.get_clothing_simulation_interactor()
            if elapsed>=2:self.samples.append({'frame_ms':wall_dt*1000,'cloth_ms':0. if STAGES[self.index].startswith('cloth_off') else self.interactor.get_simulation_time()})
            if elapsed<7:return
            row={'stage':STAGES[self.index],'frames':len(self.samples),'initial_solver':self.original,'solver':None if STAGES[self.index].startswith('cloth_off') else {'iterations':self.interactor.get_num_iterations(),'substeps':self.interactor.get_num_substeps()}}
            for key in ('frame_ms','cloth_ms'):
                values=sorted(x[key] for x in self.samples)
                row[key]={'median':statistics.median(values),'p95':values[int((len(values)-1)*.95)],'max':max(values)}
            self.results.append(row);self.index+=1
            if self.index==len(STAGES):self.finish()
            else:self.stage()
        except Exception:
            self.error=traceback.format_exc();self.finish()

def start(label='before'):
    global capture
    capture=Capture(label);capture.start()
