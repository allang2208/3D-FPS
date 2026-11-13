#include "ProductionToolComponent.h"
#include "../Weapons/PojunGrip.h"
#include "ProductionToolMeshComponent.h"
#include "WarhammerShockwave.h"
#include "WarhammerAudioPaths.h"
#include "../Skills/LeapStrikeMotion.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Movement/FPSLeapRootMotionSource.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/StatusEffectsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PhysicsVolume.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
bool LeapAvailable(AFPSGAMECharacter* Pawn,const UColdSteelStatusModel* Model,bool Continuing=false)
{
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const auto* Movement=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    return Pawn&&PC&&Item&&PojunGrip::UsesHammerMotion(*Item)&&
        Model->MasteryProgress(TEXT("leapStrike")).Level>0&&(!Health||!Health->IsDead())&&
        !Pawn->IsTraversing()&&!Pawn->IsDodging()&&!Pawn->IsSliding()&&!Pawn->IsCastBlockingLeftHandAction()&&
        (!Sword||(!Sword->IsGuarding()&&!Sword->IsPojunChainOccupied()))&&
        !(Status&&Status->BlocksMovement())&&!(Movement&&Movement->HasImpactPush())&&
        !UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&
        !(Continuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC));
}
double LeapClock(const UWorld* World)
{const auto* State=World->GetGameState();return State?State->GetServerWorldTimeSeconds():World->GetTimeSeconds();}
void ApplyLeapMotion(UCharacterMovementComponent* Move,const FVector& Start,const FVector& Target,uint32 Serial)
{
    auto Motion=MakeShared<FRootMotionSource_FPSLeap>();
    Motion->InstanceName=LeapStrike::MotionName;Motion->Priority=1200;
    Motion->AccumulateMode=ERootMotionAccumulateMode::Override;
    Motion->StartLocation=Start;Motion->TargetLocation=Target;Motion->Duration=LeapStrike::MaxAirTime;
    Motion->CastSerial=Serial;
    Motion->FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::MaintainLastRootMotionVelocity;
    Move->SetMovementMode(MOVE_Falling);Move->ApplyRootMotionSource(Motion);
}
bool LeapGround(UWorld* World,APawn* Pawn,const FVector& Top,const FVector& Bottom,FHitResult& Hit)
{
    FCollisionQueryParams Q(SCENE_QUERY_STAT(LeapStrikeFloor),false,Pawn);
    for(int32 I=0;I<12;++I)
    {
        if(!World->LineTraceSingleByChannel(Hit,Top,Bottom,ECC_Visibility,Q))return false;
        auto* Actor=Hit.GetActor();
        if(!Actor||(!Actor->IsA<APawn>()&&!Actor->FindComponentByClass<UMonsterCombatComponent>()))return true;
        Q.AddIgnoredActor(Actor);
    }
    return false;
}
}

FString UProductionToolComponent::LeapStrikeStatusText(bool IncludeNotice) const
{
    if(!IsWarhammerEquipped())return TEXT("需双手锤或破军长柄");
    if(bLeapPending)return TEXT("准备中");
    if(bLeapStrike)return LeapAge<LeapStrike::Charge?TEXT("蓄力中"):LeapAge<LeapStrike::Land?TEXT("跃击中"):TEXT("收势中");
    if(bLeapAimPreview)return !LeapAimMaterial?TEXT("范围准备中"):bLeapPreviewValid?TEXT("松开跃击"):TEXT("无可达落点");
    auto* Pawn=Character.Get();const auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!LeapAvailable(Pawn,Model)||!CanUse()||Pawn->bIsCrouched)return TEXT("暂不可用");
    if(!Pawn->GetCharacterMovement()->IsMovingOnGround())return TEXT("需站在地面");
    if(IsBusy()||Pawn->IsWeaponBusy(true))return TEXT("动作占用");
    if(Model->LeapStrikeCooldown()>0.f)return TEXT("冷却中");
    if(!Model->CanSpendStamina(Model->LeapStrikeStats().StaminaCost))return TEXT("体力不足");
    if(!Motions.FindRef(TEXT("LeapStrike")))return TEXT("动作准备中");
    if(IncludeNotice&&GetWorld()->GetTimeSeconds()<LeapNoticeUntil)return TEXT("无可达落点");
    return FString();
}

