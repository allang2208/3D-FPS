// Explicitly requested algorithm checks: isolated authority world and disposable profile.
auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;int32 Failures=0;
const auto MakeBox=[&](const FVector& Position,const FVector& Extent,const FRotator& Rotation)
{
    auto* Actor=World->SpawnActor<AActor>();auto* Shape=NewObject<UBoxComponent>(Actor);
    Actor->SetRootComponent(Shape);Shape->SetBoxExtent(Extent);Shape->SetCollisionObjectType(ECC_WorldStatic);
    Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Shape->SetCollisionResponseToAllChannels(ECR_Block);
    Shape->RegisterComponent();Actor->SetActorLocationAndRotation(Position,Rotation);return Shape;
};
const TCHAR* Names[]={TEXT("flat"),TEXT("uphill"),TEXT("downhill"),TEXT("steep_uphill"),TEXT("steep_downhill"),
    TEXT("wall"),TEXT("wall_removed"),TEXT("ceiling"),TEXT("floor_drops"),TEXT("source_removed"),TEXT("void"),TEXT("movement_disabled"),
    TEXT("wall_uphill"),TEXT("wall_downhill")};
const float Rates[]={30,60,120,144,0};
for(int32 Kind=0;Kind<UE_ARRAY_COUNT(Names);++Kind)for(float Rate:Rates)
{
    Tool->FinishLeapStrike();Tool->SetLeapAirborne(false);Pawn->WeaponState=EAKMWeaponState::Idle;
    // Reset the fixture's movement base before repositioning its floor between
    // cases; otherwise a previous lowered floor carries its reset delta into charge.
    Move->SetMovementMode(MOVE_None);
    auto Fresh=Model->Snapshot();Fresh.LeapStrikeCooldown=Fresh.LeapStrikeCooldownDuration=0.f;Fresh.Stamina=150.f;Model->CommitState(Fresh);
    Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Floor->SetActorLocation(FVector(0,0,-25));
    const float Pitch=Kind==1||Kind==12?7.f:Kind==2||Kind==13?-7.f:Kind==3?25.f:Kind==4?-25.f:0.f;
    UBoxComponent* Ramp=nullptr;UBoxComponent* Obstacle=nullptr;
    const FVector Normal=FRotator(Pitch,0,0).RotateVector(FVector::UpVector);
    const float Half=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const float Radius=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius();
    if(Pitch!=0.f)
    {
        Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Ramp=MakeBox(FVector(0,0,-25.f/Normal.Z),FVector(2000,2000,25),FRotator(Pitch,0,0));
    }
    Pawn->SetActorLocation(FVector(0,0,LeapStrike::StandingHeight(Half,Radius,Normal)),false);
    Move->SetMovementMode(MOVE_Walking);Move->StopMovementImmediately();PC->SetControlRotation(FRotator::ZeroRotator);Pawn->UpdateCamera(0.f);
    const float Reach=FMath::Abs(Pitch)>20.f?200.f:Pitch!=0.f?700.f:800.f;
    const FVector TargetFloor(Reach,0,FMath::Tan(FMath::DegreesToRadians(Pitch))*Reach);
    const FVector Target=TargetFloor+FVector(0,0,LeapStrike::StandingHeight(Half,Radius,Normal));
    FVector CheckedTarget,CheckedFloor,CheckedNormal;
    const bool ValidTarget=Tool->ValidateLeapLanding(FVector(FMath::RoundToDouble(Target.X),0,FMath::RoundToDouble(Target.Z)),CheckedTarget,CheckedFloor,CheckedNormal);
    Tool->LeapRequestDirection=FVector::ForwardVector;
    const bool Started=ValidTarget&&Tool->StartLeapStrike(Target,TargetFloor,Normal,World->GetTimeSeconds(),Model->LeapStrikeStats());
    int32 Waves=0;FVector WavePoint=FVector::ZeroVector;
    const auto SpawnHandle=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([&](AActor* Actor)
    {if(Actor->IsA<AWarhammerShockwave>()){++Waves;WavePoint=Actor->GetActorLocation();}}));
    float Time=0.f,Flight=0.f,Launch=-1.f,Contact=-1.f,End=-1.f,MaxStep=0.f,MaxStepRatio=0.f,LostForward=0.f;
    bool Triggered=false,Removed=false,Continuous=true,Monotonic=true,NoEarlyCancel=true,ContactOnFloor=false;
    FVector Landing=FVector::ZeroVector;float PreviousPose=0.f;
    float RemovedAtX=-1.f;
    for(int32 Frame=0;Started&&Frame<4000;++Frame)
    {
        const float Steps[]={1.f/120.f,1.f/45.f,1.f/60.f,.2f,1.f/144.f};
        const float Dt=Rate>0?1.f/Rate:Steps[Frame%5];Time+=Dt;++GFrameCounter;
        if(Tool->bLeapLaunched&&!Tool->bLeapLanded)Flight+=Dt;
        if(Tool->bLeapLaunched&&Flight>=(Kind==7?.05f:.15f)&&!Triggered)
        {
            Triggered=true;
            if(Kind==5||Kind==6||Kind==12||Kind==13)Obstacle=MakeBox(FVector(340,0,300),FVector(15,500,300),FRotator::ZeroRotator);
            if(Kind==7)Obstacle=MakeBox(FVector(440,0,Half*2+100),FVector(500,500,12),FRotator::ZeroRotator);
            if(Kind==8)Floor->SetActorLocation(FVector(0,0,-175));
            if(Kind==9)Move->RemoveRootMotionSource(LeapStrike::MotionName);
            if(Kind==10)Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            if(Kind==11)Move->DisableMovement();
        }
        if(Kind==6&&Obstacle&&Flight>=.5f&&!Removed)
        {Obstacle->SetCollisionEnabled(ECollisionEnabled::NoCollision);Removed=true;RemovedAtX=float(Pawn->GetActorLocation().X);}
        const FVector Before=Pawn->GetActorLocation();
        const FVector VelocityBefore=Move->Velocity;
        World->Tick(LEVELTICK_TimeOnly,Dt);Move->PerformMovement(Dt);Tool->TickLeapStrike(Dt);
        const float Step=FVector::Dist(Before,Pawn->GetActorLocation());MaxStep=FMath::Max(MaxStep,Step);
        const float Bound=(FMath::Max(1800.f,float(VelocityBefore.Size()))+FMath::Abs(Move->GetGravityZ())*Dt)*Dt+6.f;
        MaxStepRatio=FMath::Max(MaxStepRatio,Step/Bound);Continuous&=Step<=Bound;
        Monotonic&=Tool->LeapAge+1.e-5f>=PreviousPose;PreviousPose=Tool->LeapAge;
        if(Tool->bLeapLaunched&&Launch<0.f)Launch=Time;
        if(Tool->bLeapLanded&&Contact<0.f)
        {
            Contact=Flight;Landing=Pawn->GetActorLocation();FFindFloorResult Support;
            Move->ComputeFloorDist(Landing,10.f,10.f,Support,Radius);
            ContactOnFloor=Support.IsWalkableFloor()&&Support.GetDistanceToFloor()<=3.5f;
        }
        if(!Tool->bLeapStrike)
        {
            End=Time;NoEarlyCancel=Kind==11||Contact>=0.f||Flight>=LeapStrike::MaxAirTime-1.e-4f;break;
        }
    }
    World->RemoveOnActorSpawnedHandler(SpawnHandle);
    const bool ExpectContact=Kind!=10&&Kind!=11;
    const bool Landed=Contact>0.f&&Contact<=LeapStrike::MaxAirTime+.21f;
    const bool AtActualFloor=!ExpectContact||(FVector::DistSquared2D(WavePoint,Landing)<=FMath::Square(WarhammerHeavy::LandingForward+Radius+5.f)&&
        FMath::Abs(WavePoint.Z-(Pitch!=0.f?FMath::Tan(FMath::DegreesToRadians(Pitch))*WavePoint.X:Kind==8?-150.f:0.f))<3.f);
    const bool WallSafe=(Kind!=5&&Kind!=12&&Kind!=13)||(Landing.X<325.f&&WavePoint.X<325.f);
    const bool NoCatchUp=Kind!=6||(RemovedAtX>0.f&&FMath::Abs(Landing.X-RemovedAtX)<2.f);
    const bool ClearEndpoint=Kind>4||FMath::Abs(Landing.X-Reach)<5.f;
    // Removal is deferred by CharacterMovement until its next movement tick.
    Move->PerformMovement(1.f/120.f);
    const auto Remaining=Move->GetRootMotionSource(LeapStrike::MotionName);
    const bool MotionReleased=!Remaining||Remaining->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval);
    const bool Passed=Started&&Continuous&&Monotonic&&NoEarlyCancel&&WallSafe&&NoCatchUp&&ClearEndpoint&&AtActualFloor&&MotionReleased&&
        !Tool->bLeapStrike&&Move->MovementMode!=MOVE_Flying&&End>0.f&&End<=LeapStrike::Charge+LeapStrike::MaxAirTime+LeapStrike::Planted+LeapStrike::Recover+.65f&&
        (ExpectContact?(Landed&&ContactOnFloor&&Waves==1):(Contact<0.f&&Waves==0));
    if(!Passed)++Failures;
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Names[Kind]);Row->SetNumberField(TEXT("fps"),Rate);
    Row->SetBoolField(TEXT("passed"),Passed);Row->SetBoolField(TEXT("started"),Started);Row->SetBoolField(TEXT("target_valid"),ValidTarget);
    Row->SetBoolField(TEXT("continuous"),Continuous);Row->SetBoolField(TEXT("pose_monotonic"),Monotonic);Row->SetBoolField(TEXT("not_cancelled_early"),NoEarlyCancel);
    Row->SetBoolField(TEXT("at_actual_floor"),AtActualFloor);Row->SetBoolField(TEXT("contact_on_floor"),ContactOnFloor);
    Row->SetBoolField(TEXT("wall_safe"),WallSafe);Row->SetBoolField(TEXT("motion_released"),MotionReleased);
    Row->SetBoolField(TEXT("no_catch_up"),NoCatchUp);Row->SetBoolField(TEXT("clear_endpoint"),ClearEndpoint);
    Row->SetNumberField(TEXT("contact_after_launch"),Contact);Row->SetNumberField(TEXT("end"),End);Row->SetNumberField(TEXT("waves"),Waves);
    Row->SetNumberField(TEXT("max_step_cm"),MaxStep);Row->SetNumberField(TEXT("max_step_to_bound"),MaxStepRatio);
    Row->SetArrayField(TEXT("landing"),LeapVec(Landing));Row->SetArrayField(TEXT("impact"),LeapVec(WavePoint));
    Cases.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("LEAP_LANDING %s %s fps=%.0f flight=%.5f end=%.5f waves=%d"),Passed?TEXT("PASS"):TEXT("FAIL"),Names[Kind],Rate,Contact,End,Waves);
    if(Obstacle)Obstacle->GetOwner()->Destroy();if(Ramp)Ramp->GetOwner()->Destroy();
}
Report->SetArrayField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("failures"),Failures);
Report->SetStringField(TEXT("scope"),TEXT("native capsule/root-motion authority simulation; no GUI, renders, player saves or multiplayer acceptance"));
LeapWrite(Report,Out/TEXT("landing-audit.json"));
Tool->FinishLeapStrike();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
return Failures?1:0;
