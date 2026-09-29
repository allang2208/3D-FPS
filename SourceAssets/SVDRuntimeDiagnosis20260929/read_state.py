import unreal as u
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
 if a.get_class().get_name()=='FPSGAMECharacter':
  print('STATE',a.is_aiming(),a.is_reloading());print([x for x in dir(a) if any(k in x for k in ['aim','reload'])])
  for c in a.get_components_by_class(u.SkeletalMeshComponent):
   if c.get_name()=='AKMViewmodel':
    ai=c.get_anim_instance()
    for p in ['IdleClip','AimClip','ActionClip']:
     try:print(p,ai.get_editor_property(p))
     except Exception as e:print(str(e))