float UProductionToolComponent::LeapStartFloorZ() const
{
    const auto* Pawn=Character.Get();if(!Pawn)return 0.f;
    const auto* Move=Pawn->GetCharacterMovement();
    if(Move->CurrentFloor.IsWalkableFloor())return float(Move->CurrentFloor.HitResult.ImpactPoint.Z);
    return float(Pawn->GetActorLocation().Z)-Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-LeapStrike::FloorClearance;
}

bool UProductionToolComponent::IsLeapFloorHeightAllowed(float FloorZ) const
{
    const float Difference=FloorZ-LeapStartFloorZ();
    return Difference<=LeapStrike::MaxRise+LeapStrike::TargetTolerance&&Difference>=-LeapStrike::MaxDrop-LeapStrike::TargetTolerance;
}

bool UProductionToolComponent::SolveLeapTarget(const FVector& Direction,FVector& Target,FVector& Floor,FVector& Normal,
    bool CheckPath,bool AllowShorten) const
{
    const auto* Pawn=Character.Get();if(!Pawn||Direction.ContainsNaN()||Direction.IsNearlyZero())return false;
    const auto* Model=ColdSteelAuthority::ForPawn(Pawn);if(!Model)return false;
    const float LeapReach=Model->LeapStrikeBaseStats().ReachCM;
    const auto* Capsule=Pawn->GetCapsuleComponent();const auto* Move=Pawn->GetCharacterMovement();
    const FVector Start=Pawn->GetActorLocation(),Eye=Pawn->GetMeleeAimTransform().GetLocation();
    const FVector Forward=Direction.GetSafeNormal(),Flat=Forward.GetSafeNormal2D();
    const float Half=Capsule->GetScaledCapsuleHalfHeight();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(LeapStrikeTarget),false,Pawn);
    const float RayLength=FMath::Min(LeapStrike::MaxDrop+LeapReach,LeapReach/FMath::Max(.05f,float(Forward.Size2D())));
    FHitResult Aim;FVector AimPoint=Eye+Forward*RayLength;
    if(GetWorld()->LineTraceSingleByChannel(Aim,Eye,AimPoint,ECC_Visibility,Q))AimPoint=Aim.ImpactPoint;
    FVector Offset=(AimPoint-Start).GetClampedToMaxSize2D(LeapReach);Offset.Z=0;
    if(Offset.Size2D()<100.f)Offset=Flat*100.f;
    if(Offset.IsNearlyZero())return false;
    // Preview/authority share floor-based height limits and a terminal-aware
    // ballistic solution. A distant lower floor never creates a downward launch.
    for(int32 Candidate=0;Candidate<(AllowShorten?9:1);++Candidate)
    {
        const FVector XY=Start+Offset*(1.f-.1f*Candidate);
        FHitResult Ground;
        const float FloorZ=LeapStartFloorZ();
        if(!LeapGround(GetWorld(),Character.Get(),FVector(XY.X,XY.Y,FloorZ+LeapStrike::MaxRise+LeapStrike::TargetTolerance),
            FVector(XY.X,XY.Y,FloorZ-LeapStrike::MaxDrop-LeapStrike::TargetTolerance),Ground)||!Move->IsWalkable(Ground))continue;
        FVector End=Ground.ImpactPoint+FVector(0,0,LeapStrike::StandingHeight(Half,Capsule->GetScaledCapsuleRadius(),Ground.ImpactNormal));
        LeapStrike::FTrajectory Path;
        if(!IsLeapFloorHeightAllowed(float(Ground.ImpactPoint.Z))||FVector::DistSquared2D(Start,End)<FMath::Square(80.f)||
            !LeapStrike::SolveTrajectory(Start,End,Move->GetGravityZ(),Move->GetPhysicsVolume()->TerminalVelocity,Path))continue;
        if(CheckPath&&!IsLeapPathClear(End))continue;
        Target=End;Floor=Ground.ImpactPoint;Normal=Ground.ImpactNormal;return true;
    }
    return false;
}

