import unreal as u
m=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
print('Existing physics diagnostic:',u.WitchRebuiltMonster.prepare_rebuilt_physics(m,False))
