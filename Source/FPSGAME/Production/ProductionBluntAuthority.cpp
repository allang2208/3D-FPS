#include "ProductionToolComponent.h"
#include "../Weapons/PojunGrip.h"
#include "ProductionBluntCombo.h"
#include "WarhammerHeavyMotion.h"
#include "WarhammerCombat.h"
#include "RuneboundHammerTuning.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerCallIntent.h"
#include "ThunderHammerZhenTing.h"
#include "ThunderHammerStaticField.h"
#include "ThunderHammerCoil.h"
#include "WarhammerShockwave.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../FPSGAMEPlayerController.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelProfileRecovery.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/MeteorGround.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
bool CanCommitBlunt(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Profile,bool bContinuing=false)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    const auto* Tool=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
    return Pawn&&Pawn->HasAuthority()&&Item&&PojunGrip::UsesHammerMotion(*Item)&&PC&&
        !Pawn->IsTraversing()&&!Pawn->IsCastBlockingLeftHandAction()&&(!Health||!Health->IsDead())&&
        (!Sword||(!Sword->IsGuarding()&&!Sword->IsPojunChainOccupied()))&&(!Tool||!Tool->IsThunderHammerAway())&&(!PS||!PS->IsQuickCombatExecuting(Pawn))&&
        !(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC))&&(!Building||!Building->IsBuilding());
}
}

bool UProductionToolComponent::IsHeavyCharging() const
{
    const auto* Pawn=Character.Get();
    return Pawn&&(Pawn->IsLocallyControlled()?bBluntCharging:(Pawn->HasAuthority()&&bBluntServerCharging));
}

void UProductionToolComponent::TickAuthorityBluntCharge()
{
    auto* Pawn=Character.Get();
    if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled()||(!bBluntServerCharging&&!bBluntServerSprintAttack))return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!CanCommitBlunt(Pawn,Profile)||Pawn->IsDodging()||!Item||
        Item->InstanceId!=(bBluntServerCharging?BluntServerChargeInstance:BluntServerInstance)||
        (bBluntServerCharging&&Profile->Stamina()<=0.f))
    {
        ServerCancelBluntAttack_Implementation(BluntServerAttackId);
        ClientBluntAttackResult(BluntServerAttackId,0,false,false,false);
    }
}

void UProductionToolComponent::ServerBeginBluntCharge_Implementation(uint32 AttackId,const FString& WeaponId)
{
    if(int32(AttackId-BluntServerAttackId)<=0||int32(AttackId-BluntLastServerRequestId)<=0)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||WeaponId.IsEmpty()||Item->InstanceId!=WeaponId||!GetWorld()||IsLeapStrikeActive()||bBluntUppercut||bBluntWhirlwind||!CanCommitBlunt(Pawn,Profile)||Profile->Stamina()<=0.f||GetWorld()->GetTimeSeconds()<BluntServerReadyAt)
    {ClientBluntAttackResult(AttackId,0,false,false,false);return;}
    Character=Pawn;BluntServerAttackId=AttackId;bBluntServerCharging=true;bThunderCallHoldConfirmed=false;
    ApplyToolStats(Profile->ActiveProductionTool(),Profile);
    if(bThunderCallSeat)
    {
        bThunderCallCharging=false; // The server tracks the press while the tap/hold decision is pending.
    }
    BluntServerChargeStartedAt=GetWorld()->GetTimeSeconds();
    BluntServerChargeInstance=Profile->ActiveProductionTool()->InstanceId;
}