bool UProductionToolComponent::BeginLeapStrike()
{
    const auto Status=LeapStrikeStatusText(false);if(!Status.IsEmpty())return false;
    auto* Pawn=Character.Get();FVector Target,Floor,Normal;
    const FVector Direction=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X);
    if(!SolveLeapTarget(Direction,Target,Floor,Normal)){LeapNoticeUntil=GetWorld()->GetTimeSeconds()+2.;return false;}
    return CommitLeapStrike(Target,Floor,Normal,Direction);
}
bool UProductionToolComponent::CommitLeapStrike(const FVector& Target,const FVector& Floor,const FVector& Normal,const FVector& Direction)
{
    auto* Pawn=Character.Get();if(!Pawn)return false;
    const auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;
    if(!Item||Item->InstanceId.IsEmpty())return false;
    LeapWeapon=Item->InstanceId;
    SetLeapAimPreview(false);LeapRequestDirection=Direction;
    if(++LeapSerial==0)++LeapSerial;
    if(!Pawn->HasAuthority()){bLeapPending=true;ServerBeginLeapStrike(LeapSerial,LeapWeapon,Direction,Target);return true;}
    return StartLeapStrike(Target,Floor,Normal,LeapClock(GetWorld()),Model->LeapStrikeStats());
}
void UProductionToolComponent::ServerBeginLeapStrike_Implementation(uint32 Serial,const FString& WeaponId,FVector_NetQuantizeNormal Direction,FVector_NetQuantize RequestedTarget)
{
    if(!Serial||int32(Serial-LeapReceivedSerial)<=0)return;LeapReceivedSerial=Serial;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    FVector Target=FVector::ZeroVector,Floor=FVector::ZeroVector,Normal=FVector::UpVector;Character=Pawn;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;
    bool Accepted=Item&&!WeaponId.IsEmpty()&&Item->InstanceId==WeaponId&&
        !Direction.ContainsNaN()&&!Direction.IsNearlyZero()&&LeapAvailable(Pawn,Model)&&!IsBusy()&&!HasAuthorityAttackInFlight()&&
        (!PS||!PS->IsQuickCombatExecuting(Pawn))&&
        !Pawn->bIsCrouched&&Pawn->GetCharacterMovement()->IsMovingOnGround()&&ValidateLeapLanding(RequestedTarget,Target,Floor,Normal);
    const auto Cast=Model?Model->LeapStrikeStats():FLeapStrikeCast();const double Now=LeapClock(GetWorld());
    if(Accepted){LeapSerial=Serial;LeapRequestDirection=Direction;Accepted=StartLeapStrike(Target,Floor,Normal,Now,Cast);}
    const auto State=Model?Model->Snapshot():FColdSteelProfile();
    ClientLeapStrikeResult(Serial,Accepted,Target,Floor,Normal,Now,Cast,State.UppercutStaminaSpent,
        State.LeapStrikeCooldown,State.LeapStrikeCooldownDuration,State.MartialCooldownRevision);
}
void UProductionToolComponent::ClientLeapStrikeResult_Implementation(uint32 Serial,bool Accepted,FVector_NetQuantize Target,
    FVector_NetQuantize Floor,FVector_NetQuantizeNormal Normal,double StartedAt,const FLeapStrikeCast& Cast,
    double TotalSpent,float Cooldown,float Duration,int64 Revision)
{
    if(auto* Model=ColdSteelAuthority::ForPawn(Character.Get()))
        Model->ApplyLeapStrikeReceipt(TotalSpent,Cooldown,Duration,Revision,StartedAt);
    if(Serial!=LeapSerial)return;const bool Requested=bLeapPending;bLeapPending=false;
    if(!Accepted){LeapNoticeUntil=GetWorld()->GetTimeSeconds()+2.;return;}
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Equipped=Model?Model->ActiveProductionTool():nullptr;
    if(!Requested||!Equipped||Equipped->InstanceId!=LeapWeapon||!LeapAvailable(Character.Get(),Model))
    {ServerCancelLeapStrike(Serial);return;}
    if(!StartLeapStrike(Target,Floor,Normal,StartedAt,Cast,true))ServerCancelLeapStrike(Serial);
}
void UProductionToolComponent::ServerCancelLeapStrike_Implementation(uint32 Serial)
{if(Serial==LeapSerial)FinishLeapStrike();}
void UProductionToolComponent::ClientStopLeapStrike_Implementation(uint32 Serial)
{if(Serial==LeapSerial)FinishLeapStrike(false);}

