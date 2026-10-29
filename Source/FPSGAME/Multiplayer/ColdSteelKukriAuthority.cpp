#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "UppercutStaminaReceipt.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriDashRhythm.h"
#include "../Weapons/Kukri/KukriAttackTiming.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/LightningHasteSpeed.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

uint32 AColdSteelPlayerState::ResolveKukriRuneAttackSerial(const FColdSteelNetHitReport& R,uint32 SnapshotSerial)
{
    if(KukriRunePawn.Get()!=GetPawn())
    {
        KukriRunePawn=GetPawn();
        for(int32 I=0;I<5;++I){KukriRuneSequences[I]=0;KukriRuneAttackIds[I]=0;}
    }
    int32 Family=0;uint32 Sequence=KukriAttack.Serial;
    if(R.AttackMeta&0x80){Family=1;Sequence=QuickCombatServerSequence;}
    else if(R.AttackMeta==SwordUppercut::AttackMeta){Family=2;Sequence=UppercutActiveSequence;}
    else if(R.AttackMeta&0x20){Family=3;Sequence=WhirlwindActiveSequence;}
    else if((R.AttackMeta&0x10)&&R.AttackMeta!=0x16)
    {
        Family=4;
        const auto* Weapon=GetPawn()?GetPawn()->FindComponentByClass<UKukriWeaponComponent>():nullptr;
        Sequence=Weapon?Weapon->GetNetworkHeavyReleaseSerial():0;
    }
    if(!Sequence||!SnapshotSerial)return 0;
    if(KukriRuneSequences[Family]!=Sequence)
    {
        KukriRuneSequences[Family]=Sequence;
        KukriRuneAttackIds[Family]=SnapshotSerial;
    }
    return KukriRuneAttackIds[Family];
}

uint32 AColdSteelPlayerState::RequestKukriAttack(const FString& Main,const FString& Offhand,uint8 Stage,bool Dash,const FVector& Direction,uint32 MasterySerial)
{
    if(HasAuthority()||!GetPawn()||Main.IsEmpty())return 0;
    if(!++KukriSequence)++KukriSequence;
    // Begin, hits and finish share this reliable PlayerState channel.
    const auto* GS=GetWorld()->GetGameState();
    const double StartedAt=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    ServerBeginKukriAttack(KukriSequence,GetPawn(),Main,Offhand,Stage,Dash,Direction.GetSafeNormal2D(),MasterySerial,StartedAt);
    return KukriSequence;
}

void AColdSteelPlayerState::FinishKukriAttack(uint32 Serial,bool Cancelled)
{if(Serial)ServerFinishKukriAttack(Serial,GetPawn(),Cancelled);}

bool AColdSteelPlayerState::MatchesKukriEquipment() const
{
    const auto* Main=ShadowModel&&!ShadowModel->ActiveProductionTool()?ShadowModel->Equipped():nullptr;
    const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,ShadowModel);
    return Main&&Main->InstanceId==KukriAttack.Main&&KukriAttack.Pawn.Get()==GetPawn()&&
        (Off?Off->InstanceId:FString())==KukriAttack.Offhand;
}

void AColdSteelPlayerState::ClearKukriAttack()
{
    if(auto* Pawn=Cast<AFPSGAMECharacter>(KukriAttack.Pawn.Get()))
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))
            Move->CancelKukriAttackMove(KukriAttack.Serial);
    const auto Previous=MoveTemp(KukriAttack);
    KukriAttack=FKukriAttackReceipt();
    if(Previous.Dash)if(auto* Model=Previous.RewardModel.Get())
    {Model->TrainDashAttack(Previous.Hits,Previous.Kills);bServerDirty=true;}
}

