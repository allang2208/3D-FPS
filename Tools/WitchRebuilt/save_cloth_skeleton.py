"""Save this batch's skeleton update after final cloth render reimport."""
import unreal as u
path='/Game/Monsters/WitchRebuilt/SKEL_WitchRebuilt'
if not u.EditorAssetLibrary.save_asset(path,True):
    raise RuntimeError('Could not save candidate skeleton after cloth import')
print('Saved candidate skeleton changed by final render import')
