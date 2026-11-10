// Direct high-roof casts, physical acceleration, finite cancellation, and RMS correction state.
auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases,Checks;int32 Failures=0;
const auto Check=[&](const TCHAR* Name,bool Passed)
{
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("check"),Name);Row->SetBoolField(TEXT("passed"),Passed);
    Checks.Add(MakeShared<FJsonValueObject>(Row));if(!Passed)++Failures;
    UE_LOG(LogTemp,Display,TEXT("LEAP_BALLISTIC_CHECK %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name);
};
const auto MakeBox=[&](FVector P,FVector Extent)
{
    auto* A=World->SpawnActor<AActor>();auto* B=NewObject<UBoxComponent>(A);A->SetRootComponent(B);
    B->SetBoxExtent(Extent);B->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    B->SetCollisionObjectType(ECC_WorldStatic);B->SetCollisionResponseToAllChannels(ECR_Block);B->RegisterComponent();A->SetActorLocation(P);return B;
};
auto* Roof=MakeBox(FVector::ZeroVector,FVector(500,1500,20));
auto* Destination=MakeBox(FVector::ZeroVector,FVector(200,1500,20));
const float Half=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),Radius=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius();
const float Standing=LeapStrike::StandingHeight(Half,Radius,FVector::UpVector);
const auto Reset=[&](float Difference,float GravityScale)
{
    Tool->FinishLeapStrike();Tool->SetLeapAirborne(false);Move->SetMovementMode(MOVE_None);Move->GravityScale=GravityScale;
    Pawn->WeaponState=EAKMWeaponState::Idle;
    auto Fresh=Model->Snapshot();Fresh.LeapStrikeCooldown=Fresh.LeapStrikeCooldownDuration=0.f;Fresh.Stamina=150;Model->CommitState(Fresh);
    const float StartZ=FMath::Max(3000.f,-Difference+1000.f);
    // Stand at the roof edge. A fixed 8 m target far below a broad rooftop can
    // be physically unreachable without first clearing that rooftop.
    Roof->GetOwner()->SetActorLocation(FVector(-455,0,StartZ-20));
    Destination->GetOwner()->SetActorLocation(FVector(800,0,StartZ+Difference-20));
    Pawn->SetActorLocation(FVector(0,0,StartZ+Standing),false);Move->SetMovementMode(MOVE_Walking);Move->StopMovementImmediately();
    PC->SetControlRotation(FRotator::ZeroRotator);Pawn->UpdateCamera(0.f);return StartZ;
};
const float Differences[]={300,121,120,119,0,-119,-120,-121,-300,-800,-1000,-2000,-3000,-10000,-20000};
const float Rates[]={30,60,120,144,0};
for(float Difference:Differences)for(float Rate:Rates)
{
    const float StartZ=Reset(Difference,2.04f);
    FVector Checked,FloorHit,Normal,Preview,PreviewFloor,PreviewNormal;
    const bool Visible=Tool->SolveLeapTarget(FVector::ForwardVector,Preview,PreviewFloor,PreviewNormal,true,false);
    const FVector TargetFloor(800,0,StartZ+Difference),Target=TargetFloor+FVector(0,0,Standing);
    const bool Accepted=Tool->ValidateLeapLanding(FVector(800,0,FMath::RoundToDouble(Target.Z)),Checked,FloorHit,Normal);
    LeapStrike::FTrajectory Path;
    const FVector Start=Pawn->GetActorLocation();
    const bool Solved=LeapStrike::SolveTrajectory(Start,Target,Move->GetGravityZ(),Move->GetPhysicsVolume()->TerminalVelocity,Path);
    Tool->LeapRequestDirection=FVector::ForwardVector;
    const bool Started=Accepted&&Solved&&Tool->StartLeapStrike(Target,TargetFloor,FVector::UpVector,World->GetTimeSeconds(),Model->LeapStrikeStats());
    int32 Waves=0;FVector Impact=FVector::ZeroVector;
    const auto Handle=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([&](AActor* A)
    {if(A->IsA<AWarhammerShockwave>()){++Waves;Impact=A->GetActorLocation();}}));
    float Elapsed=0,Flight=0,Contact=-1,MaxAccelerationError=0,MaxCurveError=0,HorizontalAtOldDeadline=0;
    bool HadMotion=false,GoodStep=true,EverAirborne=false;FVector Landing=FVector::ZeroVector;
    for(int32 I=0;Started&&I<3000;++I)
    {
        const float Steps[]={1.f/120.f,1.f/45.f,1.f/60.f,.2f,1.f/144.f};
        const float Dt=Rate>0?1.f/Rate:Steps[I%5];Elapsed+=Dt;++GFrameCounter;
        const bool Flying=Tool->bLeapLaunched&&!Tool->bLeapLanded;
        if(Flying)Flight+=Dt;
        const FVector Before=Pawn->GetActorLocation(),BeforeVelocity=Move->Velocity;
        const float G=Move->GetGravityZ();
        World->Tick(LEVELTICK_TimeOnly,Dt);Move->PerformMovement(Dt);Tool->TickLeapStrike(Dt);
        const FVector After=Pawn->GetActorLocation();
        GoodStep&=FVector::Dist(Before,After)<=(FMath::Max(1800.f,float(BeforeVelocity.Size()))+FMath::Abs(G)*Dt)*Dt+6.f;
        if(Flying&&!Tool->bLeapLanded)
        {
            EverAirborne=true;
            if(HadMotion)
            {
                const float ExpectedZ=FMath::Max(-Move->GetPhysicsVolume()->TerminalVelocity,float(BeforeVelocity.Z)+G*Dt);
                MaxAccelerationError=FMath::Max(MaxAccelerationError,FMath::Abs(float(Move->Velocity.Z)-ExpectedZ));
            }
            HadMotion=true;
            MaxCurveError=FMath::Max(MaxCurveError,float(FVector::Dist(After,Path.Position(Start,Flight))));
            if(Flight>.8f&&Flight<1.2f)HorizontalAtOldDeadline=float(Move->Velocity.Size2D());
        }
        if(Tool->bLeapLanded&&Contact<0){Contact=Flight;Landing=After;}
        if(!Tool->bLeapStrike)break;
        if(Elapsed>LeapStrike::MaxAirTime+2.f)break;
    }
    World->RemoveOnActorSpawnedHandler(Handle);
    const bool Cadence=Difference>=-LeapStrike::StandardDrop?FMath::IsNearlyEqual(Path.Duration,LeapStrike::Flight,.002f):Path.Duration>LeapStrike::Flight;
    const bool Passed=Cadence&&Visible&&Accepted&&Started&&EverAirborne&&GoodStep&&Contact>0&&Waves==1&&
        !Tool->bLeapStrike&&Move->IsMovingOnGround()&&FMath::Abs(Landing.X-800.f)<6.f&&
        FMath::Abs(Impact.Z-(StartZ+Difference))<3.f&&MaxAccelerationError<1.f&&MaxCurveError<8.f;
    if(!Passed)++Failures;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("height_cm"),Difference);Row->SetNumberField(TEXT("fps"),Rate);
    Row->SetBoolField(TEXT("passed"),Passed);Row->SetBoolField(TEXT("preview_valid"),Visible);Row->SetBoolField(TEXT("server_accepts"),Accepted);
    Row->SetBoolField(TEXT("started"),Started);Row->SetBoolField(TEXT("continuous"),GoodStep);Row->SetNumberField(TEXT("waves"),Waves);
    Row->SetNumberField(TEXT("contact_time"),Contact);Row->SetNumberField(TEXT("planned_flight"),Path.Duration);
    Row->SetBoolField(TEXT("standard_or_extended_flight"),Cadence);
    Row->SetNumberField(TEXT("max_velocity_error_cm_s"),MaxAccelerationError);Row->SetNumberField(TEXT("max_curve_error_cm"),MaxCurveError);
    Row->SetNumberField(TEXT("horizontal_velocity_after_075s"),HorizontalAtOldDeadline);Row->SetArrayField(TEXT("landing"),LeapVec(Landing));
    Cases.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("LEAP_BALLISTIC %s dz=%.0f fps=%.0f visible=%d accepted=%d contact=%.4f planned=%.4f x=%.3f v_error=%.5f curve_error=%.3f waves=%d"),
        Passed?TEXT("PASS"):TEXT("FAIL"),Difference,Rate,Visible,Accepted,Contact,Path.Duration,Landing.X,MaxAccelerationError,MaxCurveError,Waves);
}

