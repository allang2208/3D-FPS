// User-requested diagnosis of the existing algorithm, including unsupported heights.
// Record shortcomings as findings, separately from fixture/stability failures.
auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Selection,Flights;
int32 Failures=0,LostImpactCases=0;
constexpr float RoofZ=3000.f,Reach=800.f;
const auto MakeBox=[&](const FVector& Position,const FVector& Extent)
{
    auto* Actor=World->SpawnActor<AActor>();auto* Shape=NewObject<UBoxComponent>(Actor);
    Actor->SetRootComponent(Shape);Shape->SetBoxExtent(Extent);Shape->SetCollisionObjectType(ECC_WorldStatic);
    Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Shape->SetCollisionResponseToAllChannels(ECR_Block);
    Shape->RegisterComponent();Actor->SetActorLocation(Position);return Shape;
};
auto* Roof=MakeBox(FVector(-200,0,RoofZ-20),FVector(500,1500,20)); // edge at X=300
auto* Destination=MakeBox(FVector(800,0,RoofZ-20),FVector(200,1500,20));
const float Half=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
const float Radius=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius();
const float Standing=LeapStrike::StandingHeight(Half,Radius,FVector::UpVector);
const auto Reset=[&](float TargetHeight)
{
    Tool->FinishLeapStrike();Tool->SetLeapAirborne(false);Move->SetMovementMode(MOVE_None);
    Pawn->WeaponState=EAKMWeaponState::Idle;
    auto Fresh=Model->Snapshot();Fresh.LeapStrikeCooldown=Fresh.LeapStrikeCooldownDuration=0.f;Fresh.Stamina=150;Model->CommitState(Fresh);
    Destination->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Destination->GetOwner()->SetActorLocation(FVector(800,0,TargetHeight-20));
    Pawn->SetActorLocation(FVector(0,0,RoofZ+Standing),false);
    Move->SetMovementMode(MOVE_Walking);Move->StopMovementImmediately();
    PC->SetControlRotation(FRotator::ZeroRotator);Pawn->UpdateCamera(0.f);
};
const float Heights[]={-2000,-1000,-500,-200,-123,-121,-120,-119,-100,0,100,119,120,121,123,200,500,1000,2000};
for(float Height:Heights)
{
    Reset(RoofZ+Height);FVector Target,Surface,Normal,ShortTarget,ShortFloor,ShortNormal,Checked,CheckedFloor,CheckedNormal;
    const bool Preview=Tool->SolveLeapTarget(FVector::ForwardVector,Target,Surface,Normal,false,false);
    const bool Clear=Preview&&Tool->IsLeapPathClear(Target);
    const bool Shortened=Tool->SolveLeapTarget(FVector::ForwardVector,ShortTarget,ShortFloor,ShortNormal,true,true);
    const FVector Requested(Reach,0,RoofZ+Height+Standing);
    const bool Accepted=Tool->ValidateLeapLanding(Requested,Checked,CheckedFloor,CheckedNormal);
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("floor_difference_cm"),Height);
    Row->SetBoolField(TEXT("preview_has_floor"),Preview);Row->SetBoolField(TEXT("preview_path_clear"),Clear);
    Row->SetBoolField(TEXT("server_accepts_requested_floor"),Accepted);Row->SetBoolField(TEXT("direct_solver_finds_target"),Shortened);
    if(Preview)Row->SetArrayField(TEXT("preview_floor"),LeapVec(Surface));
    if(Shortened)Row->SetArrayField(TEXT("direct_solver_floor"),LeapVec(ShortFloor));
    Row->SetBoolField(TEXT("direct_solver_falls_back_to_start_roof"),Shortened&&FMath::Abs(ShortFloor.Z-RoofZ)<1.f&&ShortFloor.X<=300.f);
    Selection.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("LEAP_HEIGHT_SELECT dz=%.0f preview=%d server=%d fallback=%d"),Height,Clear,Accepted,Shortened&&!Clear);
}
const TCHAR* Names[]={TEXT("same_height_roofs"),TEXT("roof_up_100cm"),TEXT("roof_down_100cm"),
    TEXT("destination_drops_300cm"),TEXT("destination_drops_800cm"),TEXT("destination_drops_1000cm"),
    TEXT("destination_drops_2000cm"),TEXT("destination_removed_30m_fall"),TEXT("wall_above_30m_gap")};