void UProductionToolComponent::ServerConfirmThunderCall_Implementation(uint32 AttackId)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!bBluntServerCharging||AttackId!=BluntServerAttackId)return;
    if(!CanCommitBlunt(Pawn,Profile,true)||!Item||Item->InstanceId!=BluntServerChargeInstance||
        !ThunderHammerCall::Installed(*Item)||Profile->Stamina()<=0.f||(!Profile->HasInfiniteMana()&&Profile->Mana()<=0.f))
    {
        ServerCancelBluntAttack_Implementation(AttackId);
        ClientBluntAttackResult(AttackId,0,false,false,false);return;
    }
    if(!bThunderCallHoldConfirmed)
    {
        // Credit the pending click window and bounded packet/frame jitter.
        // A client cannot idle an unconfirmed press, then confirm and instantly
        // release a full charge without paying the active hold duration.
        constexpr double ConfirmationGrace=.12;
        BluntServerChargeStartedAt=FMath::Max(BluntServerChargeStartedAt,
            GetWorld()->GetTimeSeconds()-ThunderHammerCallIntent::PendingSeconds(BluntChargeSeconds)-ConfirmationGrace);
    }
    bThunderCallHoldConfirmed=true;
}

void UProductionToolComponent::ServerBeginBluntAttack_Implementation(uint32 AttackId,bool bReleaseCharge,bool bSprintAttack,const FString& WeaponId)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* World=GetWorld();
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto Reject=[&]()
    {
        BluntServerNextStage=0;BluntServerComboExpires=0.;bBluntServerCharging=false;
        ClientBluntAttackResult(AttackId,0,false,false,false);
    };
    const bool NewRequest=int32(AttackId-BluntLastServerRequestId)>0;
    if(!NewRequest)return; // A repeated receipt cannot spend again or cancel a newer action.
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||WeaponId.IsEmpty()||Item->InstanceId!=WeaponId)
    {ClientBluntAttackResult(AttackId,0,false,false,false);return;}
    BluntLastServerRequestId=AttackId;
    // A buffered cut leaves the owner on the frame its previous cut ends, so
    // network jitter (or float/double clock drift on a listen host) can land
    // it a few ms before this clock. Accept such an ordinary cut but start its
    // server clock at the ready time: contact, cadence and DPS stay exactly
    // server-timed. Charge releases and sprint attacks keep the strict check.
    constexpr double BufferedCutTolerance=.12;
    const double Now=World?World->GetTimeSeconds():0.;
    const double Early=bReleaseCharge||bSprintAttack?0.:FMath::Clamp(BluntServerReadyAt-Now,0.,BufferedCutTolerance);
    if(!World||IsLeapStrikeActive()||bBluntUppercut||bBluntWhirlwind||!CanCommitBlunt(Pawn,Profile,bBluntServerCharging)||Now+Early<BluntServerReadyAt){Reject();return;}
    const FString SourceInstance=Item->InstanceId;
    if(bSprintAttack&&(bReleaseCharge||!PojunGrip::CanSprintAttack(*Item,Profile)||BluntSprintInstance!=SourceInstance||World->GetTimeSeconds()-BluntSprintReadyAt>.35))
    {Reject();return;}
    if(bReleaseCharge&&(!bBluntServerCharging||BluntServerAttackId!=AttackId||BluntServerChargeInstance!=SourceInstance||Profile->Stamina()<=0.f)){Reject();return;}
    const float Held=bReleaseCharge?float(World->GetTimeSeconds()-BluntServerChargeStartedAt):0.f;
    Character=Pawn;ApplyToolStats(Item,Profile);
    if(bThunderCallSeat&&bReleaseCharge&&bThunderCallHoldConfirmed)
    {ServerCancelBluntAttack_Implementation(AttackId);Reject();return;}
    // JiLei's charged release has its own RPC; a tap must remain a normal cut
    // even if the server receives its release after a long network delay.
    const bool Heavy=bSprintAttack||(!bThunderCallSeat&&bReleaseCharge&&Held>=BluntChargeSeconds);
    const bool Toll=Heavy&&!bSprintAttack&&bFinalTollHead;
    const bool Throw=Heavy&&!bSprintAttack&&bThunderThrowSeat;
    const float Resume=Heavy||bSprintAttack?0.f:BluntChargeResume(Held);
    bBluntServerCharging=false;
    if(bThunderCallSeat){bThunderCallCharging=false;FinishThunderCallResources();}
    const FProductionToolStats Stats=ToolStats;
    const bool Zhufeng=bSprintAttack&&PojunGrip::Attack(*Item,false,true,2)==PojunGrip::EAttack::Zhufeng;
    const double AttackCost=Zhufeng?Profile->DashAttackStats().StaminaCost:Heavy&&!bSprintAttack?Stats.HeavyReleaseStaminaCost:Stats.StaminaCost;
    if(!Profile->SpendStamina(float(AttackCost))){Reject();return;}
    ClientBluntStaminaSpent(AttackId,float(AttackCost));
    Item=Profile->ActiveProductionTool();
    if(!Item||Item->InstanceId!=SourceInstance){Reject();return;}
    if(BluntServerInstance!=SourceInstance||World->GetTimeSeconds()>BluntServerComboExpires||(!bThunderCallSeat&&Held>.20f))BluntServerNextStage=0;
    const int32 Stage=bSprintAttack?2:BluntServerNextStage;
    BluntServerNextStage=Heavy||bSprintAttack?0:(Stage+1)%3;
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    BluntServerInstance=SourceInstance;BluntServerAttackId=AttackId;
    bBluntServerSprintAttack=bSprintAttack;
    if(bSprintAttack)BluntSprintLungeDistance=Profile->DashAttackStats().DistanceCM;
    AxeStrike=ColdSteelSkills::Snapshot(Pawn,Item);AxeStrike.bMelee=true;
    AxeStrike.DamagePanel=WarhammerCombat::Damage(Stats.Damage,Profile,bSprintAttack,Heavy,BluntHeavyMultiplier,Stage,Stats.PofengFinisherMultiplier);
    // Snapshot only a fully charged release. Add this magic at ground contact,
    // after the physical heavy multiplier; sprint attacks never call down thunder.
    const float ThunderMagic=Heavy&&!bSprintAttack&&Item->Definition==ThunderHammer::Definition?
        ThunderHammer::LightningMagic(*Item,Profile):-1.f;
    AxeStrike.ToughnessDamageMultiplier=float(Stats.ToughnessDamage);
    if(Heavy&&!bSprintAttack)
    {
        ThunderHammerZhenTing::Commit(AxeStrike,Item,Pawn->GetViewRotation().Vector());
        ThunderHammerStaticField::Commit(AxeStrike,Item);
        ThunderHammerCoil::Commit(AxeStrike,Item,Profile);
    }
    const auto Special=PojunGrip::Attack(*Item,Heavy,bSprintAttack,Stage);
    if(Special!=PojunGrip::EAttack::Ordinary)
    {
        AxeStrike.CriticalChance=FMath::Clamp(AxeStrike.CriticalChance+float(Stats.CriticalChanceAdd),0.f,100.f);
        BluntAttackId=AttackId;
        StartPojunAttack(Special,Profile);
        BluntServerComboExpires=BluntServerReadyAt+ProductionBluntCombo::ResetSeconds;
        ClientBluntAttackResult(AttackId,Stage,true,false,Heavy,bSprintAttack);
        return;
    }
    const float ActionRate=Toll?HasteActionRate:bSprintAttack?HasteActionRate:Heavy?RateScale*BluntMasteryInterval:RateScale;
    if(Toll)FinalTollActionRate=ActionRate;
    const float Lift=bSprintAttack?WarhammerSprint::LiftSeconds/HasteActionRate:0.f;
    BluntServerSprintStartedAt=Now;
    const float Contact=float(Early)+(Throw?ThunderHammerThrow::Release/ActionRate:Toll?FinalTollHeavy::FirstContact/ActionRate:Heavy?Lift+WarhammerHeavy::Contact/ActionRate:float(Stats.ContactSeconds)-Resume);
    BluntServerSprintMoveUntil=bSprintAttack?Now+FMath::Min(Lift+.15f,Contact):0.;
    BluntServerReadyAt=Now+Early+(Throw?ThunderHammerThrow::Duration/ActionRate:Toll?FinalTollHeavy::Duration/ActionRate:Heavy?Lift+WarhammerHeavy::RealDuration(ActionRate):Stats.SwingSeconds-Resume);
    FinalTollHeavySerial=Toll?AxeStrike.MasteryAttackSerial:0;FinalTollCommitUntil=RuneboundClock()+FinalTollHeavy::Duration/ActionRate+.1;
    BluntServerGroundSlamUntil=Heavy&&!Toll&&!Throw?BluntServerReadyAt:0.;
    BluntServerSprintContactAt=bSprintAttack?Now+Contact:0.;
    if(Throw)Pawn->StopMovementForMeleeSkill();
    if(Heavy&&!Toll&&!Throw)
    {
        BluntSlamRotation=FRotator(0.f,Pawn->GetControlRotation().Yaw,0.f).Quaternion();
        BluntSlamEye=Pawn->GetMeleeAimTransform().GetLocation();
        BluntSprintAnchorLocation=Pawn->GetActorLocation();
        BluntSprintDirection=BluntSlamRotation.GetForwardVector().GetSafeNormal2D();
        bBluntFloorTarget=false;
        FHitResult Floor;bBluntFloorTarget=FindBluntGround(Floor);
        if(bBluntFloorTarget){BluntFloorPoint=Floor.ImpactPoint;BluntFloorNormal=Floor.ImpactNormal;}
        auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
        const bool PendingJump=Move&&!Move->PendingLaunchVelocity.IsZero();
        const bool CarryMomentum=bSprintAttack&&Move&&(Move->IsFalling()||PendingJump);
        const FVector Carry=Move?(PendingJump?Move->PendingLaunchVelocity:Move->Velocity):FVector::ZeroVector;
        // A remote slide-jump move can arrive after this reliable attack RPC.
        // Its CMC packet must finish the jump before we stop/retain locomotion.
        if(!bSprintAttack||Pawn->IsLocallyControlled())
        {
            if(bSprintAttack&&Pawn->IsSliding())Pawn->StopSlide(true);
            Pawn->StopMovementForMeleeSkill();
            if(CarryMomentum)Move->BeginMeleeDashMomentum(Carry);
        }
    }
    BluntServerComboExpires=BluntServerReadyAt+ProductionBluntCombo::ResetSeconds;
    ClientBluntAttackResult(AttackId,Stage,true,false,Heavy,bSprintAttack);
    const float StunSeconds=ThunderMagic>=0.f?ThunderHammer::StunSeconds:Heavy&&!bSprintAttack?BluntHeavyStunSeconds:0.f;
    const FString CommittedData=Item->Data;
    const auto Committed=AxeStrike;
    const bool Pofeng=!Heavy&&Stage==2&&Stats.PofengFinisherMultiplier.IsSet();
    World->GetTimerManager().SetTimer(BluntContactTimer,FTimerDelegate::CreateWeakLambda(this,[this,SourceInstance,AttackId,Stage,Pofeng,Heavy,bSprintAttack,StunSeconds,Toll,Throw,CommittedData,Committed,ThunderMagic]()
    {
        auto* OwnerPawn=Character.Get();auto* OwnerProfile=ColdSteelAuthority::ForPawn(OwnerPawn);
        const auto* Current=OwnerProfile?OwnerProfile->ActiveProductionTool():nullptr;
        if(BluntServerAttackId!=AttackId)return;
        if(!CanCommitBlunt(OwnerPawn,OwnerProfile,true)||!Current||Current->InstanceId!=SourceInstance)
        {BluntServerNextStage=0;BluntServerGroundSlamUntil=0.;bBluntServerSprintAttack=false;BluntServerSprintContactAt=0.;ClientBluntAttackResult(AttackId,Stage,false,false,Heavy,bSprintAttack);return;}
        if(Toll&&(BluntServerAttackId!=AttackId||Current->Data!=CommittedData||!RuneboundHammer::HasFinalToll(*Current)))return;
        if(Throw&&(Current->Data!=CommittedData||!ThunderHammerThrow::Installed(*Current,OwnerProfile)))return;
        if(Toll||ThunderMagic>=0.f)AxeStrike=Committed;
        ColdSteelAuthority::FScope Scope(OwnerProfile);
        if(bSprintAttack){UpdateBluntSprintAnchor(true);BluntServerSprintContactAt=0.;}
        const bool Confirmed=Throw?LaunchThunderHammer(Committed,ThunderMagic):Toll?ResolveBluntContact():
            Heavy?BeginBluntShockwave(bSprintAttack,StunSeconds,ThunderMagic):ResolveBluntContact(0.f,Pofeng);
        if(Confirmed)
        {
            if(!Heavy)BluntServerReadyAt=FMath::Max(BluntServerReadyAt,double(GetWorld()->GetTimeSeconds()+ProductionBluntCombo::HitRecoverSeconds/RateScale));
            BluntServerComboExpires=BluntServerReadyAt+ProductionBluntCombo::ResetSeconds;
            ClientBluntAttackResult(AttackId,Stage,true,true,Heavy,bSprintAttack);
        }
    }),FMath::Max(.001f,Contact),false);
    if(Toll)
    {
        World->GetTimerManager().SetTimer(FinalTollContactTimer,FTimerDelegate::CreateWeakLambda(this,[this,SourceInstance,AttackId,Stage,Committed,CommittedData]()
        {
            auto* OwnerPawn=Character.Get();auto* OwnerProfile=ColdSteelAuthority::ForPawn(OwnerPawn);
            const auto* Current=OwnerProfile?OwnerProfile->ActiveProductionTool():nullptr;
            if(BluntServerAttackId!=AttackId||!CanCommitBlunt(OwnerPawn,OwnerProfile,true)||!Current||Current->InstanceId!=SourceInstance||Current->Data!=CommittedData||!RuneboundHammer::HasFinalToll(*Current))return;
            ColdSteelAuthority::FScope Scope(OwnerProfile);
            AxeStrike=Committed;AxeStrike.MasteryAttackSerial=ColdSteelSkills::Snapshot(OwnerPawn,Current).MasteryAttackSerial;
            FinalTollHeavySerial=AxeStrike.MasteryAttackSerial;
            const bool Confirmed=ResolveBluntContact();
            if(Confirmed)ClientBluntAttackResult(AttackId,Stage,true,true,true,false);
        }),FinalTollHeavy::SecondContact/ActionRate,false);
    }
    // A pulse may overload a target and transact rewards/inventory. Complete
    // all borrowed item reads and attack setup before invoking those callbacks.
    if(Heavy&&!bSprintAttack)
    {
        ThunderHammerStaticField::Released(Pawn,Committed,Throw||bThunderCallSeat);
        ThunderHammerCoil::Released(Pawn,Committed,Throw||bThunderCallSeat);
    }
}

