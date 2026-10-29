"""Bounded read-only sampling of the existing PIE pawn and final bone output."""
import json, time
from pathlib import Path
import unreal as u

output=Path(__file__).with_name("live-frames.json")
bones=("pelvis","thigh_l","calf_l","foot_l","thigh_r","calf_r","foot_r","spine_01","hand_r")
rows=[]
started=time.monotonic()
next_sample=started
next_save=started
handle=None
def sample(delta):
    global next_sample,next_save
    now=time.monotonic()
    try:
        if now>=next_sample:
            next_sample=now+.04
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if world:
                for p in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
                    if not p.is_locally_controlled(): continue
                    body=p.get_component_by_class(u.FPSPlayerBodyComponent)
                    mesh=p.mesh
                    state=body.get_body_state()
                    velocity=p.get_velocity()
                    row={"t":now-started,"world":world.get_path_name(),
                         "family":str(state.family),"action":str(state.action),"progress":state.action_progress,
                         "variant":str(state.action_variant),"velocity":[velocity.x,velocity.y,velocity.z],
                         "falling":p.character_movement.is_falling(),
                         "post_process":str(mesh.get_skeletal_mesh_asset().get_editor_property("post_process_anim_blueprint")),
                         "body":mesh.get_path_name(),"owner_no_see":mesh.get_editor_property("owner_no_see"),
                         "bones":{}}
                    for name in bones:
                        tr=mesh.get_socket_transform(name,u.RelativeTransformSpace.RTS_COMPONENT)
                        v=tr.translation
                        row["bones"][name]=[v.x,v.y,v.z]
                    rows.append(row)
        if now>=next_save or now-started>=90:
            output.write_text(json.dumps(rows,ensure_ascii=False),encoding="utf-8")
            next_save=now+2
        if now-started>=90:
            u.unregister_slate_post_tick_callback(handle)
            print("Kukri live observer finished: "+str(len(rows))+" samples")
    except Exception as exc:
        output.with_suffix(".error.txt").write_text(str(exc),encoding="utf-8")
        u.unregister_slate_post_tick_callback(handle)
        raise
handle=u.register_slate_post_tick_callback(sample)
print("Read-only existing PIE observation registered for 90 seconds")
