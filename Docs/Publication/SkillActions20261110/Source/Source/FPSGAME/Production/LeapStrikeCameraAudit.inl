// Explicit camera/body review. Native movement, camera, arms, body state and
// animation evaluation in a disposable world; no rendering or player-save writes.
auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;int32 Failures=0;
FString BodyId=TEXT("jason"),Json;FParse::Value(*Params,TEXT("CameraBody="),BodyId);
TSharedPtr<FJsonObject> Config;
if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))||
    !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Config))return 3;
if(BodyId!=TEXT("jason"))Config=Config->GetObjectField(TEXT("body_variants"))->GetObjectField(BodyId);
auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();Body->Character=Pawn;
Body->Configuration=MakeShared<FJsonObject>(*Config);
auto Clips=MakeShared<FJsonObject>();
for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
    if(Pair.Key.ToView().StartsWith(TEXT("Warhammer.FullBody."))||Pair.Key.ToView().StartsWith(TEXT("Unarmed."))||
        Pair.Key.ToView().StartsWith(TEXT("Crouch."))||Pair.Key==TEXT("Jump")||Pair.Key==TEXT("Fall")||Pair.Key==TEXT("Land"))
        Clips->SetField(Pair.Key,Pair.Value);
Body->Configuration->SetObjectField(TEXT("clips"),Clips);
Body->InitializeBody(false);
#if WITH_EDITOR
FAssetCompilingManager::Get().FinishAllCompilation();
#endif
auto* Mesh=Body->GetBodyMesh();
if(!Mesh||!Mesh->GetSkeletalMeshAsset()||!Body->BodyAnimation||!Tool->Viewmodel)return 3;
// A commandlet does not dispatch BeginPlay, which normally auto-activates the
// camera. Exercise the real CameraComponent POV rather than ActorEyes fallback.
Pawn->FirstPersonCamera->Activate(true);
if(!Pawn->FirstPersonCamera->IsActive())return 3;
Body->RefreshCountdown=Body->RemoteEquipCountdown=1.e9f;Body->bEquipmentDirty=false;
Report->SetStringField(TEXT("body"),BodyId);Report->SetStringField(TEXT("mesh"),Mesh->GetSkeletalMeshAsset()->GetPathName());
Report->SetNumberField(TEXT("native_body_clips"),Body->BodyAnimation->Clips.Num());
const float Half=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),Radius=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius();
const float Standing=LeapStrike::StandingHeight(Half,Radius,FVector::UpVector);
const auto MakeBox=[&](const FVector& P,const FVector& E,const FRotator& R=FRotator::ZeroRotator)
{
    auto* A=World->SpawnActor<AActor>();auto* B=NewObject<UBoxComponent>(A);A->SetRootComponent(B);
    B->SetMobility(EComponentMobility::Movable);B->SetBoxExtent(E);B->SetCollisionObjectType(ECC_WorldStatic);
    B->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);B->SetCollisionResponseToAllChannels(ECR_Block);
    B->RegisterComponent();A->SetActorLocationAndRotation(P,R);return B;
};
const TCHAR* Names[]={TEXT("flat"),TEXT("wall"),TEXT("blocked_before_cast"),TEXT("wall_removed"),TEXT("ceiling"),
    TEXT("uphill_25"),TEXT("downhill_25"),TEXT("wall_uphill"),TEXT("wall_downhill"),
    TEXT("roof_30m"),TEXT("roof_100m"),TEXT("roof_200m"),TEXT("platform_drops_8m"),TEXT("platform_removed"),
    TEXT("platform_shifts"),TEXT("platform_moves_after_contact"),TEXT("platform_removed_after_contact"),
    TEXT("cancel_charge"),TEXT("cancel_ascent"),TEXT("cancel_descent"),TEXT("cancel_near_contact"),TEXT("cancel_after_contact"),
    TEXT("no_movement_progress"),TEXT("no_floor"),TEXT("camera_obstacle_removed"),
    TEXT("cancel_at_wall"),TEXT("cancel_after_wall_contact"),TEXT("remove_wall_during_cancel")};
