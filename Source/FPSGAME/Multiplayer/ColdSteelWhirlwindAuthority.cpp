#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "UppercutStaminaReceipt.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordOverheadRhythm.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

bool AColdSteelPlayerState::RequestSwordWhirlwind(bool Zhufeng,const FVector& Direction)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!Pawn||!Item||!ColdSteelInventory::IsTwoHandedSword(*Item)||Model->ActiveProductionTool()||
        WhirlwindSequence!=WhirlwindReceiptSequence||Model->WhirlwindCooldown()>0.f||
        !Model->CanSpendStamina(Model->WhirlwindStats().StaminaCost)||
        (Zhufeng?(!ColdSteelModularSword::UsesZhufengWhirlwind(*Item)||Model->MasteryProgress(TEXT("dashAttack")).Level<1):
            Model->MasteryProgress(TEXT("whirlwind")).Level<1))return false;
    ++WhirlwindSequence;if(!WhirlwindSequence)++WhirlwindSequence;
    uint32 MoveSequence=0;
    if(Zhufeng)
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))
        {Move->BeginMeleeLungeRequest(EFPSMeleeMove::Zhufeng,Direction);MoveSequence=Move->MeleeRequest.Sequence;}
    // Use the hit-report actor channel so accepted payment precedes every contact.
    ServerSwordWhirlwind(WhirlwindSequence,Pawn,Item->InstanceId,Zhufeng,MoveSequence,Direction,false);
    return true;
}

void AColdSteelPlayerState::FinishSwordWhirlwind()
{ServerSwordWhirlwind(WhirlwindSequence,GetPawn(),FString(),false,0,FVector::ForwardVector,true);}

bool AColdSteelPlayerState::IsSwordWhirlwindExecuting(const APawn* Pawn) const
{return WhirlwindActiveSequence&&WhirlwindPawn.Get()==Pawn&&GetWorld()->GetTimeSeconds()<WhirlwindUntil;}

void AColdSteelPlayerState::ServerSwordWhirlwind_Implementation(uint32 Sequence,APawn* ActionPawn,
    const FString& Weapon,bool Zhufeng,uint32 MoveSequence,FVector_NetQuantizeNormal Direction,bool Finish)
{
    if(!HasAuthority())return;
    if(Finish)
    {
        if(Sequence==WhirlwindActiveSequence&&ActionPawn==WhirlwindPawn.Get())SettleSwordWhirlwind();
        return;
    }
    if(!Sequence||static_cast<int32>(Sequence-WhirlwindReceivedSequence)<=0)return;
    WhirlwindReceivedSequence=Sequence;TickSwordWhirlwind(0.f);
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Item=ShadowModel?ShadowModel->Equipped():nullptr;
    const auto* HP=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    const auto* GS=GetWorld()->GetGameState();
    const double Clock=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const auto Reply=[&](bool Accepted)
    {
        const auto State=ShadowModel?ShadowModel->Snapshot():FColdSteelProfile();
        ClientSwordWhirlwindResult(Sequence,ActionPawn,Accepted,State.UppercutStaminaSpent,
            State.WhirlwindCooldown,State.WhirlwindCooldownDuration,State.MartialCooldownRevision,Clock);
    };
    if(WhirlwindActiveSequence||UppercutActiveSequence||!Pawn||Pawn!=ActionPawn||!ShadowModel||!HP||HP->IsDead()||
        !Item||Item->InstanceId!=Weapon||!ColdSteelInventory::IsTwoHandedSword(*Item)||ShadowModel->ActiveProductionTool()||
        Pawn->IsTraversing()||Pawn->IsDodging()||(!Zhufeng&&Pawn->IsSliding())||Pawn->IsCastBlockingLeftHandAction()||
        IsQuickCombatExecuting(Pawn)||!PendingCastSkill.IsNone()||(Sword&&Sword->IsGuarding())||
        UBoundCongregateCaptureComponent::IsCaptured(Pawn)||(Status&&Status->BlocksMovement()))
    {Reply(false);return;}
    if(Zhufeng&&(!ColdSteelModularSword::UsesZhufengWhirlwind(*Item)||!MoveSequence||Direction.ContainsNaN()||
        FVector(Direction).GetSafeNormal2D().IsNearlyZero()||GetWorld()->GetTimeSeconds()>WhirlwindDashReadyUntil))
    {Reply(false);return;}
    ColdSteelAuthority::FScope Scope(ShadowModel);
    const FColdSteelItem CastItem=*Item;
    const auto CastStats=ShadowModel->WhirlwindStats();const float Before=ShadowModel->Stamina();
    if(!ShadowModel->CommitWhirlwindCast(CastStats,Zhufeng)){Reply(false);return;}
    // Reuse the cumulative martial receipt ledger so late mirrors/uploads cannot
    // undo this payment or charge it twice after an animation has ended.
    ShadowModel->Current.UppercutStaminaSpent+=FMath::Max(0.f,Before-ShadowModel->Stamina());
    ServerWhirlwindCast=CastStats;WhirlwindActiveSequence=Sequence;WhirlwindMoveSequence=MoveSequence;
    WhirlwindPawn=Pawn;WhirlwindWeapon=Weapon;WhirlwindRewardModel=ShadowModel;bWhirlwindZhufeng=Zhufeng;
    WhirlwindStartedAt=GetWorld()->GetTimeSeconds();WhirlwindTargets.Reset();WhirlwindHits=WhirlwindKills=0;
    const auto& T=ShadowModel->MasteryDefinition(TEXT("whirlwind")).Whirlwind;
    WhirlwindReadySeconds=T.ReadySeconds;WhirlwindMoveSeconds=T.ReadySeconds+T.SpinSeconds;
    WhirlwindUntil=WhirlwindStartedAt+WhirlwindMoveSeconds+T.RecoverSeconds+(Zhufeng?0.f:T.HitStopBudget)+.35;
    WhirlwindMoveSpeed=Zhufeng?ShadowModel->DashAttackStats().DistanceCM/RuneSwordOverheadRhythm::DashWindupSeconds:0.f;
    WhirlwindMoveDirection=FVector(Direction).GetSafeNormal2D();
    const auto M=ColdSteelMelee::Evaluate(CastItem,ShadowModel).Modifiers;
    WhirlwindRuneVulnerability=M.RuneVulnerability;WhirlwindRuneSeconds=M.RuneVulnerabilitySeconds;
    WhirlwindCooldownReduction=CastItem.Definition==TEXT("ue_rune_sword")?.5f+float(M.CooldownReduceSecondsPerHit):0.f;
    bWhirlwindCooldownReduced=false;WhirlwindSprintSeconds=0.f;WhirlwindDashReadyUntil=-1.;
    if(Zhufeng&&Pawn->IsSliding())Pawn->StopSlide(true);
    Pawn->StopMovementForMeleeSkill();
    if(Zhufeng)if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))
        Move->PendingLaunchVelocity.X=Move->PendingLaunchVelocity.Y=0.;
    bServerDirty=true;Reply(true);
}

