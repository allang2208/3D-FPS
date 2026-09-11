import unreal
for kind in ['Nurse','HandBrain']:
 clip=unreal.load_asset('/Game/Monsters/AI/A_'+kind+'_Hit');assert clip
 assert unreal.MonsterCombatComponent.author_hit_clip(clip,kind=='HandBrain');assert unreal.EditorAssetLibrary.save_loaded_asset(clip,False)
unreal.log('MONSTER_HIT_AXES_REBUILT')