void UProductionToolComponent::ServerCancelBluntAttack_Implementation(uint32 AttackId)
{
    if(AttackId!=BluntServerAttackId)return;
    bThunderCallHoldConfirmed=false;
    bThunderCallCharging=false;FinishThunderCallResources();
    if(auto* Pawn=Character.Get())
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))Move->CancelHammerSprintMove(AttackId);
    FinishBluntWhirlwind();
    FinishBluntUppercut();
    if(GetWorld()){GetWorld()->GetTimerManager().ClearTimer(BluntContactTimer);GetWorld()->GetTimerManager().ClearTimer(FinalTollContactTimer);}
    FinalTollHeavySerial=0;
    BluntServerNextStage=0;BluntServerComboExpires=0.;bBluntServerCharging=false;
    BluntServerGroundSlamUntil=0.;BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    BluntServerReadyAt=0.;
    bBluntServerSprintAttack=false;BluntServerSprintContactAt=0.;bBluntSprintLungeBlocked=true;
}

void UProductionToolComponent::ServerReleaseThunderCall_Implementation(uint32 AttackId,FVector_NetQuantize Point)
{
    if(int32(AttackId-BluntServerAttackId)<0||int32(AttackId-BluntLastServerRequestId)<=0)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto Reject=[&]()
    {
        bBluntServerCharging=bThunderCallCharging=false;FinishThunderCallResources();
        ClientThunderCallResult(AttackId,false);
    };
    if(!Pawn||!GetWorld()||!Item||!ThunderHammerCall::Installed(*Item)||!CanCommitBlunt(Pawn,Profile,bBluntServerCharging)||
        int32(AttackId-BluntLastServerRequestId)<=0||GetWorld()->GetTimeSeconds()<BluntServerReadyAt)
    {Reject();return;}
    const bool Local=Pawn->IsLocallyControlled();
    if(!(Local?bBluntCharging:bBluntServerCharging)||(!Local&&(!bThunderCallHoldConfirmed||BluntServerAttackId!=AttackId||BluntServerChargeInstance!=Item->InstanceId)))
    {Reject();return;}
    Character=Pawn;ApplyToolStats(Item,Profile);
    const float Held=float(GetWorld()->GetTimeSeconds()-(Local?BluntChargeStartedAt:BluntServerChargeStartedAt));
    FVector GroundPoint=Point,GroundNormal=FVector::UpVector;FString GroundFailure;
    if(FParse::Param(FCommandLine::Get(),TEXT("ThunderHammerClosureAudit")))
        UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_RELEASE id=%u held=%.6f full=%.6f stamina=%.2f mana=%.2f point=%s"),AttackId,Held,BluntChargeSeconds,Profile->Stamina(),Profile->Mana(),*GroundPoint.ToString());
    const float Remaining=BluntChargeSeconds-Held;
    if(!Local&&Remaining>0.f&&Remaining<=.25f)
    {
        // Press and release packets can have different transit times. A full
        // local release may therefore arrive just before the server deadline.
        // Wait for that deadline, retaining resource charging and all identity,
        // death, cancellation and ground checks; never grant an early strike.
        GetWorld()->GetTimerManager().SetTimer(BluntContactTimer,FTimerDelegate::CreateWeakLambda(this,[this,AttackId,Point]()
        {ServerReleaseThunderCall_Implementation(AttackId,Point);}),Remaining+.005f,false);
        return;
    }
    if(Held<BluntChargeSeconds||Profile->Stamina()<=0.f||(!Profile->HasInfiniteMana()&&Profile->Mana()<=0.f)||
        !MeteorGround::Validate(Pawn,ThunderHammerCall::RangeCM,GroundPoint,GroundNormal,true,GroundFailure))
    {if(FParse::Param(FCommandLine::Get(),TEXT("ThunderHammerClosureAudit")))UE_LOG(LogTemp,Display,TEXT("THUNDER_CLOSURE_RELEASE_REJECT ground=%s"),*GroundFailure);Reject();return;}
    BluntLastServerRequestId=BluntServerAttackId=AttackId;
    bBluntServerCharging=bThunderCallCharging=false;
    BluntServerReadyAt=GetWorld()->GetTimeSeconds()+ThunderHammerCall::ReleaseSeconds/HasteActionRate;
    BluntServerNextStage=0;BluntServerComboExpires=0.;
    auto Shot=ColdSteelSkills::Snapshot(Pawn,Item);Shot.bMelee=true;Shot.AttackMeta=0x10;
    // JiLei takes the complete ordinary heavy attack. The wave adds the native
    // thunder once, then converts the whole receipt to magic before contact.
    Shot.DamagePanel=WarhammerCombat::Damage(ToolStats.Damage,Profile,false,true,BluntHeavyMultiplier,0);
    Shot.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage);
    ThunderHammerZhenTing::Commit(Shot,Item,Pawn->GetViewRotation().Vector());
    ThunderHammerStaticField::Commit(Shot,Item);
    ThunderHammerCoil::Commit(Shot,Item,Profile);
    const float Magic=ThunderHammer::LightningMagic(*Item,Profile);
    FActorSpawnParameters Params;Params.Owner=Pawn;Params.Instigator=Pawn;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Wave=GetWorld()->SpawnActor<AWarhammerShockwave>(GroundPoint+GroundNormal*2.f,FRotationMatrix::MakeFromZ(GroundNormal).Rotator(),Params))
    {Wave->Setup(Shot,ThunderHammerCall::RadiusCM,ThunderHammer::StunSeconds,Magic,true);ClientThunderCallResult(AttackId,true);}
    else ClientThunderCallResult(AttackId,false);
    FinishThunderCallResources();Pawn->ForceNetUpdate();
}

