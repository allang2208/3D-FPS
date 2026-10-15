import json
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/NetworkAudioReviewV18')
root.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview')
cdo=u.get_default_object(bp.generated_class())
report={'blueprint':bp.get_path_name(),'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),'sounds':{},'clips':{},'settings':{},'instances':[]}
for name in ('breath_sound','breath_inhale_sound'):
    sound=cdo.get_editor_property(name)
    row={'path':sound.get_path_name() if sound else None}
    if sound:
        row.update(duration=sound.get_editor_property('duration'),attenuation=str(sound.get_editor_property('attenuation_settings')))
        if isinstance(sound,u.SoundWave):
            row['looping']=sound.get_editor_property('looping')
            row['channels']=sound.get_editor_property('num_channels')
    report['sounds'][name]=row
for name in ('idle_clip','move_clip','turn_left_clip','turn_right_clip','sweep_clip','slam_clip','breath_clip','stun_clip','air_clip','land_clip','get_up_clip','death_clip'):
    clip=cdo.get_editor_property(name)
    row={'path':clip.get_path_name() if clip else None}
    if clip:
        row['duration']=clip.get_play_length()
        row['notifies']=[str(n) for n in u.AnimationLibrary.get_animation_notify_events(clip)]
    report['clips'][name]=row
for name in ('sweep_damage','slam_damage','slam_area_radius','slam_stun_seconds','breath_damage','breath_range','breath_minimum_range','breath_arc_degrees','breath_cooldown','enable_back_smoke','visual_mesh','reaction_physics'):
    value=cdo.get_editor_property(name)
    report['settings'][name]=value.get_path_name() if isinstance(value,u.Object) else value
report['mouth_samples']=len(cdo.get_editor_property('breath_mouth_samples'))
report['hit_clips']=[c.get_path_name() if c else None for c in cdo.get_editor_property('hit_clips')]
report['audio_components']=[c.get_path_name() for c in cdo.get_components_by_class(u.AudioComponent)]
for actor in u.ObjectIterator(u.M66IncineratorMonster):
    if actor==cdo:continue
    report['instances'].append({'path':actor.get_path_name(),'health':actor.get_editor_property('health'),'authority':actor.has_authority()})
(root/'asset_snapshot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_READ_ONLY_ASSET_SNAPSHOT '+json.dumps(report,ensure_ascii=False))