void AColdSteelPlayerState::ServerBeginKukriAttack_Implementation(uint32 Serial,APawn* ActionPawn,
    const FString& MainId,const FString& OffId,uint8 Stage,bool Dash,FVector_NetQuantizeNormal Direction,uint32 MasterySerial,double ClientStartedAt)
{
    if(!HasAuthority()||!Serial||static_cast<int32>(Serial-KukriReceivedSequence)<=0)return;
    KukriReceivedSequence=Serial;
    TickKukriAuthority(0.f);
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Main=ShadowModel&&!ShadowModel->ActiveProductionTool()?ShadowModel->Equipped():nullptr;
    const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,ShadowModel);
    const auto* HP=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const double Now=GetWorld()->GetTimeSeconds();
    const auto Reply=[&](bool Accepted){ClientKukriAttackResult(Serial,ActionPawn,Accepted,
        ShadowModel?ShadowModel->Snapshot().UppercutStaminaSpent:0.);};
    // Reliable begin/hit messages can arrive in one frame after loss or a host
    // hitch. Use the same bounded server-clock domain as the hit report, while
    // keeping cadence on this timeline so backdating cannot accelerate a chain.
    if(!FMath::IsFinite(ClientStartedAt)||ClientStartedAt<=0.||ClientStartedAt>Now+.1||Now-ClientStartedAt>.9)
    {Reply(false);return;}
    const double StartedAt=FMath::Min(ClientStartedAt,Now);
    if(!Pawn||Pawn!=ActionPawn||!ShadowModel||!Main||Main->Definition!=TEXT("ue_kukri")||
        Main->InstanceId!=MainId||(Off?Off->InstanceId:FString())!=OffId||Stage>=KukriRhythm::SwingCount||
        !MasterySerial||!HP||HP->IsDead()||Pawn->IsTraversing()||Pawn->IsDodging()||(!Dash&&Pawn->IsSliding())||
        Pawn->IsCastBlockingLeftHandAction()||UBoundCongregateCaptureComponent::IsCaptured(Pawn)||
        (Status&&Status->BlocksMovement())||IsQuickCombatExecuting(Pawn)||IsSwordWhirlwindExecuting(Pawn)||
        UppercutActiveSequence||!PendingCastSkill.IsNone()||Direction.ContainsNaN()||FVector(Direction).GetSafeNormal2D().IsNearlyZero())
    {Reply(false);return;}
    const FString Key=MainId+TEXT("|")+OffId;
    if(Key==KukriChainKey&&StartedAt+.08<KukriReadyAt){Reply(false);return;}
    // Stages follow accepted starts, including misses; swapping either blade resets the chain.
    const uint8 Expected=Key==KukriChainKey&&StartedAt<=KukriChainUntil?KukriNextStage:0;
    if((!Dash&&Stage!=0&&Stage!=Expected)||(Dash&&(ShadowModel->MasteryProgress(TEXT("dashAttack")).Level<1||
        KukriSprintKey!=Key||KukriSprintPawn.Get()!=Pawn||StartedAt>KukriDashReadyUntil)))
    {Reply(false);return;}
    ColdSteelAuthority::FScope Scope(ShadowModel);
    const float MainRate=FMath::Max(.01f,KukriAttackTiming::PlayRate(ColdSteelMelee::Evaluate(*Main,ShadowModel).AttackRate));
    const float OffRate=Off?FMath::Max(.01f,KukriAttackTiming::PlayRate(ColdSteelMelee::Evaluate(*Off,ShadowModel).AttackRate)):MainRate;
    const float SkillRate=FMath::Max(.05f,LightningHaste::ActionSpeed(Pawn));
    const float Cost=Dash?ShadowModel->DashAttackStats().StaminaCost:ColdSteelMelee::ComboAttackStamina(Main,ShadowModel,Off!=nullptr);
    const float Before=ShadowModel->Stamina();
    if(!ShadowModel->SpendStamina(Cost)){Reply(false);return;}
    // Only confirmed costs enter the persisted cumulative ledger. Never debit at each hit.
    ShadowModel->Current.UppercutStaminaSpent+=FMath::Max(0.f,Before-ShadowModel->Stamina());
    ClearKukriAttack();
    auto& A=KukriAttack;A.Serial=Serial;A.MasterySerial=MasterySerial;A.Pawn=Pawn;A.RewardModel=ShadowModel;
    A.Main=MainId;A.Offhand=OffId;A.Dash=Dash;A.Stage=Stage;
    if(Dash)A.DashKnockback=ShadowModel->DashAttackStats().KnockbackCM;
    A.Started=StartedAt;A.Direction=FVector(Direction).GetSafeNormal2D();
    A.ThrustRate=KukriAttackTiming::PairedPlayRate(MainRate,OffRate);
    const bool Dual=!OffId.IsEmpty();
    const float Duration=Dash?KukriDashRhythm::Seconds/SkillRate:
        KukriAttackReceipt::Seconds(Stage,Dual,KukriAttackReceipt::Length(Stage,Dual),MainRate,OffRate);
    for(int32 Hand=0;Hand<2;++Hand)
    {
        const float Offset=Dual&&Stage<2&&Hand==1?KukriRhythm::DualSweepOffset(Stage):0.f;
        const float Start=Dual&&Stage==2?KukriRhythm::DualThrustContactStart:KukriRhythm::Swings[Stage].ContactStart+Offset;
        const float End=Dual&&Stage==2?KukriRhythm::DualThrustContactEnd:KukriRhythm::Swings[Stage].ContactEnd+Offset;
        A.ContactStart[Hand]=Dash?KukriDashRhythm::ContactStart/SkillRate:KukriAttackReceipt::Seconds(Stage,Dual,Start,MainRate,OffRate);
        A.ContactEnd[Hand]=Dash?KukriDashRhythm::ContactEnd/SkillRate:KukriAttackReceipt::Seconds(Stage,Dual,End,MainRate,OffRate);
    }
    // Fixed presentation/hit-stop allowance; it does not permit early contacts or faster next attacks.
    A.Until=StartedAt+Duration+.5;
    KukriReadyAt=StartedAt+Duration;KukriChainKey=Key;
    KukriNextStage=Dash?0:(Stage+1)%KukriRhythm::SwingCount;
    KukriChainUntil=Dash?0.:A.Until+KukriRhythm::ComboResetSeconds;
    KukriSprintSeconds=0.f;KukriDashReadyUntil=-1.;
    bServerDirty=true;Reply(true);
}