const float Rates[]={30,60,120,144,0};
for(int32 Kind=0;Kind<UE_ARRAY_COUNT(Names);++Kind)for(float Rate:Rates)
{
    const float Height=Kind==1?100.f:Kind==2?-100.f:0.f;
    Reset(RoofZ+Height);UBoxComponent* Obstacle=nullptr;
    FVector Checked,CheckedFloor,CheckedNormal;
    const FVector TargetFloor(Reach,0,RoofZ+Height),Target=TargetFloor+FVector(0,0,Standing);
    const bool ValidTarget=Tool->ValidateLeapLanding(Target,Checked,CheckedFloor,CheckedNormal);
    Tool->LeapRequestDirection=FVector::ForwardVector;
    const bool Started=ValidTarget&&Tool->StartLeapStrike(Target,TargetFloor,FVector::UpVector,World->GetTimeSeconds(),Model->LeapStrikeStats());
    int32 Waves=0;FVector Impact=FVector::ZeroVector;
    const auto SpawnHandle=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([&](AActor* Actor)
    {if(Actor->IsA<AWarhammerShockwave>()){++Waves;Impact=Actor->GetActorLocation();}}));
    float Time=0,Flight=0,Contact=-1,Finished=-1,PhysicalLanding=-1,MaxStep=0;
    bool Changed=false,Continuous=true,FinishedAirborne=false;
    FVector EndPosition=FVector::ZeroVector,EndVelocity=FVector::ZeroVector,AfterEndVelocity=FVector::ZeroVector;
    FVector PreDropVelocity=FVector::ZeroVector,DropVelocity=FVector::ZeroVector;
    bool SeenVerticalDrop=false,RecordedAfterEnd=false;
    TArray<TSharedPtr<FJsonValue>> Frames;
    for(int32 Frame=0;Started&&Frame<1800;++Frame)
    {
        const float Steps[]={1.f/120.f,1.f/45.f,1.f/60.f,.2f,1.f/144.f};
        const float Dt=Rate>0?1.f/Rate:Steps[Frame%5];Time+=Dt;++GFrameCounter;
        if(Tool->bLeapLaunched||Finished>=0.f)Flight+=Dt;
        if(Tool->bLeapLaunched&&Flight>=.15f&&!Changed)
        {
            Changed=true;
            const float Drop=Kind==3?300.f:Kind==4?800.f:Kind==5?1000.f:Kind==6?2000.f:0.f;
            if(Drop>0)Destination->GetOwner()->SetActorLocation(FVector(800,0,RoofZ-Drop-20));
            if(Kind==7)Destination->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            if(Kind==8)Obstacle=MakeBox(FVector(500,0,1750),FVector(20,1500,1750));
        }
        const FVector Before=Pawn->GetActorLocation(),VelocityBefore=Move->Velocity;
        const auto Source=Move->GetRootMotionSource(LeapStrike::MotionName);
        const float SourceTime=Source?Source->GetTime():-1.f;
        const bool WasFinished=Finished>=0.f;
        World->Tick(LEVELTICK_TimeOnly,Dt);Move->PerformMovement(Dt);
        if(WasFinished&&!RecordedAfterEnd){AfterEndVelocity=Move->Velocity;RecordedAfterEnd=true;}
        if(!SeenVerticalDrop&&SourceTime>=LeapStrike::Flight)
        {PreDropVelocity=VelocityBefore;DropVelocity=Move->Velocity;SeenVerticalDrop=true;}
        const float Step=FVector::Dist(Before,Pawn->GetActorLocation());MaxStep=FMath::Max(MaxStep,Step);
        const float SpeedBound=FMath::Max(1600.f,float(VelocityBefore.Size()))+FMath::Abs(Move->GetGravityZ())*Dt;
        Continuous&=Step<=SpeedBound*Dt+6.f;
        if(Tool->bLeapStrike)Tool->TickLeapStrike(Dt);
        if(Tool->bLeapAirborne&&!Tool->IsLeapControlImmune())Tool->SetLeapAirborne(false);
        if(Contact<0.f&&Tool->bLeapLanded)Contact=Flight;
        if(Finished<0.f&&!Tool->bLeapStrike)
        {Finished=Flight;FinishedAirborne=!Move->IsMovingOnGround();EndPosition=Pawn->GetActorLocation();EndVelocity=Move->Velocity;}
        if(PhysicalLanding<0.f&&Changed&&Flight>0.f&&Move->IsMovingOnGround())PhysicalLanding=Flight;
        if(Rate==120)
        {
            auto F=MakeShared<FJsonObject>();F->SetNumberField(TEXT("time"),Time);F->SetNumberField(TEXT("flight_time"),Flight);
            F->SetArrayField(TEXT("position"),LeapVec(Pawn->GetActorLocation()));F->SetArrayField(TEXT("velocity"),LeapVec(Move->Velocity));
            F->SetNumberField(TEXT("pose_time"),Tool->LeapAge);F->SetNumberField(TEXT("mode"),Move->MovementMode);
            F->SetBoolField(TEXT("skill_active"),Tool->bLeapStrike);F->SetNumberField(TEXT("waves"),Waves);
            Frames.Add(MakeShared<FJsonValueObject>(F));
        }
        if(Finished>=0.f&&PhysicalLanding>=0.f)break;
        if(Time>12.f)break;
    }
    World->RemoveOnActorSpawnedHandler(SpawnHandle);
    const bool LostImpact=FinishedAirborne&&PhysicalLanding>Finished&&Waves==0;
    if(LostImpact)++LostImpactCases;
    const bool Stable=Started&&Continuous&&Finished>0.f&&Finished<=LeapStrike::MaxAirTime+LeapStrike::Planted+LeapStrike::Recover+.5f&&PhysicalLanding>0.f&&Waves==1&&!FinishedAirborne;
    if(!Stable)++Failures;
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Names[Kind]);Row->SetNumberField(TEXT("fps"),Rate);
    Row->SetBoolField(TEXT("started"),Started);Row->SetBoolField(TEXT("stability_checks_passed"),Stable);Row->SetBoolField(TEXT("continuous_positions"),Continuous);
    Row->SetBoolField(TEXT("skill_finished_in_air"),FinishedAirborne);Row->SetBoolField(TEXT("landed_without_attack_after_timeout"),LostImpact);
    Row->SetNumberField(TEXT("skill_contact_time"),Contact);Row->SetNumberField(TEXT("skill_end_time"),Finished);Row->SetNumberField(TEXT("physical_landing_time"),PhysicalLanding);
    Row->SetNumberField(TEXT("waves"),Waves);Row->SetNumberField(TEXT("max_step_cm"),MaxStep);
    Row->SetArrayField(TEXT("skill_end_position"),LeapVec(EndPosition));Row->SetArrayField(TEXT("physical_landing_position"),LeapVec(Pawn->GetActorLocation()));
    Row->SetArrayField(TEXT("impact"),LeapVec(Impact));Row->SetArrayField(TEXT("velocity_before_vertical_phase"),LeapVec(PreDropVelocity));
    Row->SetArrayField(TEXT("velocity_in_vertical_phase"),LeapVec(DropVelocity));Row->SetArrayField(TEXT("velocity_at_skill_end"),LeapVec(EndVelocity));
    Row->SetArrayField(TEXT("velocity_next_move_after_end"),LeapVec(AfterEndVelocity));
    if(Rate==120){auto Detail=MakeShared<FJsonObject>();Detail->SetArrayField(TEXT("frames"),Frames);LeapWrite(Detail,Out/(FString(Names[Kind])+TEXT("-120fps.json")));}
    Flights.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("LEAP_HEIGHT_FLIGHT %s fps=%.0f stable=%d contact=%.3f end=%.3f physical_land=%.3f waves=%d lost_attack=%d"),
        Names[Kind],Rate,Stable,Contact,Finished,PhysicalLanding,Waves,LostImpact);
    if(Obstacle)Obstacle->GetOwner()->Destroy();
}
Report->SetArrayField(TEXT("target_selection"),Selection);Report->SetArrayField(TEXT("flights"),Flights);
Report->SetNumberField(TEXT("stability_failures"),Failures);Report->SetNumberField(TEXT("landed_without_attack_cases"),LostImpactCases);
Report->SetNumberField(TEXT("world_gravity_cm_s2"),World->GetGravityZ());Report->SetNumberField(TEXT("character_gravity_cm_s2"),Move->GetGravityZ());
Report->SetStringField(TEXT("scope"),TEXT("ballistic repair regression; every physical landing must attack once; isolated authority, no GUI or user saves"));
LeapWrite(Report,Out/TEXT("height-audit.json"));
Tool->FinishLeapStrike();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
return Failures?1:0;