bool AColdSteelPlayerState::ValidateSwordWhirlwindHit(const FColdSteelNetHitReport& R,
    const AFPSGAMECharacter* Pawn,FString& Reason) const
{
    const auto* Item=ShadowModel?ShadowModel->Equipped():nullptr;
    if(R.AttackMeta!=0x20||!R.WhirlwindSerial||R.WhirlwindSerial!=WhirlwindActiveSequence||
        !IsSwordWhirlwindExecuting(Pawn)||!(R.Flags&(1<<3))||(R.Flags&(1<<4))||
        GetWorld()->GetTimeSeconds()+.12<WhirlwindStartedAt+WhirlwindReadySeconds||WhirlwindTargets.Contains(R.Target.Get()))
    {Reason=TEXT("whirlwind not committed, not released or duplicate target");return false;}
    if(!Item||Item->InstanceId!=WhirlwindWeapon||Item->Definition!=R.ItemDefinition||ShadowModel->ActiveProductionTool())
    {Reason=TEXT("whirlwind equipment changed");return false;}
    return true;
}

bool AColdSteelPlayerState::SwordWhirlwindMove(uint32 MoveSequence,FVector& Direction,float& DistanceLimit) const
{
    if(!bWhirlwindZhufeng||!MoveSequence||MoveSequence!=WhirlwindMoveSequence||!IsSwordWhirlwindExecuting(GetPawn()))return false;
    Direction=WhirlwindMoveDirection;
    // A late cumulative move may catch up; it cannot teleport the entire cast
    // on its first packet. The small allowance covers actor-channel ordering.
    const float Age=FMath::Clamp(float(GetWorld()->GetTimeSeconds()-WhirlwindStartedAt)+.12f,0.f,WhirlwindMoveSeconds);
    DistanceLimit=WhirlwindMoveSpeed*Age;
    return true;
}