bool UProductionToolComponent::StartLeapStrike(const FVector& Target,const FVector& Floor,const FVector& Normal,double StartedAt,
    const FLeapStrikeCast& Cast,bool Paid)
{
    auto* Pawn=Character.Get();auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;if(!Pawn||!Item)return false;
    const FColdSteelItem CastWeapon=*Item;
    // Payment is authoritative and precedes the first charge pose. Preview is free.
    if(Pawn->HasAuthority()){if(!Model->CommitLeapStrikeCast(Cast))return false;}
    else if(!Paid)return false;
    LeapCast=Cast;bLeapTrainingPending=Pawn->HasAuthority();LeapRewardModel=Model;
    CancelInspect();ClearWarhammerRifts(false);bQueuedBluntAttack=false;NextBluntStage=0;SprintBlend=0.f;
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    LeapWeapon=CastWeapon.InstanceId;LeapTarget=Target;LeapFloor=Floor;LeapNormal=Normal;
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    // Keep the eye in the capsule's frame, shared with the world body. Neither
    // the requested endpoint nor an animated chest can drag it off the actor.
    LeapEyeLocal=Pawn->GetActorTransform().InverseTransformPosition(Aim.GetLocation());
    LeapCameraReleaseUntil=0.;LeapContactLocal=LeapCameraCollisionOffset=FVector::ZeroVector;
    const FVector Facing=LeapRequestDirection.GetSafeNormal2D(UE_SMALL_NUMBER,Pawn->GetActorForwardVector());
    LeapSlamRotation=FRotator(0,Facing.Rotation().Yaw,0).Quaternion();
    LeapLookCenter=LeapRequestDirection.Rotation();LeapLookCenter.Yaw=Facing.Rotation().Yaw;
    LeapImpactPoint=LeapImpactForFloor(Floor,Facing,LeapNormal);
    LeapStartedAt=StartedAt;LeapAge=FMath::Clamp(float(LeapClock(GetWorld())-StartedAt),0.f,LeapStrike::Charge);
    LeapNoticeUntil=0.;
    bLeapStrike=true;bLeapLaunched=bLeapLanded=bLeapWhoosh=false;LeapPoseClip=NAME_None;
    LeapFlightAge=0.f;LeapPoseRate=1.f;LeapStalledTime=0.f;LeapContactFrame=MAX_uint64;
    const auto Stats=ColdSteelMelee::Evaluate(CastWeapon,Model);
    LeapShot=ColdSteelSkills::Snapshot(Pawn,&CastWeapon);LeapShot.bMelee=true;LeapShot.WeakpointPercent=0.f;
    // Damage-derived poise uses this same coefficient once, preserving weapon bonuses.
    LeapShot.DamagePanel=Stats.DamageParts.Scaled(LeapCast.DamageMultiplier*Stats.Modifiers.MartialDamage);
    LeapShot.AttackForm=EMonsterAttackForm::Impact;LeapShot.AttackMeta=0;LeapShot.MasteryId=NAME_None;
    Pawn->StopMovementForMeleeSkill();
    return true;
}

bool UProductionToolComponent::LaunchLeapStrike()
{
    auto* Pawn=Character.Get();auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    if(!bLeapStrike||bLeapLaunched||!Move||!Move->IsMovingOnGround())return false;
    LeapStart=Pawn->GetActorLocation();
    LeapStrike::FTrajectory Path;
    if(!LeapStrike::SolveTrajectory(LeapStart,LeapTarget,Move->GetGravityZ(),Move->GetPhysicsVolume()->TerminalVelocity,Path))return false;
    LeapExpectedFlight=Path.Duration;LeapProgressPosition=LeapStart;
    ApplyLeapMotion(Move,LeapStart,LeapTarget,LeapSerial);
    bLeapLaunched=true;SetLeapAirborne(true);return true;
}

