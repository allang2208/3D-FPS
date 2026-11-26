// Inside ULeapStrikeAuditCommandlet::Main, using its isolated profile and world.
// Exercises production application APIs, root motion and the real leap lifecycle.
auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Checks;int32 Failures=0;
// UE 5.8 IsPlayerControlled reads PlayerState, not merely a player controller.
auto* PlayerState=World->SpawnActor<APlayerState>();PlayerState->SetOwner(PC);
PC->SetPlayerState(PlayerState);Pawn->SetPlayerState(PlayerState);
const auto Check=[&](const TCHAR* Name,bool Passed)
{
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("check"),Name);Row->SetBoolField(TEXT("passed"),Passed);
    Checks.Add(MakeShared<FJsonValueObject>(Row));if(!Passed)++Failures;
    UE_LOG(LogTemp,Display,TEXT("LEAP_CONTROL %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name);
};
auto* Status=UCombatStatusFormula::GetOrAdd(Pawn);
auto* Lock=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
if(!Lock){Lock=NewObject<UPlayerGuardBreakComponent>(Pawn);Pawn->AddInstanceComponent(Lock);Lock->RegisterComponent();}
auto* Fear=NewObject<UHandBrainFearComponent>(Pawn);Pawn->AddInstanceComponent(Fear);Fear->RegisterComponent();
auto* Capture=UBoundCongregateCaptureComponent::GetOrAdd(Pawn);
auto* Captor=World->SpawnActor<ABoundCongregate>(FVector(3000,3000,100),FRotator::ZeroRotator);
auto* Display=UStatusEffectsComponent::GetOrCreate(Pawn);
const auto HasTile=[&](FName Type){return Display->Snapshot().ContainsByPredicate([&](const auto& V){return V.Type==Type;});};
const auto Reset=[&]()
{
    Tool->CancelUse();Tool->SetLeapAirborne(false);Status->PurgeTransient();Pawn->WeaponState=EAKMWeaponState::Idle;
    auto Fresh=Model->Snapshot();Fresh.LeapStrikeCooldown=Fresh.LeapStrikeCooldownDuration=0.f;Fresh.Stamina=150.f;Model->CommitState(Fresh);
    PC->SetControlRotation(FRotator::ZeroRotator);
    Pawn->SetActorLocation(FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.4f),false);
    Move->SetMovementMode(MOVE_Walking);Move->StopMovementImmediately();Pawn->UpdateCamera(0.f);
};
Reset();Check(TEXT("fixture_is_player_controlled"),Pawn->IsPlayerControlled());
Check(TEXT("ground_has_no_immunity"),!CombatControl::IsImmune(Pawn));
Check(TEXT("charge_started"),Tool->BeginLeapStrike());Tool->TickLeapStrike(.25f);
Check(TEXT("charge_has_no_immunity"),!CombatControl::IsImmune(Pawn)&&!HasTile(TEXT("leapControlImmune")));
Status->AddBind(2.f);Tool->TickLeapStrike(.01f);
Check(TEXT("charge_bind_interrupts_before_takeoff"),!Tool->IsLeapStrikeActive()&&Status->BlocksMovement()&&!Tool->IsLeapControlImmune());
Reset();Check(TEXT("leap_started"),Tool->BeginLeapStrike());Tool->TickLeapStrike(LeapStrike::Charge);
Check(TEXT("takeoff_grants_immunity_and_buff"),Tool->bLeapLaunched&&CombatControl::IsImmune(Pawn)&&HasTile(TEXT("leapControlImmune")));
Status->AddStun(2.f);Status->AddStunWithExtension(1.f,1.f);
Check(TEXT("stun_and_extension_rejected"),!Status->IsStunned()&&!Lock->IsActive()&&!PC->IsMoveInputIgnored());
Lock->Apply(2.f);
Check(TEXT("direct_guard_break_rejected"),!Lock->IsActive()&&!PC->IsLookInputIgnored());
Status->AddBind(2.f);Status->AddPetrify(2.f);
Check(TEXT("bind_and_petrify_rejected"),!Status->BlocksMovement()&&!Status->IsPetrified());
Fear->Apply(Captor);
Check(TEXT("fear_rejected_before_input_lock"),Fear->Stacks==0&&!PC->IsMoveInputIgnored());
Check(TEXT("tentacle_capture_rejected"),Captor&&Capture&&!Capture->Capture(Captor)&&!Capture->IsHeld());
Move->ApplyImpactPush(FVector::ForwardVector,1000.f);
Check(TEXT("kick_displacement_rejected"),!Move->HasImpactPush()&&Tool->IsLeapStrikeActive());
UFleshHandPushComponent::Apply(Pawn,FVector::ForwardVector,100.f);
Check(TEXT("flesh_hand_displacement_rejected"),!Pawn->FindComponentByClass<UFleshHandPushComponent>());
Tool->SetLeapAirborne(false);UFleshHandPushComponent::Apply(Pawn,FVector::ForwardVector,100.f);
auto* PendingPush=Pawn->FindComponentByClass<UFleshHandPushComponent>();Tool->SetLeapAirborne(true);
const FVector BeforePush=Pawn->GetActorLocation();
PendingPush->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
Check(TEXT("preexisting_flesh_push_stops_in_air"),!PendingPush->IsComponentTickEnabled()&&Pawn->GetActorLocation().Equals(BeforePush));
const float BaseSpeed=Status->MovementMultiplier();
Status->AddSlow(3.f,.5f);Check(TEXT("slow_applies"),FMath::IsNearlyEqual(Status->MovementMultiplier(),BaseSpeed*.5f)&&HasTile(TEXT("slow")));
Status->PurgeTransient();Status->AddCripple(3.f);Check(TEXT("cripple_applies"),FMath::IsNearlyEqual(Status->MovementMultiplier(),BaseSpeed*.5f));
Status->PurgeTransient();Status->AddWaxSeal(3.f,.2f);Check(TEXT("wax_slow_applies"),FMath::IsNearlyEqual(Status->MovementMultiplier(),BaseSpeed*.8f));
Status->PurgeTransient();Status->AddChill(CombatChill::FreezeThreshold,3.f);
Check(TEXT("chill_slows_but_does_not_freeze"),Status->ChillCount()==CombatChill::FreezeThreshold&&!Status->IsFrozen()
    &&Status->MovementMultiplier()>0.f&&Status->MovementMultiplier()<BaseSpeed&&!HasTile(TEXT("frozen")));