void UProductionToolComponent::ClientBluntAttackResult_Implementation(uint32 AttackId,int32 Stage,bool bAccepted,bool bConfirmed,bool bHeavy,bool bSprint)
{
    if(!bAccepted&&AttackId==BluntAttackId&&!ThrownHammer)ThunderAwayInstance.Reset();
    // Cancellation still retires the matching movement after the local pose has finished.
    if(!bAccepted)if(auto* Pawn=Character.Get())
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))Move->CancelHammerSprintMove(AttackId);
    if(Kind!=TEXT("warhammer")||AttackId!=BluntAttackId)return;
    if(PojunAttack!=PojunGrip::EAttack::Ordinary||Elapsed>=0.f)
    {
        auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
        const auto Special=bAccepted&&Item?PojunGrip::Attack(*Item,bHeavy,bSprint,Stage):PojunGrip::EAttack::Ordinary;
        if(Special!=PojunGrip::EAttack::Ordinary&&PojunAttack==Special)return;
        if(PojunAttack!=PojunGrip::EAttack::Ordinary)
        {
            FinishBluntUppercut();FinishBluntWhirlwind();
            if(!bAccepted){NextBluntStage=0;return;}
            Elapsed=0.f;bContacted=bHitConfirmed=bSwingSoundPlayed=false;
        }
        if(Special!=PojunGrip::EAttack::Ordinary)
        {
            BluntStage=Stage;StartPojunAttack(Special,Profile);return;
        }
    }
    if(!bBluntCharging&&Elapsed<0.f)return;
    if(!bAccepted){if(bBluntCharging)CancelHeavyCharge();else CancelUse();return;}
    if(bBluntHeavy!=bHeavy)Elapsed=0.f;
    // The server owns the combo stage; a chained cut predicted another stage.
    if(Stage!=BluntStage&&BluntStartClip>0.f){BluntStartClip=0.f;HandOffBluntPose();}
    bBluntHeavy=bHeavy;bBluntSprintAttack=bSprint;BluntStage=Stage;
    if(bHeavy&&!UsesFinalTollHeavy()&&!UsesThunderThrowHeavy()&&!bBluntFloorTarget)
    {
        FHitResult Floor;bBluntFloorTarget=FindBluntGround(Floor);
        if(bBluntFloorTarget){BluntFloorPoint=Floor.ImpactPoint;BluntFloorNormal=Floor.ImpactNormal;}
        BluntSlamRotation=FRotator(0.f,Character->GetControlRotation().Yaw,0.f).Quaternion();
        BluntSlamEye=Character->GetMeleeAimTransform().GetLocation();
    }
    SwingSeconds=UsesThunderThrowHeavy()?ThunderHammerThrow::Duration:UsesFinalTollHeavy()?FinalTollHeavy::Duration:bHeavy?WarhammerHeavy::Duration:float(ToolStats.SwingSeconds*RateScale);
    ContactSeconds=UsesThunderThrowHeavy()?ThunderHammerThrow::Release:UsesFinalTollHeavy()?FinalTollHeavy::FirstContact:bHeavy?WarhammerHeavy::Contact:float(ToolStats.ContactSeconds*RateScale);
    SelectBluntMotion();
    if(bConfirmed&&Elapsed>=0.f)
    {
        // The owner already predicted this hit at contact: keep its running hit stop.
        if(!bHeavy&&bHitConfirmed){bContacted=true;return;}
        // A late confirmation can arrive after a miss chain already began.
        if(!bHeavy&&(bBluntChain||Elapsed>RealContactSeconds()+.02f)){bBluntChain=false;HandOffBluntPose();}
        bHitConfirmed=true;bContacted=true;
        if(!bHeavy)Elapsed=RealContactSeconds();
    }
}

