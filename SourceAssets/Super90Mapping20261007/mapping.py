"""Register the gun's FBX UVs to the original, top-origin PNG atlas.

The original receiver islands are U=.3591-.4174 / V=.2255-.5544 and
U=.7315-.7894 / V=.6712-.9980, matching the PNG's two marked panels directly
in image coordinates. Blender needs (u, 1-v), not a 180-degree rotation.
Do not derive this from the separately converted GLB's material transform.
Only gun/shell objects are passed here; arms and clothing keep their UVs.
"""
VERSION='SourcePNG-VFlip-20261007'
LEGACY_VERSION='SourceGunAtlas180-20261007'

def correct_weapon_uv(objects):
    changed=[]
    for ob in objects:
        me=ob.data
        previous=me.get('Super90AtlasMapping')
        if previous==VERSION:continue
        for corner in me.uv_layers[0].data:
            # Already-corrected V is retained when migrating the old recipe.
            if previous==LEGACY_VERSION:corner.uv.x=1.-corner.uv.x
            else:corner.uv.y=1.-corner.uv.y
        me['Super90AtlasMapping']=VERSION;changed.append(ob.name)
    return changed