Status->AddBleeding(Captor,1);Status->AddWeakness(1);
Check(TEXT("non_control_debuffs_remain"),HasTile(TEXT("bleed"))&&Status->WeaknessCount()==1&&!Status->IsImmune());
float Flight=0.f;
for(int32 I=0;I<100&&!Tool->bLeapLanded&&Tool->bLeapStrike;++I)
{
    constexpr float Dt=1.f/120.f;Flight+=Dt;++GFrameCounter;
    World->Tick(LEVELTICK_TimeOnly,Dt);Move->PerformMovement(Dt);Tool->TickLeapStrike(Dt);
}
Check(TEXT("slow_preserves_gravity_based_flight"),Tool->bLeapLanded&&FMath::IsNearlyEqual(Flight,Tool->LeapExpectedFlight,1.f/120.f+.002f));
Check(TEXT("landing_removes_immunity_and_buff"),!CombatControl::IsImmune(Pawn)&&!HasTile(TEXT("leapControlImmune")));
Check(TEXT("slow_survives_landing_without_queued_freeze"),Status->ChillCount()==CombatChill::FreezeThreshold&&!Status->IsFrozen());
Status->AddStun(1.f);Check(TEXT("stun_applies_after_landing"),Status->IsStunned()&&Lock->IsActive());
Reset();Status->AddChill(CombatChill::FreezeThreshold,2.f);Check(TEXT("freeze_works_outside_leap"),Status->IsFrozen());
Reset();Fear->Apply(Captor);Check(TEXT("fear_works_outside_leap"),Fear->Stacks>0&&PC->IsMoveInputIgnored());
Reset();Move->ApplyImpactPush(FVector::ForwardVector,100.f);Check(TEXT("push_works_outside_leap"),Move->HasImpactPush());
Move->RemoveRootMotionSource(TEXT("HeQueImpactPush"));
Reset();Check(TEXT("interruption_case_started"),Tool->BeginLeapStrike());Tool->TickLeapStrike(LeapStrike::Charge);Tool->FinishLeapStrike();
Check(TEXT("interrupted_fall_keeps_immunity"),Move->IsFalling()&&!Tool->IsLeapStrikeActive()&&CombatControl::IsImmune(Pawn));
Move->SetMovementMode(MOVE_Walking);
Check(TEXT("physical_ground_contact_ends_immunity_immediately"),!CombatControl::IsImmune(Pawn)&&!HasTile(TEXT("leapControlImmune")));
Tool->TickComponent(0.f,LEVELTICK_TimeOnly,nullptr);Move->SetMovementMode(MOVE_Falling);
Check(TEXT("ordinary_jump_does_not_reactivate_buff"),!CombatControl::IsImmune(Pawn));
Reset();Tool->BeginLeapStrike();Tool->TickLeapStrike(LeapStrike::Charge);Move->DisableMovement();
Check(TEXT("disabled_movement_ends_immunity"),!CombatControl::IsImmune(Pawn));
Reset();Report->SetArrayField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("failures"),Failures);Report->SetNumberField(TEXT("flight_seconds"),Flight);
Report->SetStringField(TEXT("scope"),TEXT("isolated authority fixture; no GUI, screenshots, player saves or multiplayer acceptance"));
LeapWrite(Report,Out/TEXT("control-audit.json"));
GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
return Failures?1:0;