bool UProductionToolComponent::ApplyBluntStaminaReceipt(UColdSteelStatusModel* Profile,uint32 AttackId,float Amount)
{
    if(!Profile||static_cast<int32>(AttackId-LastBluntStaminaReceipt)<=0||!FMath::IsFinite(Amount)||Amount<0.f)return false;
    LastBluntStaminaReceipt=AttackId;
    // Accepted costs survive animation cancellation or a later equipment change.
    // Local regeneration/other spending may have advanced since the server's cut.
    if(Amount>0.f)
    {
        Profile->SpendStamina(FMath::Min(Profile->Stamina(),Amount));
        Profile->DelayStaminaRecovery();
    }
    return true;
}

void UProductionToolComponent::ClientBluntStaminaSpent_Implementation(uint32 AttackId,float Amount)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||Pawn->HasAuthority()||!Pawn->IsLocallyControlled())return;
    ApplyBluntStaminaReceipt(ColdSteelAuthority::ForPawn(Pawn),AttackId,Amount);
}

void UProductionToolComponent::SendBluntMartialReceipt(UColdSteelStatusModel* Profile,uint32 AttackId,float Amount)
{
    if(!Profile||!GetWorld())return;
    const auto State=Profile->Snapshot();const auto* GS=GetWorld()->GetGameState();
    ClientBluntMartialCommitted(AttackId,Amount,State.MartialCooldownRevision,
        State.WhirlwindCooldown,State.WhirlwindCooldownDuration,State.SwordUppercutCooldown,State.SwordUppercutCooldownDuration,
        GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds());
}