void UProductionToolComponent::TickLeapStrike(float Delta)
{
    auto* Pawn=Character.Get();auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;
    if(!LeapAvailable(Pawn,Model,true)||!Item||Item->InstanceId!=LeapWeapon)
    {FinishLeapStrike();return;}
    auto* Move=Pawn->GetCharacterMovement();
    Delta=FMath::Max(0.f,Delta);
    const float PreviousAge=LeapAge;
    if(!bLeapLaunched)
    {
        LeapAge=FMath::Min(LeapStrike::Charge,LeapAge+Delta);
        if(LeapStrike::Charge-LeapAge<1.e-5f)LeapAge=LeapStrike::Charge;
        if(LeapAge>=LeapStrike::Charge)
        {
            // Remote authority starts on the owner's launch saved move, not an
            // unrelated Actor tick. Otherwise the server can correct the owner
            // into Falling before its charge ends and make it cancel the cast.
            if(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())
            {
                if(LeapClock(GetWorld())-LeapStartedAt>LeapStrike::MaxAirTime)FinishLeapStrike();
                return;
            }
            if(!LaunchLeapStrike()){FinishLeapStrike();return;}
        }
        return;
    }
    if(!bLeapLanded)
    {
        LeapFlightAge+=Delta;
        if(!Move->IsFalling()&&!Move->IsMovingOnGround())
        {FinishLeapStrike();return;}
        const FVector Position=Pawn->GetActorLocation();
        if(FVector::DistSquared(Position,LeapProgressPosition)>FMath::Square(1.f))
        {LeapProgressPosition=Position;LeapStalledTime=0.f;}
        else LeapStalledTime+=Delta;
        FFindFloorResult Support;
        const auto* Capsule=Pawn->GetCapsuleComponent();
        const float DownSpeed=FMath::Max(0.f,float(-Move->Velocity.Z)),Gravity=FMath::Max(1.f,-Move->GetGravityZ());
        const float Probe=FMath::Clamp(DownSpeed*LeapStrike::Downstroke+.5f*Gravity*FMath::Square(LeapStrike::Downstroke)+50.f,100.f,800.f);
        if(Move->Velocity.Z<=0.f)Move->ComputeFloorDist(Position,Probe,Probe,Support,Capsule->GetScaledCapsuleRadius());
        const bool HasFloor=Support.IsWalkableFloor()&&!Support.HitResult.bStartPenetrating;
        const float FloorDistance=HasFloor?FMath::Max(0.f,Support.GetDistanceToFloor()-LeapStrike::FloorClearance):Probe;
        const float UntilContact=HasFloor?FMath::Clamp(LeapStrike::FallTime(FloorDistance,DownSpeed,Gravity,
            FMath::Max(1.f,Move->GetPhysicsVolume()->TerminalVelocity)),.001f,LeapStrike::Downstroke):LeapStrike::Downstroke;
        const float Raise=LeapStrike::Charge+(LeapStrike::Flight-LeapStrike::Downstroke)*
            FMath::Clamp(LeapFlightAge/FMath::Max(.1f,FMath::Min(LeapExpectedFlight,LeapStrike::Flight)-LeapStrike::Downstroke),0.f,1.f);
        const float ContactPose=HasFloor&&UntilContact<LeapStrike::Downstroke-1.e-4f?LeapStrike::Land-UntilContact:Raise;
        LeapAge=FMath::Max(LeapAge,FMath::Max(Raise,ContactPose));
        if(HasFloor)
        {
            LeapFloor=Support.HitResult.ImpactPoint;LeapNormal=Support.HitResult.ImpactNormal;
            LeapImpactPoint=LeapImpactForFloor(LeapFloor,LeapSlamRotation.GetForwardVector(),LeapNormal);
        }
        if(Move->IsMovingOnGround()&&HasFloor)
        {
            CompleteLeapLanding(Support.HitResult);
        }
        else if(LeapFlightAge>=LeapStrike::MaxAirTime||LeapStalledTime>=LeapStrike::StallTimeout)
        {
            // A genuinely stuck/no-ground cast releases the action. Native Falling
            // and its velocity continue; there is no endpoint snap or zero-velocity handoff.
            FinishLeapStrike(false);return;
        }
    }
    else if(LeapContactFrame!=GFrameCounter)LeapAge+=Delta;
    LeapPoseRate=Delta>UE_SMALL_NUMBER?FMath::Max(0.f,(LeapAge-PreviousAge)/Delta):0.f;
    if(!bLeapWhoosh&&LeapAge>LeapStrike::Land-LeapStrike::Downstroke+UE_SMALL_NUMBER)
    {
        bLeapWhoosh=true;
        if(Pawn->IsLocallyControlled())
        {
            if(bPojunGrip)PlayPojunSwing(.95f,.9f);
            else if(auto* Sound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject()))
                UGameplayStatics::PlaySound2D(this,Sound,.85f,1.f,WarhammerAudioPaths::HeavyStartSeconds);
        }
    }
    if(LeapAge>=LeapStrike::End)FinishLeapStrike(false);
}

