"""Install the Witch navigation profile in the open editor and build its map.

DefaultEngine.ini owns the persistent profile. This applies it to the already
running editor as well, so a restart is not required to build/save the navmesh.
Run with Tools/AssetPipeline/ue_python_exec.py --script Tools/Witch/install_navigation.py.
Does not start PIE, spawn actors for gameplay, or run path/placement tests.
"""
import json
from pathlib import Path

import unreal as u


editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError("Stop the current PIE session before editing navigation.")
world = editor.get_editor_world()
nav = u.NavigationSystemV1.get_navigation_system(world)
if not nav:
    raise RuntimeError("The open map has no navigation system.")
bounds = u.GameplayStatics.get_all_actors_of_class(world, u.NavMeshBoundsVolume)
if not bounds:
    raise RuntimeError("The open map requires authored navigation bounds first.")

cdo = u.get_default_object(u.NavigationSystemV1)
agents = list(cdo.get_editor_property("supported_agents"))
witch_index = next((i for i, a in enumerate(agents)
                    if str(a.get_editor_property("name")) == "Witch"), None)
if witch_index is None:
    # Keep existing agent indices: level bounds masks refer to those indices.
    agents.append(agents[0].copy())
    witch_index = len(agents) - 1
witch = agents[witch_index]
witch.set_editor_property("name", "Witch")
witch.set_editor_property("agent_radius", 34.0)
# IsEquivalent has a 5 cm tolerance. A 188 cm profile is merged with Nurse's
# 184 cm profile during registration; 192 cm provides valid, distinct clearance.
witch.set_editor_property("agent_height", 192.0)
witch.set_editor_property("agent_step_height", 40.0)
cdo.set_editor_property("supported_agents", agents)
nav.set_editor_property("supported_agents", agents)

# Align the loaded CDO with the updated native construction logic. Live Coding
# does not rerun constructors for existing class defaults.
movement = u.get_default_object(u.WitchMonster).get_editor_property("character_movement")
props = movement.get_editor_property("nav_agent_props")
props.set_editor_property("agent_radius", 34.0)
props.set_editor_property("agent_height", 192.0)
props.set_editor_property("agent_step_height", 40.0)
movement.set_editor_property("nav_agent_props", props)
policy = movement.get_editor_property("nav_movement_properties")
policy.set_editor_property("update_nav_agent_with_owners_collision", False)
movement.set_editor_property("nav_movement_properties", policy)

# This map already enables all agents. Do not widen its bounds or replace
# existing masks, brushes, or other monsters' navigation settings.
selector_field = "supports_agent%d" % witch_index
mask = nav.get_editor_property("supported_agents_mask")
if not mask.get_editor_property(selector_field):
    raise RuntimeError("Enable the Witch agent in this map's navigation-system mask.")
if not any(b.get_editor_property("supported_agents").get_editor_property(selector_field)
           for b in bounds):
    raise RuntimeError("Enable the Witch agent on the intended navigation bounds.")

# UNavigationSystemV1::Build creates missing data, registers it and waits for
# tile generation to finish. It is an asset build, not a gameplay probe.
actor_editor = u.get_editor_subsystem(u.EditorActorSubsystem)
for data in u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh):
    if data.get_name().startswith("RecastNavMesh-Witch") and (
        data.get_editor_property("agent_radius") != 34.0
        or data.get_editor_property("agent_height") != 192.0
    ):
        # Replace only this task's earlier profile, which UE may leave in the
        # level after rejecting it as equivalent to Nurse during registration.
        if not actor_editor.destroy_actor(data):
            raise RuntimeError("Could not replace the previous Witch navigation data.")
u.SystemLibrary.execute_console_command(world, "RebuildNavigation")
created_data = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh)
                if a.get_editor_property("agent_radius") == 34.0
                and a.get_editor_property("agent_height") == 192.0]
if not created_data:
    raise RuntimeError("Navigation build did not produce the Witch profile; map not saved.")
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():
    raise RuntimeError("Could not save the current map after building navigation.")

report = {
    "map": world.get_path_name(),
    "profile": {"name": "Witch", "radius_cm": 34, "height_cm": 192, "step_cm": 40},
    "capsule_height_cm": 188,
    "navigation_data": [a.get_path_name() for a in created_data],
    "profile_index": witch_index,
    "operation": "RebuildNavigation and save_current_level",
    "saved": True,
    "runtime_tested": False,
}
destination = Path(u.Paths.project_saved_dir()) / "WitchMeshy" / "navigation_install.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
