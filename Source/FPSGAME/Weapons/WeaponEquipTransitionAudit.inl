// Exercise real profile publication and CycleWeapon, not a direct camera action.
if(auto* C=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.body.AsyncPreload")))C->Set(0,ECVF_SetByCode);
Pawn->DispatchBeginPlay();Model->AttachPawn(Pawn);
Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
#if WITH_EDITOR
FAssetCompilingManager::Get().FinishAllCompilation();
#endif
const auto Present=[&](float Dt)
{
    ++GFrameCounter;World->Tick(LEVELTICK_TimeOnly,Dt);
    Pawn->UpdateWeaponState(Dt);Pawn->UpdateWeaponFeedback(Dt);Pawn->UpdateCamera(Dt);
    Pawn->UpdateViewmodel(Dt);Pawn->UpdateActionPose(Dt);
    Pawn->AKMViewmodel->TickAnimation(Dt,false);Pawn->AKMViewmodel->RefreshBoneTransforms();
    Body->TickComponent(Dt,LEVELTICK_All,nullptr);
    if(auto* Mesh=Body->GetBodyMesh()){Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();}
    FMinimalViewInfo View;Pawn->CalcCamera(Dt,View);return View;
};
const TCHAR* Guns[]={TEXT("ue_lmg201"),TEXT("ue_pkm_lowpoly"),TEXT("ue_m249")};
TArray<TSharedPtr<FJsonValue>> Transitions;
for(int32 From=0;From<3;++From)for(int32 To=0;To<3;++To)if(From!=To)
for(int32 Mode=0;Mode<3;++Mode)for(int32 FPS:{30,120,0})
{
    Pawn->bIsSprinting=Pawn->bSprintHeld=false;Pawn->SetAimingState(false);
    Pawn->GetCharacterMovement()->SetMovementMode(MOVE_None);Pawn->GetCharacterMovement()->Velocity=FVector::ZeroVector;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    for(int32 Loadout=0;Loadout<2;++Loadout)
    {auto I=Model->CreateItem(Guns[Loadout?To:From]);I.Place=1;I.Cell=Loadout?9:6;I.Magazine=30;Seed.Items.Add(I);}
    if(!Model->CommitState(Seed))return 4;
    for(int32 I=0;I<150;++I)Present(1.f/60.f);
    if(Mode==1)
    {
        Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        Pawn->GetCharacterMovement()->Velocity=FVector(Pawn->SprintSpeed,0,0);
        Pawn->bIsSprinting=Pawn->bSprintHeld=true;
    }
    if(Mode==2)Pawn->SetAimingState(true);
    for(int32 I=0;I<60;++I)Present(1.f/60.f);
    double MaxJumpFOV=0,MaxJumpAngle=0,MaxJumpCM=0,MaxFOVRate=0,MaxAngleRate=0;
    bool Finite=true,Identity=true,MirrorStable=true;
    FMinimalViewInfo Previous;Pawn->CalcCamera(0,Previous);
    for(int32 Switch=0;Switch<3;++Switch)
    {
        const FString Old=Pawn->ActiveInventoryWeapon;
        if(!Model->CycleWeapon())return 4;
        Identity&=Old!=Pawn->ActiveInventoryWeapon&&Model->ActiveFirearm()&&Pawn->ActiveInventoryWeapon==Model->ActiveFirearm()->InstanceId;
        Pawn->FirearmEquipRate=FPS==120?2.5f:1.f;
        const auto Event=Present(0.f);
        MaxJumpFOV=FMath::Max(MaxJumpFOV,double(FMath::Abs(Event.FOV-Previous.FOV)));
        MaxJumpAngle=FMath::Max(MaxJumpAngle,FMath::RadiansToDegrees(Event.Rotation.Quaternion().AngularDistance(Previous.Rotation.Quaternion())));
        MaxJumpCM=FMath::Max(MaxJumpCM,FVector::Dist(Event.Location,Previous.Location));Previous=Event;
        float Age=0;int32 Frame=0;
        while(Age<(Mode==0?.11f:Switch==0?.33f:.09f))
        {
            const float Dt=FPS>0?1.f/FPS:(Frame++%7==3?.12f:1.f/90.f);Age+=Dt;
            const auto V=Present(Dt);Finite&=!V.Location.ContainsNaN()&&!V.Rotation.ContainsNaN()&&FMath::IsFinite(V.FOV);
            MaxFOVRate=FMath::Max(MaxFOVRate,double(FMath::Abs(V.FOV-Previous.FOV)/Dt));
            MaxAngleRate=FMath::Max(MaxAngleRate,FMath::RadiansToDegrees(V.Rotation.Quaternion().AngularDistance(Previous.Rotation.Quaternion()))/Dt);
            Previous=V;
        }
        const auto Started=Pawn->WeaponActionStartedAt;
        Model->AdoptNetMirror(Model->Snapshot(),true);Pawn->ApplyColdSteelProfile(Model);
        MirrorStable&=Pawn->WeaponActionStartedAt==Started;
    }
    Pawn->bIsSprinting=Pawn->bSprintHeld=false;Pawn->SetAimingState(false);
    Pawn->GetCharacterMovement()->Velocity=FVector::ZeroVector;Pawn->GetCharacterMovement()->SetMovementMode(MOVE_None);
    for(int32 I=0;I<180;++I)Present(1.f/60.f);
    const auto End=Read(Pawn->FirstPersonCamera);
    const bool Settled=End.Equals(FTransform::Identity,.001f)&&FMath::IsNearlyEqual(Pawn->FirstPersonCamera->FieldOfView,Pawn->BaseLookHorizontalFOV(),.01f)&&Pawn->WeaponState==EAKMWeaponState::Idle;
    const bool Passed=Finite&&Identity&&MirrorStable&&Settled&&MaxJumpFOV<.01&&MaxJumpAngle<.05&&MaxJumpCM<.1&&MaxFOVRate<240&&MaxAngleRate<90;
    auto C=MakeShared<FJsonObject>();C->SetStringField(TEXT("from"),Guns[From]);C->SetStringField(TEXT("to"),Guns[To]);
    C->SetStringField(TEXT("mode"),Mode==0?TEXT("rapid"):Mode==1?TEXT("sprint"):TEXT("ads"));C->SetNumberField(TEXT("fps"),FPS);
    C->SetBoolField(TEXT("passed"),Passed);C->SetBoolField(TEXT("settled"),Settled);C->SetBoolField(TEXT("mirror_no_restart"),MirrorStable);
    C->SetNumberField(TEXT("event_fov_jump_deg"),MaxJumpFOV);C->SetNumberField(TEXT("event_angle_jump_deg"),MaxJumpAngle);C->SetNumberField(TEXT("event_position_jump_cm"),MaxJumpCM);
    C->SetNumberField(TEXT("max_fov_rate_deg_s"),MaxFOVRate);C->SetNumberField(TEXT("max_angle_rate_deg_s"),MaxAngleRate);
    Transitions.Add(MakeShared<FJsonValueObject>(C));Failures+=!Passed;
    UE_LOG(LogTemp,Display,TEXT("EQUIP_TRANSITION %s %s -> %s mode=%d fps=%d jump=%.5f/%.5f/%.5f settled=%d"),Passed?TEXT("PASS"):TEXT("FAIL"),Guns[From],Guns[To],Mode,FPS,MaxJumpFOV,MaxJumpAngle,MaxJumpCM,Settled);
}
Report->SetArrayField(TEXT("transitions"),Transitions);
Report->SetStringField(TEXT("transition_scope"),TEXT("Native profile CycleWeapon, full camera POV and evaluated body; 3 rapid changes; identical mirror reapply. Controlled movement, no rendering."));
