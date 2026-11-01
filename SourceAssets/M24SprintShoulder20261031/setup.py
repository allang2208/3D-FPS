from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24GripOutfit20261030/setup.py').read_text(),'current_M24_setup','exec'))
def entry_for(family,role):
    role=role.removesuffix('_mag10')
    path=next(p for p in roles if p.endswith('A_M24_'+role))
    return roles[path],next(c for c in ue['profiles'][family] if c['base']==path)
def row_at(family,role,frame):
    clip,entry=entry_for(family,role);return local_pose(clip,entry,frame/30)[0]

_sample_original=sample
def sample(track,t):
    # Existing serialized float keys may share their final timestamp. UE holds
    # the last key at this endpoint; do the same when reading the author inputs.
    if t>=track['times'][-1]:return unpack(track['values'][-10:])
    return _sample_original(track,t)
