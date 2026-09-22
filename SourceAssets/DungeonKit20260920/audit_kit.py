"""Read-only audit of dungeon kit candidates in the running editor.

Prints bounds (cm) for EBS structure meshes and candidate prop meshes so the
assembly script can snap pieces to a real grid instead of guessing.

Run: python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/DungeonKit20260920/audit_kit.py
"""
import unreal

STRUCTURES = [
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Wall',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Foundation',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Ceiling',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Stairs',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Doorframe',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Door',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Fence',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Tri_Wall',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Metal/SM_Polygonal_Metal_Wall',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Metal/SM_Polygonal_Metal_Foundation',
    '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Wood/SM_Polygonal_Wood_Wall',
]
PROPS = [
    '/Game/MilitaryTrench/Assets/3D/Ind_Storage_Barrel_Metal_Rust_01/StaticMeshes/SM_Ind_Storage_Barrel_Metal_Rust_01',
    '/Game/MilitaryTrench/Assets/3D/Mil_Trench_Bench_Wood_01/StaticMeshes/SM_Mil_Trench_Bench_Wood_01',
    '/Game/MilitaryTrench/Assets/3D/Ind_Con_Pile_Rubble_Gravel_Patch_01/StaticMeshes/SM_Ind_Con_Pile_Rubble_Gravel_Patch_01',
    '/Game/Props/RomanColumn20260915/SM_RomanColumn_Round_20',
    '/Game/Props/RomanColumn20260915/SM_BronzeTorch',
]


def report(path):
    mesh = unreal.load_asset(path)
    if mesh is None:
        unreal.log('KIT_MISSING ' + path)
        return
    try:
        b = mesh.get_bounds()
        box = b.box_extent
        origin = b.origin
        unreal.log(f'KIT_SIZE {path.split("/")[-1]} extent=({box.x:.1f},{box.y:.1f},{box.z:.1f}) origin=({origin.x:.1f},{origin.y:.1f},{origin.z:.1f})')
    except Exception as e:
        unreal.log(f'KIT_ERR {path} {e}')


for p in STRUCTURES + PROPS:
    report(p)

# Also report what the dungeon host candidates look like.
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.log('KIT_WORLD ' + (world.get_name() if world else 'none'))
unreal.log('KIT_ACTORS ' + str(len(sub.get_all_level_actors())))
unreal.log('KIT_AUDIT_DONE')