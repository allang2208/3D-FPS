import unreal
lib=unreal.EditorAssetLibrary
for p in ['/Game/Monsters/AI/BP_MonsterAIController','/Game/Monsters/NurseZombie/BP_NurseZombie','/Game/Monsters/HandBrain/BP_HandBrain']:
 bp=unreal.load_asset(p);cdo=unreal.get_default_object(bp.generated_class());unreal.log('AI_CDO '+p)
 for k in ['behavior','ai_controller_class','auto_possess_ai','combat']:
  try:unreal.log('AI_PROPERTY '+k+' '+str(cdo.get_editor_property(k)))
  except:pass
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);level.load_level('/Game/Tests/MonsterAI/L_MonsterAI')
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 if isinstance(a,unreal.NurseZombie):unreal.log('AI_INSTANCE '+str(a.get_editor_property('ai_controller_class'))+' hit='+str(a.get_editor_property('combat').get_editor_property('hit_clip')))
