#include "ProductionToolComponent.h"
#include "ProductionBluntCombo.h"
#include "WarhammerHeavyMotion.h"
#include "WarhammerCombat.h"
#include "RuneboundHammerTuning.h"
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
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"

namespace
{
bool CanCommitBlunt(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    return Pawn&&Pawn->HasAuthority()&&Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item)&&PC&&
        !Pawn->IsTraversing()&&!Pawn->IsCastBlockingLeftHandAction()&&(!Health||!Health->IsDead())&&
        (!Sword||!Sword->IsGuarding())&&(!PS||!PS->IsQuickCombatExecuting(Pawn))&&
        !AFPSGAMEPlayerController::BlocksOngoingActions(PC)&&(!Building||!Building->IsBuilding());
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

void UProductionToolComponent::ServerBeginBluntCharge_Implementation(uint32 AttackId)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    if(!GetWorld()||bBluntUppercut||bBluntWhirlwind||!CanCommitBlunt(Pawn,Profile)||Profile->Stamina()<=0.f||GetWorld()->GetTimeSeconds()<BluntServerReadyAt)
    {ClientBluntAttackResult(AttackId,0,false,false,false);return;}
    Character=Pawn;BluntServerAttackId=AttackId;bBluntServerCharging=true;
    BluntServerChargeStartedAt=GetWorld()->GetTimeSeconds();
    BluntServerChargeInstance=Profile->ActiveProductionTool()->InstanceId;
}

void UProductionToolComponent::ServerBeginBluntAttack_Implementation(uint32 AttackId,bool bReleaseCharge,bool bSprintAttack)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* World=GetWorld();
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto Reject=[&]()
    {
        BluntServerNextStage=0;BluntServerComboExpires=0.;bBluntServerCharging=false;
        ClientBluntAttackResult(AttackId,0,false,false,false);
    };
    const bool NewRequest=int32(AttackId-BluntLastServerRequestId)>0;
    if(NewRequest)BluntLastServerRequestId=AttackId;
    if(bSprintAttack&&!NewRequest)return; // duplicates cannot reopen movement or cancel the accepted pose
    // A buffered cut leaves the owner on the frame its previous cut ends, so
    // network jitter (or float/double clock drift on a listen host) can land
    // it a few ms before this clock. Accept such an ordinary cut but start its
    // server clock at the ready time: contact, cadence and DPS stay exactly
    // server-timed. Charge releases and sprint attacks keep the strict check.
    constexpr double BufferedCutTolerance=.12;
    const double Now=World?World->GetTimeSeconds():0.;
    const double Early=bReleaseCharge||bSprintAttack?0.:FMath::Clamp(BluntServerReadyAt-Now,0.,BufferedCutTolerance);
    if(!World||bBluntUppercut||bBluntWhirlwind||!CanCommitBlunt(Pawn,Profile)||Now+Early<BluntServerReadyAt){Reject();return;}
    const auto* Item=Profile->ActiveProductionTool();const FString SourceInstance=Item->InstanceId;
    if(bSprintAttack&&(bReleaseCharge||BluntSprintInstance!=SourceInstance||World->GetTimeSeconds()-BluntSprintReadyAt>.35))
    {Reject();return;}
    if(bReleaseCharge&&(!bBluntServerCharging||BluntServerAttackId!=AttackId||BluntServerChargeInstance!=SourceInstance||Profile->Stamina()<=0.f)){Reject();return;}
    const float Held=bReleaseCharge?float(World->GetTimeSeconds()-BluntServerChargeStartedAt):0.f;
    Character=Pawn;ApplyToolStats(Item,Profile);
    const bool Heavy=bSprintAttack||(bReleaseCharge&&Held>=BluntChargeSeconds);
    const bool Toll=Heavy&&!bSprintAttack&&bFinalTollHead;
    const float Resume=Heavy||bSprintAttack?0.f:BluntChargeResume(Held);
    bBluntServerCharging=false;
    const FProductionToolStats Stats=ToolStats;
    const double AttackCost=Heavy&&!bSprintAttack?Stats.HeavyReleaseStaminaCost:Stats.StaminaCost;
    if(!Profile->SpendStamina(float(AttackCost))){Reject();return;}
    ClientBluntStaminaSpent(AttackId,float(AttackCost));
    Item=Profile->ActiveProductionTool();
    if(!Item||Item->InstanceId!=SourceInstance){Reject();return;}
    if(BluntServerInstance!=SourceInstance||World->GetTimeSeconds()>BluntServerComboExpires||Held>.20f)BluntServerNextStage=0;
    const int32 Stage=bSprintAttack?2:BluntServerNextStage;
    BluntServerNextStage=Heavy||bSprintAttack?0:(Stage+1)%3;
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    BluntServerInstance=SourceInstance;BluntServerAttackId=AttackId;
    bBluntServerSprintAttack=bSprintAttack;
    if(bSprintAttack)BluntSprintLungeDistance=Profile->DashAttackStats().DistanceCM;
    AxeStrike=ColdSteelSkills::Snapshot(Pawn,Item);AxeStrike.bMelee=true;
    AxeStrike.DamagePanel=WarhammerCombat::Damage(Stats.Damage,Profile,bSprintAttack,Heavy,BluntHeavyMultiplier,Stage);
    AxeStrike.ToughnessDamageMultiplier=float(Stats.ToughnessDamage);
    const float ActionRate=Toll?HasteActionRate:bSprintAttack?HasteActionRate:Heavy?RateScale*BluntMasteryInterval:RateScale;
    if(Toll)FinalTollActionRate=ActionRate;
    const float Lift=bSprintAttack?WarhammerSprint::LiftSeconds/HasteActionRate:0.f;
    BluntServerSprintStartedAt=Now;
    const float Contact=float(Early)+(Toll?FinalTollHeavy::FirstContact/ActionRate:Heavy?Lift+WarhammerHeavy::Contact/ActionRate:float(Stats.ContactSeconds)-Resume);
    BluntServerSprintMoveUntil=bSprintAttack?Now+FMath::Min(Lift+.15f,Contact):0.;
    BluntServerReadyAt=Now+Early+(Toll?FinalTollHeavy::Duration/ActionRate:Heavy?Lift+WarhammerHeavy::RealDuration(ActionRate):Stats.SwingSeconds-Resume);
    FinalTollHeavySerial=Toll?AxeStrike.MasteryAttackSerial:0;FinalTollCommitUntil=RuneboundClock()+FinalTollHeavy::Duration/ActionRate+.1;
    BluntServerGroundSlamUntil=Heavy&&!Toll?BluntServerReadyAt:0.;
    BluntServerSprintContactAt=bSprintAttack?Now+Contact:0.;
    if(Heavy&&!Toll)
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
    const float StunSeconds=Heavy&&!bSprintAttack?BluntHeavyStunSeconds:0.f;
    const FString CommittedData=Item->Data;
    const auto Committed=AxeStrike;
    World->GetTimerManager().SetTimer(BluntContactTimer,FTimerDelegate::CreateWeakLambda(this,[this,SourceInstance,AttackId,Stage,Heavy,bSprintAttack,StunSeconds,Toll,CommittedData,Committed]()
    {
        auto* OwnerPawn=Character.Get();auto* OwnerProfile=ColdSteelAuthority::ForPawn(OwnerPawn);
        const auto* Current=OwnerProfile?OwnerProfile->ActiveProductionTool():nullptr;
        if(BluntServerAttackId!=AttackId)return;
        if(!CanCommitBlunt(OwnerPawn,OwnerProfile)||!Current||Current->InstanceId!=SourceInstance)
        {BluntServerNextStage=0;BluntServerGroundSlamUntil=0.;bBluntServerSprintAttack=false;BluntServerSprintContactAt=0.;ClientBluntAttackResult(AttackId,Stage,false,false,Heavy,bSprintAttack);return;}
        if(Toll&&(BluntServerAttackId!=AttackId||Current->Data!=CommittedData||!RuneboundHammer::HasFinalToll(*Current)))return;
        if(Toll)AxeStrike=Committed;
        ColdSteelAuthority::FScope Scope(OwnerProfile);
        if(bSprintAttack){UpdateBluntSprintAnchor(true);BluntServerSprintContactAt=0.;}
        const bool Confirmed=Toll?ResolveBluntContact():Heavy?BeginBluntShockwave(StunSeconds):ResolveBluntContact();
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
            if(BluntServerAttackId!=AttackId||!CanCommitBlunt(OwnerPawn,OwnerProfile)||!Current||Current->InstanceId!=SourceInstance||Current->Data!=CommittedData||!RuneboundHammer::HasFinalToll(*Current))return;
            ColdSteelAuthority::FScope Scope(OwnerProfile);
            AxeStrike=Committed;AxeStrike.MasteryAttackSerial=ColdSteelSkills::Snapshot(OwnerPawn,Current).MasteryAttackSerial;
            FinalTollHeavySerial=AxeStrike.MasteryAttackSerial;
            const bool Confirmed=ResolveBluntContact();
            if(Confirmed)ClientBluntAttackResult(AttackId,Stage,true,true,true,false);
        }),FinalTollHeavy::SecondContact/ActionRate,false);
    }
}