void UProductionToolComponent::CompleteLeapLanding(const FHitResult& Ground)
{
    auto* Pawn=Character.Get();auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;
    if(!bLeapStrike||!bLeapLaunched||bLeapLanded||!Pawn)return;
    auto* Move=Pawn->GetCharacterMovement();
    if(!Move->IsMovingOnGround()||!Move->IsWalkable(Ground))return;
    if(!LeapAvailable(Pawn,Model,true)||!Item||Item->InstanceId!=LeapWeapon){FinishLeapStrike();return;}
    bLeapLanded=true;SetLeapAirborne(false);LeapAge=LeapStrike::Land;LeapContactFrame=GFrameCounter;
    LeapFloor=Ground.ImpactPoint;LeapNormal=Ground.ImpactNormal;
    LeapImpactPoint=LeapImpactForFloor(LeapFloor,LeapSlamRotation.GetForwardVector(),LeapNormal);
    LeapContactLocal=Pawn->GetActorTransform().InverseTransformPosition(LeapImpactPoint);
    Move->RemoveRootMotionSource(LeapStrike::MotionName);Move->StopMovementImmediately();
    if(Pawn->HasAuthority())
    {
        FActorSpawnParameters Params;Params.Owner=Pawn;Params.Instigator=Pawn;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if(auto* Wave=GetWorld()->SpawnActor<ALeapStrikeShockwave>(LeapImpactPoint+LeapNormal*2.f,FRotationMatrix::MakeFromZ(LeapNormal).Rotator(),Params))
        {
            Wave->Setup(LeapShot,LeapCast.RadiusCM,0.f);
            Wave->SetLeapTraining(LeapRewardModel.Get());bLeapTrainingPending=false;LeapRewardModel.Reset();Wave->PresentImpact();
        }
    }
}

void UProductionToolComponent::FinishLeapStrike(bool Interrupted)
{
    if(bLeapAirborne&&!IsLeapControlImmune())SetLeapAirborne(false);
    const bool Active=bLeapStrike||bLeapPending;
    bLeapStrike=bLeapPending=false;
    if(!Active)return;
    // Keep the collision constraint during the ordinary camera's return blend.
    LeapCameraReleaseUntil=GetWorld()->GetTimeSeconds()+.35;
    // Ordinary camera interpolation starts at the already collision-adjusted
    // component position. Carrying our correction as well would apply it twice
    // on the first recovery frame, pulling the view back another wall offset.
    LeapCameraCollisionOffset=FVector::ZeroVector;
    // No wave owns this cast (cancel, failed landing or spawn failure): release XP only.
    if(bLeapTrainingPending)
    {
        bLeapTrainingPending=false;auto* Reward=LeapRewardModel.Get();LeapRewardModel.Reset();
        if(Reward)Reward->TrainLeapStrike(0);
    }
    if(auto* Pawn=Character.Get())
    {
        auto* Move=Pawn->GetCharacterMovement();Move->RemoveRootMotionSource(LeapStrike::MotionName);
        if(bLeapLaunched&&Move->MovementMode==MOVE_Flying)Move->SetMovementMode(MOVE_Falling);
        // Predicted recovery can finish before authority reaches its own floor.
        // Natural completion must not cancel the server's pending impact.
        if(!Pawn->HasAuthority()&&Interrupted)ServerCancelLeapStrike(LeapSerial);
        else if(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())ClientStopLeapStrike(LeapSerial);
    }
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.16f,true);
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    bLeapLaunched=bLeapLanded=false;VisualTime=0.f;LeapPoseClip=NAME_None;
}

bool UProductionToolComponent::IsLeapControlImmune() const
{
    if(!bLeapAirborne)return false;
    const auto* Pawn=Character.Get();
    const auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    // Ground contact and death take effect immediately, even before the tool tick.
    return Move&&(Move->MovementMode==MOVE_Flying||Move->IsFalling())&&(!Health||!Health->IsDead());
}

void UProductionToolComponent::SetLeapAirborne(bool Active)
{
    if(bLeapAirborne==Active)return;
    bLeapAirborne=Active;
    if(auto* Owner=GetOwner())
    {
        auto* Display=UStatusEffectsComponent::GetOrCreate(Owner);
        if(Active)Display->SetPersistent(TEXT("leapControlImmune"),TEXT("腾空期间"));
        else Display->Remove(TEXT("leapControlImmune"));
        if(Owner->HasAuthority())Owner->ForceNetUpdate();
    }
}