void AColdSteelPlayerState::ConfirmSwordWhirlwindHit(AFPSGAMECharacter* Pawn,AActor* Target,float Applied,bool Killed)
{
    if(Applied<=0.f||!Target||!WhirlwindRewardModel)return;
    auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    if(Combat&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
    {++WhirlwindHits;if(Killed)++WhirlwindKills;}
    if(Combat&&!Killed)
    {
        Combat->ReceiveStun(Pawn,ServerWhirlwindCast.StunSeconds,ServerWhirlwindCast.KnockbackCM);
        if(WhirlwindRuneVulnerability>0.f)
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddRuneMagicVulnerability(WhirlwindRuneVulnerability,WhirlwindRuneSeconds);
    }
    if(WhirlwindCooldownReduction>0.f&&!bWhirlwindCooldownReduced)
    {bWhirlwindCooldownReduced=true;WhirlwindRewardModel->ReduceAllAbilityCooldowns(WhirlwindCooldownReduction);}
}

void AColdSteelPlayerState::SettleSwordWhirlwind()
{
    if(!HasAuthority()||!WhirlwindActiveSequence)return;
    auto* Model=WhirlwindRewardModel.Get();const int32 Hits=WhirlwindHits,Kills=WhirlwindKills;
    const bool Zhufeng=bWhirlwindZhufeng;
    WhirlwindActiveSequence=WhirlwindMoveSequence=0;WhirlwindUntil=0.;WhirlwindWeapon.Reset();WhirlwindRewardModel=nullptr;
    WhirlwindTargets.Reset();WhirlwindHits=WhirlwindKills=0;bWhirlwindZhufeng=false;
    if(Model){ColdSteelAuthority::FScope Scope(Model);if(Zhufeng)Model->TrainDashAttack(Hits,Kills);else Model->TrainWhirlwind(Hits,Kills);}
    bServerDirty=true;
}

void AColdSteelPlayerState::TickSwordWhirlwind(float Delta)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());const auto* Item=ShadowModel?ShadowModel->Equipped():nullptr;
    const auto* HP=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(WhirlwindActiveSequence)
    {
        const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
        if(!Pawn||Pawn!=WhirlwindPawn.Get()||(HP&&HP->IsDead())||!Item||Item->InstanceId!=WhirlwindWeapon||
            ShadowModel->ActiveProductionTool()||Pawn->IsTraversing()||Pawn->IsDodging()||
            UBoundCongregateCaptureComponent::IsCaptured(Pawn)||(Status&&Status->BlocksMovement())||GetWorld()->GetTimeSeconds()>=WhirlwindUntil)
            SettleSwordWhirlwind();
        return;
    }
    const auto* Move=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    if(!Move||!Item||!ColdSteelInventory::IsTwoHandedSword(*Item)||ShadowModel->ActiveProductionTool()||
        (HP&&HP->IsDead())||UppercutActiveSequence||Pawn->IsDodging()||Pawn->IsTraversing()||
        ShadowModel->MasteryProgress(TEXT("dashAttack")).Level<1)
    {WhirlwindSprintSeconds=0.f;WhirlwindDashReadyUntil=-1.;return;}
    if(WhirlwindSprintWeapon!=Item->InstanceId)
    {WhirlwindSprintWeapon=Item->InstanceId;WhirlwindSprintSeconds=0.f;WhirlwindDashReadyUntil=-1.;}
    const auto& D=ShadowModel->MasteryDefinition(TEXT("dashAttack"));
    const int32 L=FMath::Clamp(ShadowModel->MasteryProgress(D.Id).Level,1,D.MaxLevel);
    const float Ready=FMath::Max(.01f,D.DashAttack.ReadySeconds*(1.f-(L-1)*D.DashAttack.ReadyReductionPerLevel));
    const bool Sprint=Move->bWantsToSprint&&Move->IsMovingOnGround()&&!Pawn->IsSliding()&&Pawn->GetVelocity().SizeSquared2D()>2500.f;
    const bool Carry=WhirlwindSprintSeconds>=Ready&&(Pawn->IsSliding()||Move->IsFalling()||!Move->PendingLaunchVelocity.IsZero());
    WhirlwindSprintSeconds=Sprint?FMath::Min(Ready,WhirlwindSprintSeconds+Delta):Carry?Ready:0.f;
    if(WhirlwindSprintSeconds+.08f>=Ready)WhirlwindDashReadyUntil=GetWorld()->GetTimeSeconds()+.25;
}

void AColdSteelPlayerState::ClientSwordWhirlwindResult_Implementation(uint32 Sequence,APawn* ActionPawn,bool Accepted,
    double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt)
{
    if(HasAuthority()||!Sequence||static_cast<int32>(Sequence-WhirlwindReceiptSequence)<=0)return;
    WhirlwindReceiptSequence=Sequence;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Pawn||Pawn!=ActionPawn||!Pawn->IsLocallyControlled()||!Model)return;
    if(Accepted)
    {
        auto* Exhaustion=Pawn->FindComponentByClass<UFPSExhaustionComponent>();
        if(Exhaustion)Exhaustion->ObserveStamina(Model->Current.Stamina);
        UppercutStaminaReceipt::Merge(Model->Current,TotalSpent);Model->DelayStaminaRecovery();
        if(Exhaustion)Exhaustion->ObserveStamina(Model->Current.Stamina);
    }
    if(Revision>=Model->Current.MartialCooldownRevision)
    {
        const auto* GS=GetWorld()->GetGameState();const double Now=GS?GS->GetServerWorldTimeSeconds():ServerAt;
        Model->Current.WhirlwindCooldown=FMath::Max(0.f,Cooldown-float(FMath::Max(0.,Now-ServerAt)));
        Model->Current.WhirlwindCooldownDuration=Duration;Model->Current.MartialCooldownRevision=Revision;
    }
    Model->OnStaminaChanged.Broadcast();
    if(!Accepted&&Sequence==WhirlwindSequence)
    {
        if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsWhirlwindActive())Sword->CancelAction();
        Model->PostNotice(TEXT("旋风未执行"),TEXT("服务器体力、冷却或冲刺准备不满足条件"));
    }
}