Reset(-1000,2.04f);LeapStrike::FTrajectory NormalPath,HalfGravityPath;
const FVector Aim(800,0,Pawn->GetActorLocation().Z-1000.f);
Check(TEXT("half_gravity_changes_the_solved_flight"),
    LeapStrike::SolveTrajectory(Pawn->GetActorLocation(),Aim,-1999.2f,4000.f,NormalPath)&&
    LeapStrike::SolveTrajectory(Pawn->GetActorLocation(),Aim,-999.6f,4000.f,HalfGravityPath)&&HalfGravityPath.Duration>NormalPath.Duration);
LeapStrike::FTrajectory Invalid;
Check(TEXT("zero_gravity_rejects_grounded_ballistic_cast"),!LeapStrike::SolveTrajectory(Pawn->GetActorLocation(),Aim,0.f,4000.f,Invalid));

FRootMotionSource_FPSLeap State;State.InstanceName=LeapStrike::MotionName;State.Priority=1200;State.Duration=LeapStrike::MaxAirTime;
State.StartLocation=FVector(0,0,3000);State.TargetLocation=FVector(800,0,1000);State.SetTime(.6f);
State.LinearVelocity=FVector(120,0,-350);State.bLaunched=true;
TArray<uint8> Bytes;FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive WriteArchive(Writer,false);bool Written=false;
State.NetSerialize(WriteArchive,nullptr,Written);
FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive ReadArchive(Reader,true);FRootMotionSource_FPSLeap Received;bool Read=false;
Received.NetSerialize(ReadArchive,nullptr,Read);
Check(TEXT("replicated_source_preserves_collision_velocity"),Written&&Read&&State.MatchesAndHasSameState(&Received)&&Received.bRestoreVelocity);
FRootMotionSource_FPSLeap Replayed=State;Replayed.LinearVelocity=FVector(1000,0,500);
Check(TEXT("authority_correction_replaces_predicted_velocity"),Replayed.UpdateStateFrom(&Received)&&Replayed.LinearVelocity.Equals(Received.LinearVelocity)&&Replayed.bRestoreVelocity);