void AColdSteelPlayerState::ServerFinishKukriAttack_Implementation(uint32 Serial,APawn* ActionPawn,bool Cancelled)
{
    if(!HasAuthority()||!Serial||Serial!=KukriAttack.Serial||ActionPawn!=KukriAttack.Pawn.Get())return;
    if(Cancelled){KukriNextStage=0;KukriChainUntil=0.;}
    ClearKukriAttack(); // Payment remains committed, including misses and cancelled attacks.
}

void AColdSteelPlayerState::TickKukriAuthority(float Delta)
{
    if(!HasAuthority())return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* HP=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const double Now=GetWorld()->GetTimeSeconds();
    if(KukriAttack.Serial&&(!MatchesKukriEquipment()||!HP||HP->IsDead()||Now>KukriAttack.Until||
        Pawn->IsTraversing()||Pawn->IsDodging()||Pawn->IsCastBlockingLeftHandAction()||
        UBoundCongregateCaptureComponent::IsCaptured(Pawn)||(Status&&Status->BlocksMovement())))
    {ClearKukriAttack();KukriChainUntil=0.;KukriNextStage=0;}
    const auto* Main=ShadowModel&&!ShadowModel->ActiveProductionTool()?ShadowModel->Equipped():nullptr;
    const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,ShadowModel);
    const FString Key=Main?Main->InstanceId+TEXT("|")+(Off?Off->InstanceId:FString()):FString();
    const auto* Move=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    const bool Eligible=Move&&HP&&!HP->IsDead()&&Main&&Main->Definition==TEXT("ue_kukri")&&
        !KukriAttack.Serial&&!IsSwordWhirlwindExecuting(Pawn)&&!UppercutActiveSequence&&!IsQuickCombatExecuting(Pawn)&&
        !Pawn->IsTraversing()&&!Pawn->IsDodging()&&!Pawn->IsCastBlockingLeftHandAction()&&
        !UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&!(Status&&Status->BlocksMovement());
    if(KukriSprintPawn.Get()!=Pawn){KukriReadyAt=KukriChainUntil=0.;KukriNextStage=0;KukriChainKey.Reset();}
    if(!Eligible||KukriSprintKey!=Key||KukriSprintPawn.Get()!=Pawn)
    {KukriSprintSeconds=0.f;KukriDashReadyUntil=-1.;KukriSprintKey=Key;KukriSprintPawn=Pawn;if(!Eligible)return;}
    const auto& Def=ShadowModel->MasteryDefinition(TEXT("dashAttack"));
    const int32 Level=FMath::Clamp(ShadowModel->MasteryProgress(Def.Id).Level,1,Def.MaxLevel);
    const float Ready=FMath::Max(.01f,Def.DashAttack.ReadySeconds*(1.f-(Level-1)*Def.DashAttack.ReadyReductionPerLevel));
    const bool Sprint=Move->bWantsToSprint&&Move->IsMovingOnGround()&&!Pawn->IsSliding()&&Pawn->GetVelocity().SizeSquared2D()>2500.f;
    const bool Carry=KukriSprintSeconds>=Ready&&(Pawn->IsSliding()||Move->IsFalling()||!Move->PendingLaunchVelocity.IsZero());
    KukriSprintSeconds=Sprint?FMath::Min(Ready,KukriSprintSeconds+Delta):Carry?Ready:0.f;
    // The release packet may precede the reliable attack. Retain a short earned-ready grace.
    if(KukriSprintSeconds+.08f>=Ready)KukriDashReadyUntil=Now+.25;
}

