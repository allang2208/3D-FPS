// Source/FPSGAME/Production/ProductionToolComponent.cpp
// Separated insertion sites, not one contiguous function body. See current compiled source and sprint authority consumer.
    // RefreshHeldTool: include material in existing async Paths before RequestAsyncLoad.
    Paths.Add(FSoftObjectPath(WarhammerRift::Material));
    // AdvanceActionBeforeCamera: immediately before/after existing Elapsed advancement.
    const float PreviousElapsed=Elapsed;
    // ... existing Elapsed update ...
    if(bBluntSprintAttack)AdvanceBluntSprintLunge(PreviousElapsed,Elapsed);
    // TickComponent: after existing local hand presentation.
    TickWarhammerRifts(Delta,Present);
    UpdateStormDriveLightning(Delta);
    // EndPlay: before releasing visible tool components.
    ClearWarhammerRifts(true);
    ClearStormDriveLightning();
    // FinishUse/CancelUse: bBluntSprintLungeBlocked=true; bBluntServerSprintAttack=false.