void UProductionToolComponent::PresentLeapStrike()
{
    if(!Viewmodel)return;
    const FName Clip=TEXT("LeapStrike");
    if(LeapPoseClip!=Clip)
    {
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.10f,true,true);
        LeapPoseClip=Clip;LeapPoseChangedAt=LeapAge;
    }
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(LeapAge-LeapPoseChangedAt);
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    const float Ground=LeapStrike::GroundWeight(LeapAge);
    if(Ground>0.f&&Camera)
    {
        const auto* Move=Character->GetCharacterMovement();
        const bool Contact=bLeapLanded&&Move->IsMovingOnGround()&&Move->CurrentFloor.IsWalkableFloor();
        const FVector Normal=Contact?Move->CurrentFloor.HitResult.ImpactNormal:FVector::UpVector;
        const FQuat Planted=FQuat::FindBetweenNormals(FVector::UpVector,Normal)*
            FRotator(LeapStrike::ViewPitch,LeapSlamRotation.Rotator().Yaw,0).Quaternion();
        FVector Eye=Camera->GetComponentLocation();
        if(Contact)
        {
            // A real, nearby contact may refine the hammer's floor placement.
            // Carry it with the actor/base; never pin the arms to an old world
            // point after a correction, platform move or interrupted landing.
            const FVector Impact=Character->GetActorTransform().TransformPosition(LeapContactLocal);
            const FVector Anchor=Impact-Planted.RotateVector(LeapStrike::ContactHead);
            const float ContactBlend=LeapStrike::Ease((LeapAge-LeapStrike::Land)/.06f);
            Eye+=(Anchor-Eye).GetClampedToMaxSize(20.f)*Ground*ContactBlend;
            ConstrainLeapStrikeView(Eye);
        }
        Viewmodel->SetWorldLocationAndRotation(Eye,
            FQuat::Slerp(Camera->GetComponentQuat(),Planted,Ground)*FRotator(0,90,0).Quaternion());
    }
    // The continuous clip already contains the complete supported arm chain.
    // Move its camera/weapon frame together; floor IK must not pull shoulders forward.
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    SampleMotion(Clip,LeapAge);
}

bool UProductionToolComponent::GetLeapStrikeCameraLocation(FVector& Point) const
{
    const auto* Pawn=Character.Get();if(!bLeapStrike||!Pawn)return false;
    FVector NeutralEye=LeapEyeLocal;
    // Let any stair-camera offset present at activation settle during charge;
    // do not carry that old floor correction through a multi-second fall.
    NeutralEye.Z=FMath::Lerp(NeutralEye.Z,double(Pawn->StandingCameraHeight),LeapStrike::Ease(LeapAge/LeapStrike::Charge));
    const FVector Eye=Pawn->GetActorTransform().TransformPosition(NeutralEye);
    const FQuat Planted=FRotator(LeapStrike::ViewPitch,LeapSlamRotation.Rotator().Yaw,0).Quaternion();
    // Use the authored posture over the CURRENT capsule foot plane. At terminal
    // speed a predicted floor can be metres below the actor during downstroke;
    // it must never become the camera's positional anchor, even for one frame.
    const FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Anchor=Feet+LeapSlamRotation.GetForwardVector()*WarhammerHeavy::LandingForward-
        Planted.RotateVector(LeapStrike::ContactHead);
    FVector Bend=Anchor-Eye;
    const FVector Horizontal=FVector(Bend.X,Bend.Y,0).GetClampedToMaxSize(35.f);
    Bend=FVector(Horizontal.X,Horizontal.Y,FMath::Clamp(Bend.Z,-65.,10.));
    Point=Eye+Bend*LeapStrike::GroundWeight(LeapAge);
    return true;
}

void UProductionToolComponent::UpdateLeapStrikeCamera(FVector& WorldPoint,float Delta)
{
    const FVector Desired=WorldPoint;
    if(!ConstrainLeapStrikeView(WorldPoint)){LeapCameraCollisionOffset=FVector::ZeroVector;return;}
    const FQuat Frame=Character->GetActorQuat();
    const FVector Required=Frame.UnrotateVector(WorldPoint-Desired);
    // Carry only the obstruction correction in actor space. Release it gradually
    // when a wall disappears; actual falling velocity and authored posture never
    // lag behind the capsule. The final sweep still retracts immediately on contact.
    const FVector Offset=FMath::VInterpConstantTo(LeapCameraCollisionOffset,Required,FMath::Max(0.f,Delta),180.f);
    WorldPoint=Desired+Frame.RotateVector(Offset);
    ConstrainLeapStrikeView(WorldPoint);
    LeapCameraCollisionOffset=Frame.UnrotateVector(WorldPoint-Desired);
}

