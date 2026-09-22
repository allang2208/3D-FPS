"""User-requested review: temporary PIE, fabric A/B and one ragdoll sample.

No assets or user settings are saved. Only the PIE and actor created here are ended.
"""
import json
import statistics
import time
import traceback
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Revision11')
STAGES = ('cloth_on', 'cloth_off', 'cloth_off_flat', 'cloth_restored', 'death')
PAIRS = (('thigh_l', 'calf_l'), ('calf_l', 'foot_l'), ('thigh_r', 'calf_r'),
         ('calf_r', 'foot_r'), ('upperarm_r', 'lowerarm_r'), ('lowerarm_r', 'hand_r'))


class Capture:
    def __init__(self):
        self.world = self.actor = self.mesh = self.handle = None
        self.travel = self.spawn = False
        self.started = self.previous = time.perf_counter()
        self.stage_index = -1
        self.samples = []
        self.report = {'scenario': 'Windows Editor PIE / DayNight_Lighting, one idle Witch, fixed player camera; 2 s settle + 4 s sample per stage',
                       'metrics': 'Slate frame intervals and Chaos interactor simulation time (ms), not packaged GPU/FPS',
                       'results': [], 'error': None}
        self.settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
        self.throttle = self.settings.get_editor_property('bThrottleCPUWhenNotForeground')

    def start(self):
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
            raise RuntimeError('Existing PIE preserved; probe not started')
        self.settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
        self.handle = u.register_slate_post_tick_callback(self.tick)
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        print('WITCH_AUDIT11 scheduled: temporary PIE only; no asset saves')

    def finish(self):
        if self.handle:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        active = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if active and active == self.world:
            if self.actor:
                self.actor.destroy_actor()
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        self.settings.set_editor_property('bThrottleCPUWhenNotForeground', self.throttle)
        (OUT / 'runtime_audit.json').write_text(json.dumps(self.report, indent=2), encoding='utf-8')
        print('WITCH_AUDIT11 finished: ' + str(OUT / 'runtime_audit.json'))

    def lengths(self):
        return {(a + '-' + b): (self.mesh.get_socket_location(a) - self.mesh.get_socket_location(b)).length() for a, b in PAIRS}

    def stage(self):
        name = STAGES[self.stage_index]
        self.mesh.set_editor_property('disable_cloth_simulation', name in ('cloth_off', 'cloth_off_flat'))
        flat = u.load_asset('/Engine/EngineMaterials/DefaultMaterial') if name == 'cloth_off_flat' else None
        for i, material in enumerate(self.materials):
            self.mesh.set_material(i, flat or material)
        self.mesh.force_cloth_next_update_teleport_and_reset()
        if name == 'death':
            self.report['limb_lengths_alive_cm'] = self.lengths()
            u.GameplayStatics.apply_damage(self.actor, 1000000., None, None, u.DamageType)
        self.since = time.perf_counter()
        self.samples = []

    def tick(self, dt):
        try:
            now = time.perf_counter()
            wall_dt = now - self.previous
            self.previous = now
            if now - self.started > 150:
                raise RuntimeError('Probe timeout')
            world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if self.world and world != self.world:
                raise RuntimeError('Owned PIE ended/changed; other world preserved')
            if not world:
                return
            if self.world is None:
                if 'DayNight_Lighting' not in world.get_name():
                    if not self.travel:
                        self.travel = True
                        u.GameplayStatics.open_level(world, '/Game/GameMaps/DayNight_Lighting')
                    return
                self.world = world
                self.report['map'] = world.get_path_name()
            if self.actor is None:
                player = u.GameplayStatics.get_player_pawn(world, 0)
                if not player:
                    return
                found = u.GameplayStatics.get_all_actors_of_class(world, u.WitchRebuiltMonster)
                if not self.spawn:
                    if found:
                        raise RuntimeError('Unexpected Witch present; probe did not adopt it')
                    self.spawn = True
                    u.SystemLibrary.execute_console_command(world, 'summon FPSGAME.WitchRebuiltMonster', u.GameplayStatics.get_player_controller(world, 0))
                    return
                if not found:
                    return
                self.actor = found[0]
                controller = self.actor.get_controller()
                if controller:
                    brain = controller.get_component_by_class(u.BrainComponent)
                    if brain:
                        brain.stop_logic('Temporary Witch review')
                    controller.stop_movement()
                    controller.set_actor_tick_enabled(False)
                self.actor.get_component_by_class(u.CharacterMovementComponent).disable_movement()
                self.actor.set_actor_tick_enabled(False)
                self.mesh = self.actor.get_component_by_class(u.SkeletalMeshComponent)
                self.materials = [self.mesh.get_material(i) for i in range(self.mesh.get_num_materials())]
                self.report['animation_class'] = self.mesh.get_anim_instance().get_class().get_name()
                self.report['initial_state'] = str(self.actor.state)
                self.report['materials'] = [x.get_path_name() if x else None for x in self.materials]
                self.since = now
                return
            if self.stage_index < 0:
                if now - self.since < 4:
                    return
                it = self.mesh.get_clothing_simulation_interactor()
                self.report['solver'] = {'iterations': it.get_num_iterations(), 'substeps': it.get_num_substeps(),
                    'dynamic_particles': it.get_num_dynamic_particles(), 'kinematic_particles': it.get_num_kinematic_particles()}
                self.stage_index = 0
                self.stage()
                return
            elapsed = now - self.since
            if elapsed >= 2:
                off = STAGES[self.stage_index].startswith('cloth_off')
                it = self.mesh.get_clothing_simulation_interactor()
                self.samples.append({'frame_ms': wall_dt * 1000., 'cloth_ms': 0. if off else it.get_simulation_time()})
            if elapsed < 6:
                return
            result = {'stage': STAGES[self.stage_index], 'samples': len(self.samples)}
            for key in ('frame_ms', 'cloth_ms'):
                values = sorted(x[key] for x in self.samples)
                result[key] = {'median': statistics.median(values), 'p95': values[int((len(values) - 1) * .95)], 'max': max(values)}
            if STAGES[self.stage_index] == 'death':
                result['state'] = str(self.actor.state)
                result['ragdoll'] = self.mesh.is_simulating_physics('pelvis')
                result['limb_lengths_cm'] = self.lengths()
                result['component_bounds'] = str(self.mesh.get_local_bounds())
            self.report['results'].append(result)
            self.stage_index += 1
            if self.stage_index == len(STAGES):
                self.finish()
            else:
                self.stage()
        except Exception:
            self.report['error'] = traceback.format_exc()
            self.finish()


capture = Capture()
capture.start()