bool AColdSteelPlayerState::ValidateKukriHit(const FColdSteelNetHitReport& R,const AFPSGAMECharacter* Pawn,FString& Reason) const
{
    const auto& A=KukriAttack;const int32 Hand=R.ItemInstance==A.Main?0:1;
    const auto* HP=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const double Now=GetWorld()->GetTimeSeconds();
    const double ContactAt=R.ClientFireTime>0.?R.ClientFireTime:Now;
    const double Age=ContactAt-A.Started;
    if(!A.Serial||R.KukriAttackSerial!=A.Serial||R.MasteryAttackSerial!=A.MasterySerial||A.Pawn.Get()!=Pawn||!MatchesKukriEquipment()||
        !HP||HP->IsDead()||Pawn->IsTraversing()||Pawn->IsDodging()||Pawn->IsCastBlockingLeftHandAction()||
        UBoundCongregateCaptureComponent::IsCaptured(Pawn)||(Status&&Status->BlocksMovement())||
        R.AttackMeta!=(A.Dash?0x16:0)||!(R.Flags&(1<<3))||(R.Flags&(1<<4))||
        (Hand==1&&(A.Offhand.IsEmpty()||R.ItemInstance!=A.Offhand||A.Dash))||
        !FMath::IsFinite(R.ClientFireTime)||R.ClientFireTime<0.||ContactAt>Now+.1||Now-ContactAt>.9||
        Age+.10<A.ContactStart[Hand]||Age>A.ContactEnd[Hand]+.5||Now>A.Until||
        !R.Target||A.Targets[Hand].Contains(R.Target.Get()))
    {Reason=TEXT("kukri attack not committed, out of contact window or duplicate blade target");return false;}
    return true;
}

bool AColdSteelPlayerState::IsKukriMovementPending(uint32 Serial) const
{return Serial&&static_cast<int32>(Serial-KukriReceivedSequence)>0;}

bool AColdSteelPlayerState::GetKukriMovement(uint32 Serial,uint8 Kind,FVector& Direction,float& Limit,float& Recovery) const
{
    const auto& A=KukriAttack;
    if(!Serial||Serial!=A.Serial||!MatchesKukriEquipment()||GetWorld()->GetTimeSeconds()>A.Until)return false;
    const auto Move=EFPSMeleeMove(Kind);const float Age=float(GetWorld()->GetTimeSeconds()-A.Started);
    Direction=A.Direction;Recovery=FMath::Max(0.f,float(KukriReadyAt-GetWorld()->GetTimeSeconds()));
    if(A.Dash){Limit=0.f;return Move==EFPSMeleeMove::AirMomentum&&Age<=A.ContactEnd[0]+.15f;}
    if(Move!=EFPSMeleeMove::Thrust||A.Stage!=2||A.Offhand.IsEmpty())return false;
    const float End=KukriRhythm::DualThrustLungeEnd/A.ThrustRate;
    Limit=KukriRhythm::DualThrustLungeCM*FMath::SmoothStep(KukriRhythm::DualThrustLungeStart/A.ThrustRate,End,Age+.08f);
    return Age<=End+.3f;
}

void AColdSteelPlayerState::ClientKukriAttackResult_Implementation(uint32 Serial,APawn* ActionPawn,bool Accepted,double TotalSpent)
{
    if(HasAuthority()||!Serial||static_cast<int32>(Serial-KukriReceiptSequence)<=0)return;
    KukriReceiptSequence=Serial;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model)return;
    // Resource receipts survive cancel, weapon switch and respawn. Animation rejection does not.
    if(Accepted&&TotalSpent>Model->Current.UppercutStaminaSpent)
    {
        UppercutStaminaReceipt::Merge(Model->Current,TotalSpent);Model->DelayStaminaRecovery();
        if(auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn()))
            if(auto* Exhaustion=Pawn->FindComponentByClass<UFPSExhaustionComponent>())Exhaustion->ObserveStamina(Model->Current.Stamina);
        Model->OnStaminaChanged.Broadcast();
    }
    if(!Accepted&&GetPawn()==ActionPawn)
        if(auto* Kukri=ActionPawn?ActionPawn->FindComponentByClass<UKukriWeaponComponent>():nullptr)Kukri->RejectNetworkAttack(Serial);
}

void AColdSteelPlayerState::ConfirmKukriHit(const FColdSteelNetHitReport& R,AFPSGAMECharacter* Pawn,float Applied,bool Killed,bool TrainingEligible)
{
    if(!R.KukriAttackSerial||R.KukriAttackSerial!=KukriAttack.Serial||!KukriAttack.Dash||(Applied<=0.f&&!Killed))return;
    // Eligibility was sampled before ApplyHit, while a target killed by this hit was alive.
    if(TrainingEligible)
    {++KukriAttack.Hits;if(Killed)++KukriAttack.Kills;}
    if(auto* Combat=R.Target?R.Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;Combat&&!Combat->IsDead())
        Combat->ReceiveMeleeKnockback(Pawn,KukriAttack.DashKnockback);
}