void UProductionToolComponent::ClientBluntMartialCommitted_Implementation(uint32 AttackId,float Amount,int64 Revision,
    float Whirlwind,float WhirlwindDuration,float Uppercut,float UppercutDuration,double ServerAt)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||Pawn->HasAuthority()||!Pawn->IsLocallyControlled())return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);if(!Profile)return;
    ApplyBluntStaminaReceipt(Profile,AttackId,Amount);
    auto State=Profile->Snapshot();auto Incoming=State;
    Incoming.MartialCooldownRevision=Revision;
    Incoming.WhirlwindCooldown=Whirlwind;Incoming.WhirlwindCooldownDuration=WhirlwindDuration;
    Incoming.SwordUppercutCooldown=Uppercut;Incoming.SwordUppercutCooldownDuration=UppercutDuration;
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():ServerAt;
    ColdSteelProfileRecovery::MartialCooldowns(State,Incoming,float(FMath::Max(0.,Now-ServerAt)));
    // This receipt carries only blunt skills; the chain-slash clock is already local-time adjusted.
    State.ChainSlashCooldown=Profile->ChainSlashCooldown();State.ChainSlashCooldownDuration=Profile->ChainSlashCooldownDuration();
    State.LeapStrikeCooldown=Profile->LeapStrikeCooldown();State.LeapStrikeCooldownDuration=Profile->LeapStrikeCooldownDuration();
    State.ShadowStepCooldown=Profile->ShadowStepCooldown();State.ShadowStepCooldownDuration=Profile->ShadowStepCooldownDuration();
    Profile->AdoptNetMirror(State);Profile->OnStaminaChanged.Broadcast();
}