void UProductionToolComponent::ServerCancelBluntAttack_Implementation(uint32 AttackId)
{
    if(AttackId!=BluntServerAttackId)return;
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

void UProductionToolComponent::ClientBluntAttackResult_Implementation(uint32 AttackId,int32 Stage,bool bAccepted,bool bConfirmed,bool bHeavy,bool bSprint)
{
    // Cancellation still retires the matching movement after the local pose has finished.
    if(!bAccepted)if(auto* Pawn=Character.Get())
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))Move->CancelHammerSprintMove(AttackId);
    if(Kind!=TEXT("warhammer")||AttackId!=BluntAttackId||(!bBluntCharging&&Elapsed<0.f))return;
    if(!bAccepted){if(bBluntCharging)CancelHeavyCharge();else CancelUse();return;}
    if(bBluntHeavy!=bHeavy)Elapsed=0.f;
    // The server owns the combo stage; a chained cut predicted another stage.
    if(Stage!=BluntStage&&BluntStartClip>0.f){BluntStartClip=0.f;HandOffBluntPose();}
    bBluntHeavy=bHeavy;bBluntSprintAttack=bSprint;BluntStage=Stage;
    if(bHeavy&&!UsesFinalTollHeavy()&&!bBluntFloorTarget)
    {
        FHitResult Floor;bBluntFloorTarget=FindBluntGround(Floor);
        if(bBluntFloorTarget){BluntFloorPoint=Floor.ImpactPoint;BluntFloorNormal=Floor.ImpactNormal;}
        BluntSlamRotation=FRotator(0.f,Character->GetControlRotation().Yaw,0.f).Quaternion();
        BluntSlamEye=Character->GetMeleeAimTransform().GetLocation();
    }
    SwingSeconds=UsesFinalTollHeavy()?FinalTollHeavy::Duration:bHeavy?WarhammerHeavy::Duration:float(ToolStats.SwingSeconds*RateScale);
    ContactSeconds=UsesFinalTollHeavy()?FinalTollHeavy::FirstContact:bHeavy?WarhammerHeavy::Contact:float(ToolStats.ContactSeconds*RateScale);
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
    Profile->AdoptNetMirror(State);Profile->OnStaminaChanged.Broadcast();
}