Reset(0,2.04f);Move->PerformMovement(.001f);Pawn->SetActorLocation(Pawn->GetActorLocation()+FVector(0,0,200));
Move->SetMovementMode(MOVE_Falling);auto Restored=MakeShared<FRootMotionSource_FPSLeap>(Received);
Move->ApplyRootMotionSource(Restored);const FVector RestorePosition=Pawn->GetActorLocation();Move->PerformMovement(.02f);
Check(TEXT("restored_source_resumes_velocity_without_relaunch_or_snap"),
    FMath::Abs(Move->Velocity.X-120.f)<.1f&&FMath::Abs(Move->Velocity.Z-(-350.f+Move->GetGravityZ()*.02f))<1.f&&
    FVector::Dist(RestorePosition,Pawn->GetActorLocation())<12.f);
Move->RemoveRootMotionSource(LeapStrike::MotionName);

const TCHAR* GravityNames[]={TEXT("native_half_gravity"),TEXT("native_gravity_reduces_midflight"),
    TEXT("native_gravity_increases_midflight"),TEXT("native_low_terminal_velocity")};
for(int32 Variant=0;Variant<4;++Variant)
{
    const float StartZ=Reset(-1000,Variant==0?1.02f:2.04f);
    auto* Volume=Move->GetPhysicsVolume();const float OriginalTerminal=Volume->TerminalVelocity;
    if(Variant==3)Volume->TerminalVelocity=1500.f;
    Tool->LeapRequestDirection=FVector::ForwardVector;
    const bool Started=Tool->StartLeapStrike(FVector(800,0,StartZ-1000+Standing),FVector(800,0,StartZ-1000),
        FVector::UpVector,World->GetTimeSeconds(),Model->LeapStrikeStats());
    int32 Waves=0;const auto Handle=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([&](AActor* A)
    {if(A->IsA<AWarhammerShockwave>())++Waves;}));
    float Flight=0,MaxError=0;bool BeganMoving=false,Changed=false;
    for(int32 I=0;Started&&Tool->bLeapStrike&&I<1800;++I)
    {
        constexpr float Dt=1.f/120.f;++GFrameCounter;
        const bool Flying=Tool->bLeapLaunched&&!Tool->bLeapLanded;
        if(Flying)Flight+=Dt;
        if(Flying&&!Changed&&Flight>.3f)
        {Changed=true;if(Variant==1)Move->GravityScale=1.02f;if(Variant==2)Move->GravityScale=4.08f;}
        const float Expected=FMath::Max(-Volume->TerminalVelocity,float(Move->Velocity.Z)+Move->GetGravityZ()*Dt);
        World->Tick(LEVELTICK_TimeOnly,Dt);Move->PerformMovement(Dt);Tool->TickLeapStrike(Dt);
        if(Flying&&!Tool->bLeapLanded)
        {if(BeganMoving)MaxError=FMath::Max(MaxError,FMath::Abs(float(Move->Velocity.Z)-Expected));BeganMoving=true;}
    }
    World->RemoveOnActorSpawnedHandler(Handle);Volume->TerminalVelocity=OriginalTerminal;
    Check(GravityNames[Variant],Started&&Waves==1&&!Tool->bLeapStrike&&Move->IsMovingOnGround()&&MaxError<1.f);
}

