"""Install the original fitted query shapes (first stage only).

For the current game, follow this with install_combat_physics.py in the FPSGAME
editor host. That stage enables complex weapon traces and constrained ragdolls.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieMeshy20260913')
folder = '/Game/Monsters/FatZombieMeshy/'
mesh = u.load_asset(folder + 'SK_FatZombie_Meshy')
def call(name, **arguments):
    result = u.ToolsetRegistry.execute_tool('PhysicsToolsets.PhysicsAssetToolset', name, json.dumps(arguments))
    if not result.is_complete or result.error:
        raise RuntimeError(str(result.error) or 'Physics tool did not finish synchronously: ' + name)
    return json.loads(result.value).get('returnValue')

physics = u.load_asset(folder + 'SK_FatZombie_Meshy_PhysicsAsset')
if not physics:
    created = call('CreateFromMesh', meshPath=folder + 'SK_FatZombie_Meshy', bAssignToMesh=True)
    physics = u.load_asset(created['refPath'])
ref = {'refPath': physics.get_path_name()}
for bone in call('GetBodyNames', physicsAsset=ref):
    call('RemoveBody', physicsAsset=ref, boneName=bone)
shapes = json.loads((ROOT / 'damage_collision_shapes.json').read_text(encoding='utf-8'))
for shape in shapes:
    bone = shape['bone']
    call('AddBody', physicsAsset=ref, boneName=bone)
    rotation = u.MathLibrary.make_rot_from_z(u.Vector(*shape['axis']))
    call('SetCapsule', physicsAsset=ref, boneName=bone, shapeName='SkinFit',
         center=dict(zip(('x','y','z'),shape['center'])),
         rotation={'pitch':rotation.pitch, 'yaw':rotation.yaw, 'roll':rotation.roll},
         radius=shape['radius'], length=shape['length'])
    call('SetBodyPhysicsMode', physicsAsset=ref, boneName=bone, mode='Kinematic')
mesh.set_editor_property('physics_asset', physics)
u.EditorAssetLibrary.set_metadata_tag(physics, 'Purpose', 'Bone-local damage query bodies fitted to original Meshy skin; not a ragdoll')
u.EditorAssetLibrary.set_metadata_tag(mesh, 'Status', 'Original skin retained; fitted damage-query physics; user gameplay testing pending')
if not u.EditorAssetLibrary.save_loaded_asset(physics, False):
    raise RuntimeError('Cannot save damage physics')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Cannot save mesh physics assignment')
u.log('FAT_DAMAGE_PHYSICS_SAVED ' + str(len(shapes)))