bool UProductionToolComponent::ConstrainLeapStrikeView(FVector& WorldPoint) const
{
    const auto* Pawn=Character.Get();const auto* World=GetWorld();
    if(!Pawn||!World||(!bLeapStrike&&World->GetTimeSeconds()>=LeapCameraReleaseUntil))return false;
    if(Pawn->IsTraversing()||UFPSFurnitureRestComponent::IsResting(Pawn))return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    const auto* Capsule=Pawn->GetCapsuleComponent();
    const FVector Center=Capsule->GetComponentLocation();
    constexpr float EyeRadius=6.f;
    const float Half=Capsule->GetScaledCapsuleHalfHeight();
    FVector Offset=WorldPoint-Center;
    if(Offset.ContainsNaN())Offset=FVector(0,0,Pawn->StandingCameraHeight);
    const FVector Horizontal=FVector(Offset.X,Offset.Y,0).GetClampedToMaxSize(80.f);
    Offset=FVector(Horizontal.X,Horizontal.Y,FMath::Clamp(Offset.Z,-double(Half)+EyeRadius,double(Half)-EyeRadius));
    WorldPoint=Center+Offset;
    // Sweep the FINAL eye (including recoil, interpolation and landing spring)
    // from inside the live capsule, not from the already offset/penetrating eye.
    // The axial start is below the rounded cap so the query sphere fits inside.
    const double SafeHalf=FMath::Max(0.,double(Half)-Capsule->GetScaledCapsuleRadius());
    const FVector Start=Center+FVector(0,0,FMath::Clamp(Offset.Z,-SafeHalf,SafeHalf));
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(LeapStrikeCamera),false,Pawn);
    const auto Shape=FCollisionShape::MakeSphere(EyeRadius);
    if(World->SweepSingleByChannel(Hit,Start,WorldPoint,FQuat::Identity,ECC_Camera,Shape,Q))
    {
        if(!Hit.bStartPenetrating)WorldPoint=FMath::Lerp(Start,WorldPoint,FMath::Max(0.f,Hit.Time-.01f));
        else
        {
            // Camera-only blockers can intersect the capsule without stopping
            // CharacterMovement. Resolve the small sphere's penetration instead
            // of returning the same embedded start (or an invalid hit location).
            FVector Safe=Start;
            for(int32 Attempt=0;Attempt<3&&Hit.bStartPenetrating;++Attempt)
            {
                Safe+=Hit.Normal*FMath::Min(Hit.PenetrationDepth+1.f,Capsule->GetScaledCapsuleRadius());
                if(!World->SweepSingleByChannel(Hit,Safe,Safe+FVector(0,0,.01f),FQuat::Identity,ECC_Camera,Shape,Q))break;
            }
            WorldPoint=Safe;
        }
    }
    return true;
}

void UProductionToolComponent::LeapStrikeCamera(FVector& Location,FRotator& Rotation) const
{
    const float T=LeapAge;
    struct FKey {float T;FVector P;FRotator R;};
    const FKey Keys[]={
        {0,{0,0,0},{0,0,0}},
        {.40f,{-4,1,-5},{-4,-1.5f,-2.5f}},
        {.50f,{-2,0,-3},{-2,0,-1}},
        {.64f,{-7,-1,3},{7,1.5f,3}},
        {.92f,{-4,0,2},{4,1,1.5f}},
        {LeapStrike::Land-LeapStrike::Downstroke,{-3,0,1},{3,0,1}},
        {LeapStrike::Land,{3,0,-7},{-8,0,-3}},
        {LeapStrike::Land+.09f,{-2,0,1},{2,0,1}},
        {LeapStrike::Land+.24f,{0,0,-1},{-.8f,0,-.3f}},
        {LeapStrike::End,{0,0,0},{0,0,0}}};
    for(int32 I=1;I<UE_ARRAY_COUNT(Keys);++I)if(T<=Keys[I].T)
    {
        const auto& A=Keys[I-1];const auto& B=Keys[I];const float U=LeapStrike::Ease((T-A.T)/(B.T-A.T));
        Location=FMath::Lerp(A.P,B.P,U);Rotation=FMath::Lerp(A.R,B.R,U);break;
    }
    if(T>=LeapStrike::Land)
    {
        const float Age=T-LeapStrike::Land,Envelope=FMath::Exp(-18.f*Age);
        Location.Z-=2.f*Envelope*FMath::Sin(80.f*Age);
        Rotation.Pitch+=3.5f*Envelope*FMath::Sin(70.f*Age);
        Rotation.Roll+=1.5f*Envelope*FMath::Sin(95.f*Age);
    }
    // Author at the project's default 0.45 camera-motion setting, retaining the user slider.
    Location*=1.f/.45f;Rotation*=1.f/.45f;
}