const float Z=Reset(0,2.04f);Tool->LeapRequestDirection=FVector::ForwardVector;
Tool->StartLeapStrike(FVector(800,0,Z+Standing),FVector(800,0,Z),FVector::UpVector,World->GetTimeSeconds(),Model->LeapStrikeStats());
Tool->TickLeapStrike(LeapStrike::Charge);
for(int32 I=0;I<20;++I){++GFrameCounter;Move->PerformMovement(.02f);Tool->TickLeapStrike(.02f);}
const FVector BeforeCancel=Move->Velocity;Tool->FinishLeapStrike();++GFrameCounter;Move->PerformMovement(.01f);
Check(TEXT("cancelling_in_air_does_not_zero_fall_velocity"),!Tool->bLeapStrike&&Move->IsFalling()&&FMath::Abs(Move->Velocity.Z-(BeforeCancel.Z+Move->GetGravityZ()*.01f))<1.f);

Reset(0,2.04f);Tool->StartLeapStrike(FVector(800,0,Z+Standing),FVector(800,0,Z),FVector::UpVector,World->GetTimeSeconds(),Model->LeapStrikeStats());
Tool->TickLeapStrike(LeapStrike::Charge);
for(int32 I=0;I<30&&Tool->bLeapStrike;++I){++GFrameCounter;Tool->TickLeapStrike(.05f);}
Check(TEXT("nonadvancing_movement_releases_skill"),!Tool->bLeapStrike&&Move->MovementMode!=MOVE_Flying);

Report->SetArrayField(TEXT("cases"),Cases);Report->SetArrayField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("failures"),Failures);
Report->SetStringField(TEXT("scope"),TEXT("native authority physics plus serialized/replayed RMS state; not two-client gameplay acceptance"));
LeapWrite(Report,Out/TEXT("ballistic-audit.json"));
Tool->FinishLeapStrike();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
return Failures?1:0;