const float Rates[]={30,60,120,144,0};
FMinimalViewInfo View;
const auto Present=[&](float Dt)
{
    Pawn->UpdateCamera(Dt);Tool->UpdateHandPresentation(Dt);
    Body->TickComponent(Dt,LEVELTICK_All,nullptr);
    Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();Pawn->CalcCamera(Dt,View);
};
for(int32 Kind=0;Kind<UE_ARRAY_COUNT(Names);++Kind)for(float Rate:Rates)
{
    Tool->FinishLeapStrike();Tool->SetLeapAirborne(false);Move->SetMovementMode(MOVE_None);Move->StopMovementImmediately();
    Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->LandingOffset=Pawn->LandingVelocity=Pawn->PreviousVerticalVelocity=0.f;Pawn->bWasGrounded=true;
    auto Fresh=Model->Snapshot();Fresh.LeapStrikeCooldown=Fresh.LeapStrikeCooldownDuration=0.f;Fresh.Stamina=150.f;Model->CommitState(Fresh);
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Floor->SetActorLocation(FVector(0,0,-25));
    TArray<UBoxComponent*> Geometry;UBoxComponent* Platform=nullptr;UBoxComponent* Wall=nullptr;
    const bool Roof=(Kind>=9&&Kind<=16)||Kind==18||Kind==19||Kind==20;
    const float StartZ=Kind==10?10000.f:Kind==11?20000.f:Roof?3000.f:0.f;
    const float Pitch=Kind==5||Kind==7?25.f:Kind==6||Kind==8?-25.f:0.f;
    const float Reach=Pitch!=0.f?200.f:800.f;
    const FVector Normal=FRotator(Pitch,0,0).RotateVector(FVector::UpVector);
    float TargetZ=Pitch!=0.f?FMath::Tan(FMath::DegreesToRadians(Pitch))*Reach:Kind>=12&&Kind<=16?StartZ:0.f;
    if(Roof)
    {
        Geometry.Add(MakeBox(FVector(-455,0,StartZ-20),FVector(500,1500,20)));
        if(TargetZ>0.f){Platform=MakeBox(FVector(Reach,0,TargetZ-20),FVector(200,1500,20));Geometry.Add(Platform);}
    }
    if(Pitch!=0.f)
    {
        Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Geometry.Add(MakeBox(FVector(0,0,-25.f/Normal.Z),FVector(2000,2000,25),FRotator(Pitch,0,0)));
    }
    const auto AddWall=[&]()
    {Wall=MakeBox(FVector(Pitch!=0.f?120:340,0,300),FVector(15,500,300));Geometry.Add(Wall);};
    Pawn->SetActorLocation(FVector(0,0,StartZ+LeapStrike::StandingHeight(Half,Radius,Normal)),false);
    Move->SetMovementMode(MOVE_Walking);PC->SetControlRotation(FRotator::ZeroRotator);
    Tool->LeapCameraReleaseUntil=0.;
    Pawn->FirstPersonCamera->SetRelativeLocation(FVector(0,0,Pawn->StandingCameraHeight));
    if(Kind==24)
    {
        Wall=MakeBox(Pawn->GetActorLocation()+FVector(43,0,55),FVector(3,120,70));Geometry.Add(Wall);
        Wall->SetCollisionResponseToAllChannels(ECR_Ignore);Wall->SetCollisionResponseToChannel(ECC_Camera,ECR_Block);
    }
    for(int32 Warm=0;Warm<45;++Warm){++GFrameCounter;World->Tick(LEVELTICK_TimeOnly,1.f/60.f);Move->PerformMovement(1.f/60.f);Present(1.f/60.f);}
    if(Kind==2)AddWall();
    FVector Checked,CheckedFloor,CheckedNormal;
    const FVector TargetFloor(Reach,0,TargetZ),Target=TargetFloor+FVector(0,0,LeapStrike::StandingHeight(Half,Radius,Normal));
    const bool Valid=Tool->ValidateLeapLanding(Target,Checked,CheckedFloor,CheckedNormal);
    Tool->LeapRequestDirection=FVector::ForwardVector;
    const bool Started=Valid&&Tool->StartLeapStrike(Target,TargetFloor,Normal,World->GetTimeSeconds(),Model->LeapStrikeStats());
    bool Changed=false,Cancelled=false,Removed=false,Frozen=false,Finite=true,Continuous=true,Attached=true,Bounded=true,NoPenetration=true;
    float Time=0,Flight=0,Ended=-1,Contact=-1,MaxRelativeStep=0,MaxRelativeRate=0,MaxArmStep=0,MaxEyeRadius=0,MaxBodyOffsetError=0,MaxRootOffset=0;
    int32 Waves=0;FString FirstFailure;float FailureTime=-1;FVector PreviousActor=Pawn->GetActorLocation();
    FVector PreviousRelative=Pawn->FirstPersonCamera->GetComponentLocation()-PreviousActor;
    FVector PreviousArms=Tool->Viewmodel->GetComponentLocation()-PreviousActor;
    const auto Mark=[&](bool OK,const TCHAR* What){if(!OK&&FirstFailure.IsEmpty()){FirstFailure=What;FailureTime=Time;}};
    const auto Spawn=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([&](AActor* A){if(A->IsA<AWarhammerShockwave>())++Waves;}));
    TArray<TSharedPtr<FJsonValue>> Frames;
    for(int32 I=0;I<3000;++I)
    {
        const float Steps[]={1.f/120.f,1.f/45.f,1.f/60.f,.2f,1.f/144.f};const float Dt=Rate>0?1.f/Rate:Steps[I%5];
        Time+=Dt;++GFrameCounter;if(Tool->bLeapLaunched&&!Tool->bLeapLanded)Flight+=Dt;
        if(Tool->bLeapLaunched&&Flight>(Kind==4?.001f:.15f)&&!Changed)
        {
            Changed=true;
            if(Kind==1||Kind==3||Kind==7||Kind==8||Kind>=25)AddWall();
            if(Kind==4)Geometry.Add(MakeBox(FVector(440,0,Half*2+100),FVector(500,500,12)));
            if(Kind==12)Platform->GetOwner()->AddActorWorldOffset(FVector(0,0,-800));
            if(Kind==13)Platform->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            if(Kind==14)Platform->GetOwner()->AddActorWorldOffset(FVector(0,3000,0));
            if(Kind==22)Frozen=true;
            if(Kind==23)Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        }
        if((Kind==3||Kind==24)&&Wall&&Flight>.5f&&!Removed){Wall->SetCollisionEnabled(ECollisionEnabled::NoCollision);Removed=true;}
        if(Kind==27&&Wall&&Cancelled&&Ended>=0.f&&Time>Ended+.1f&&!Removed)
        {Wall->SetCollisionEnabled(ECollisionEnabled::NoCollision);Removed=true;}
        if(Tool->bLeapLanded&&Platform)
        {
            if(Kind==15)Platform->GetOwner()->AddActorWorldOffset(FVector(60*Dt,0,25*Dt));
            if(Kind==16&&!Removed){Platform->SetCollisionEnabled(ECollisionEnabled::NoCollision);Removed=true;}
        }
        const bool CancelNow=(Kind==17&&Time>=.25f)||(Kind==18&&Flight>=.2f)||(Kind==19&&Flight>=1.f)||
            (Kind==20&&!Tool->bLeapLanded&&Tool->LeapAge>LeapStrike::Land-LeapStrike::Downstroke+.035f)||
            ((Kind==21||Kind==26)&&Tool->bLeapLanded)||((Kind==25||Kind==27)&&Flight>=.45f);
        if(CancelNow&&!Cancelled){Tool->FinishLeapStrike();Cancelled=true;}
        const FVector Before=Pawn->GetActorLocation(),Velocity=Move->Velocity;
        World->Tick(LEVELTICK_TimeOnly,Dt);
        if(!Frozen||!Tool->bLeapStrike)Move->PerformMovement(Dt);
        Present(Dt);
        const FVector Actor=Pawn->GetActorLocation(),Eye=Pawn->FirstPersonCamera->GetComponentLocation(),Arms=Tool->Viewmodel->GetComponentLocation();
        const FVector Relative=Eye-Actor,ArmRelative=Arms-Actor;
        const float CameraStep=FVector::Dist(Relative,PreviousRelative),ArmStep=FVector::Dist(ArmRelative,PreviousArms);
        MaxRelativeStep=FMath::Max(MaxRelativeStep,CameraStep);MaxRelativeRate=FMath::Max(MaxRelativeRate,CameraStep/Dt);MaxArmStep=FMath::Max(MaxArmStep,ArmStep);
        const bool GoodMove=FVector::Dist(Actor,Before)<=(FMath::Max(1800.f,float(Velocity.Size()))+FMath::Abs(Move->GetGravityZ())*Dt)*Dt+8.f;
        const bool GoodCamera=CameraStep<=1600.f*Dt+2.f;
        const bool GoodArms=ArmStep<=FMath::Min(95.f,2400.f*Dt+3.f);
        Continuous&=GoodMove&&GoodCamera&&GoodArms;Mark(GoodMove,TEXT("capsule_jump"));Mark(GoodCamera,TEXT("camera_relative_jump"));Mark(GoodArms,TEXT("arms_relative_jump"));
        const FVector BodyLocation=Mesh->GetComponentLocation(),Head=Mesh->GetSocketLocation(TEXT("head")),Pelvis=Mesh->GetSocketLocation(TEXT("pelvis"));
        const FVector Root=Mesh->GetSocketTransform(TEXT("root"),RTS_Component).GetLocation();MaxRootOffset=FMath::Max(MaxRootOffset,float(Root.Size()));
        Finite&=!Actor.ContainsNaN()&&!Eye.ContainsNaN()&&!View.Location.ContainsNaN()&&!Head.ContainsNaN()&&!Pelvis.ContainsNaN()&&!Arms.ContainsNaN();Mark(Finite,TEXT("nonfinite_pose"));
        const float BodyError=FVector::Dist(Mesh->GetRelativeLocation(),FVector(0,0,-Half));MaxBodyOffsetError=FMath::Max(MaxBodyOffsetError,BodyError);
        Attached&=BodyError<.1f&&Root.Size()<100.f;Mark(Attached,TEXT("world_body_detached"));
        const bool Constrained=Tool->bLeapStrike||World->GetTimeSeconds()<Tool->LeapCameraReleaseUntil;
        const FVector POVRelative=View.Location-Actor;
        MaxEyeRadius=FMath::Max(MaxEyeRadius,float(FMath::Max(Relative.Size2D(),POVRelative.Size2D())));
        const bool InBounds=!Constrained||(Relative.Size2D()<=80.2f&&POVRelative.Size2D()<=80.2f&&FMath::Abs(Relative.Z)<=Half-5.8f&&FMath::Abs(POVRelative.Z)<=Half-5.8f);
        Bounded&=InBounds;Mark(InBounds,TEXT("camera_outside_body_envelope"));
        FCollisionQueryParams Q(SCENE_QUERY_STAT(LeapCameraAudit),false,Pawn);
        const bool Clear=!Constrained||(!World->OverlapBlockingTestByChannel(Eye,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(5.5f),Q)&&
            !World->OverlapBlockingTestByChannel(View.Location,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(5.5f),Q));
        NoPenetration&=Clear;Mark(Clear,TEXT("camera_in_geometry"));
        if(Tool->bLeapLanded&&Contact<0.f)Contact=Time;
        if(!Tool->bLeapStrike&&Ended<0.f)Ended=Time;
        auto F=MakeShared<FJsonObject>();F->SetNumberField(TEXT("time"),Time);F->SetNumberField(TEXT("dt"),Dt);F->SetNumberField(TEXT("pose"),Tool->LeapAge);
        F->SetBoolField(TEXT("active"),Tool->bLeapStrike);F->SetBoolField(TEXT("landed"),Tool->bLeapLanded);F->SetNumberField(TEXT("mode"),Move->MovementMode);
        F->SetArrayField(TEXT("actor"),LeapVec(Actor));F->SetArrayField(TEXT("eye_relative"),LeapVec(Relative));F->SetArrayField(TEXT("pov_relative"),LeapVec(POVRelative));
        F->SetArrayField(TEXT("arms_relative"),LeapVec(ArmRelative));F->SetArrayField(TEXT("body_relative"),LeapVec(BodyLocation-Actor));
        F->SetArrayField(TEXT("head_relative"),LeapVec(Head-Actor));F->SetArrayField(TEXT("pelvis_relative"),LeapVec(Pelvis-Actor));
        F->SetStringField(TEXT("body_action"),Body->GetBodyState().ActionVariant.ToString());F->SetNumberField(TEXT("camera_relative_step"),CameraStep);
        Frames.Add(MakeShared<FJsonValueObject>(F));PreviousActor=Actor;PreviousRelative=Relative;PreviousArms=ArmRelative;
        if(Ended>=0.f&&Time>Ended+1.f&&(Move->IsMovingOnGround()||Kind==23))break;
        if(Time>14.5f)break;
    }
    World->RemoveOnActorSpawnedHandler(Spawn);
    const int32 ExpectedWaves=Kind==2||(Kind>=17&&Kind<=20)||Kind==22||Kind==23||Kind==25||Kind==27?0:1;
    const auto Source=Move->GetRootMotionSource(LeapStrike::MotionName);
    const bool Released=!Source||Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval);
    const bool EndedClean=Ended>0.f&&Ended<13.5f&&!Tool->IsLeapStrikeActive()&&Released&&Move->MovementMode!=MOVE_Flying;
    Mark(EndedClean,TEXT("skill_did_not_release"));Mark(Waves==ExpectedWaves,TEXT("incorrect_impact_count"));
    const bool Passed=(Kind==2?!Started:Started)&&Finite&&Continuous&&Attached&&Bounded&&NoPenetration&&EndedClean&&Waves==ExpectedWaves;
    if(!Passed)++Failures;
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Names[Kind]);Row->SetNumberField(TEXT("fps"),Rate);Row->SetBoolField(TEXT("passed"),Passed);
    Row->SetBoolField(TEXT("started"),Started);Row->SetStringField(TEXT("first_failure"),FirstFailure);Row->SetNumberField(TEXT("failure_time"),FailureTime);
    Row->SetBoolField(TEXT("continuous"),Continuous);Row->SetBoolField(TEXT("attached"),Attached);Row->SetBoolField(TEXT("bounded"),Bounded);Row->SetBoolField(TEXT("clear_of_geometry"),NoPenetration);
    Row->SetNumberField(TEXT("max_relative_step_cm"),MaxRelativeStep);Row->SetNumberField(TEXT("max_relative_speed_cm_s"),MaxRelativeRate);Row->SetNumberField(TEXT("max_arm_step_cm"),MaxArmStep);
    Row->SetNumberField(TEXT("max_eye_radius_cm"),MaxEyeRadius);Row->SetNumberField(TEXT("body_offset_error_cm"),MaxBodyOffsetError);Row->SetNumberField(TEXT("max_root_translation_cm"),MaxRootOffset);
    Row->SetNumberField(TEXT("contact"),Contact);Row->SetNumberField(TEXT("ended"),Ended);Row->SetNumberField(TEXT("waves"),Waves);
    if(Rate==120||!Passed){auto Detail=MakeShared<FJsonObject>();Detail->SetArrayField(TEXT("frames"),Frames);LeapWrite(Detail,Out/FString::Printf(TEXT("%s-%.0f.json"),Names[Kind],Rate));}
    Cases.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("LEAP_CAMERA %s %s fps=%.0f relative_step=%.2f end=%.3f reason=%s"),Passed?TEXT("PASS"):TEXT("FAIL"),Names[Kind],Rate,MaxRelativeStep,Ended,*FirstFailure);
    for(auto* G:Geometry)G->GetOwner()->Destroy();
}
Report->SetArrayField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("failures"),Failures);
Report->SetStringField(TEXT("scope"),TEXT("native authority movement + actual camera/component/POV + native body animation; isolated profile; no GUI/render or real multiplayer"));
LeapWrite(Report,Out/TEXT("camera-audit.json"));
Tool->FinishLeapStrike();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
return Failures?1:0;
