#include "FPSQuickCombatComponent.h"
#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

UFPSQuickCombatComponent::UFPSQuickCombatComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    // 姿态层在 FinalizeBoneTransform 里采样本组件的阶段，必须先于网格求值。
    PrimaryComponentTick.TickGroup=ETickingGroup::TG_PrePhysics;
}

void UFPSQuickCombatComponent::BeginPlay()
{
    Super::BeginPlay();
    // 与符文剑配重锤共用同一枚钝器命中音。
    ImpactSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick"));
}

UColdSteelStatusModel* UFPSQuickCombatComponent::Model() const
{ return GetOwner()&&GetOwner()->GetGameInstance()?GetOwner()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr; }

bool UFPSQuickCombatComponent::BeginAction()
{
    auto* Profile=Model();if(!Profile)return false;
    // 排队不扣费：动作实际开始才一次性提交冷却与使用修炼（与剑版同一事务口径）。
    Profile->CommitQuickCombatCast();
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    ++Serial;PhaseAge=0.f;Phase=EQuickCombatBashPhase::Release;
    bContactDone=bKillPending=false;
    return true;
}

void UFPSQuickCombatComponent::Cancel(){if(Phase!=EQuickCombatBashPhase::None)FinishAction();}

float UFPSQuickCombatComponent::PhaseFraction() const
{
    float Span=1.f;
    switch(Phase)
    {
    case EQuickCombatBashPhase::Release:Span=QuickCombatPistolMotion::ReleaseEnd;break;
    case EQuickCombatBashPhase::Cock:Span=QuickCombatPistolMotion::CockEnd-QuickCombatPistolMotion::ReleaseEnd;break;
    case EQuickCombatBashPhase::Smash:Span=QuickCombatPistolMotion::SmashEnd-QuickCombatPistolMotion::CockEnd;break;
    case EQuickCombatBashPhase::Recover:Span=QuickCombatPistolMotion::AttackEnd-QuickCombatPistolMotion::SmashEnd;break;
    default:return 0.f;
    }
    return FMath::Clamp(PhaseAge/FMath::Max(.01f,Span),0.f,1.f);
}

void UFPSQuickCombatComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(Phase==EQuickCombatBashPhase::None)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    // 换枪/双持/死亡立刻收手；冷却与已提交的修炼照常保留。
    const auto* Health=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Player||!Player->IsPistolWeapon()||Player->IsDualWieldingPistols()||(Health&&Health->IsDead())){FinishAction();return;}
    AdvancePhase(Delta);
}

void UFPSQuickCombatComponent::AdvancePhase(float Delta)
{
    PhaseAge+=Delta;
    switch(Phase)
    {
    case EQuickCombatBashPhase::Release:
        if(PhaseAge>=QuickCombatPistolMotion::ReleaseEnd){Phase=EQuickCombatBashPhase::Cock;PhaseAge=0.f;}
        break;
    case EQuickCombatBashPhase::Cock:
        if(PhaseAge>=QuickCombatPistolMotion::CockEnd-QuickCombatPistolMotion::ReleaseEnd){Phase=EQuickCombatBashPhase::Smash;PhaseAge=0.f;}
        break;
    case EQuickCombatBashPhase::Smash:
        if(!bContactDone&&PhaseAge>=QuickCombatPistolMotion::ContactTime-QuickCombatPistolMotion::CockEnd){bContactDone=true;ContactHit();}
        if(PhaseAge>=QuickCombatPistolMotion::SmashEnd-QuickCombatPistolMotion::CockEnd){Phase=EQuickCombatBashPhase::Recover;PhaseAge=0.f;}
        break;
    case EQuickCombatBashPhase::Recover:
        if(PhaseAge>=QuickCombatPistolMotion::AttackEnd-QuickCombatPistolMotion::SmashEnd)FinishAction();
        break;
    default:break;
    }
}

void UFPSQuickCombatComponent::ContactHit()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=Model();
    if(!Player||!Profile||!GetWorld())return;
    const auto Stats=Profile->QuickCombatStats();
    const auto Aim=Player->GetMeleeAimTransform();
    const FVector Start=Aim.GetLocation(),Direction=Aim.GetUnitAxis(EAxis::X),End=Start+Direction*Stats.RangeCM;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(QuickCombatBash),false,Player);
    // 单目标：最近一次阻挡即结算，不像剑刃那样沿路径多次采样。
    const bool bHit=GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeSphere(QuickCombatPistolMotion::QueryRadiusCM),Params);
    AActor* Target=bHit?Hit.GetActor():nullptr;
    auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Combat||Combat->IsDead())return;
    const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    auto Shot=ColdSteelSkills::Snapshot(Player,Profile->Equipped());
    Shot.bRifle=false;Shot.bPistol=true;Shot.WeakpointPercent=0;
    const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,Shot,nullptr);
    const bool bKilled=Combat->IsDead();
    // 击退与眩晕合并进 ReceiveStun 的一次提交（无该组件的怪物与剑版口径一致：不硬控）。
    if(Applied>0.f||bKilled)Combat->ReceiveStun(Player,Stats.StunSeconds,Stats.KnockbackCM);
    if(Eligible&&bKilled)bKillPending=true;
    if((Applied>0.f||bKilled)&&ImpactSound)
        UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,.9f,.9f);
}

void UFPSQuickCombatComponent::FinishAction()
{
    if(auto* Profile=Model())
    {
        // 冷却在动作结束后才起跳（预留-结束起跳合同）；击杀修炼随收势统一提交。
        Profile->FinishQuickCombatCast();
        if(bKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    bKillPending=false;
    Phase=EQuickCombatBashPhase::None;PhaseAge=0.f;
}

void UFPSQuickCombatComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    // 销毁路径同样解除冷却预留并保留已提交的冷却。
    if(Phase!=EQuickCombatBashPhase::None)FinishAction();
    Super::EndPlay(Reason);
}
