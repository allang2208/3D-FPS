#include "ColdSteelEnchantmentCombat.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"

FColdSteelShotEffects ColdSteelCombat::Snapshot(AActor* Source,const FColdSteelItem* Item)
{
    FColdSteelShotEffects R;auto* Pawn=Cast<AFPSGAMECharacter>(Source);if(!Pawn||!Pawn->GetController()||!Pawn->IsPlayerControlled())return R;
    auto* P=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* E=Pawn->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    if(P&&E)if(const auto* I=Item?Item:P->Equipped()){R.Piercing=FMath::Clamp(int32(E->Effect(*I,TEXT("piercingBonus"))),0,8);R.Poison=E->Effect(*I,TEXT("poisonOnHit"))?FMath::Max(1,int32(E->Effect(*I,TEXT("poisonStacks"),1))):0;}return R;
}
FColdSteelTurboRamp ColdSteelCombat::TurboRamp(const UColdSteelEnhancementSystem* Enhancement,const FColdSteelItem* Item)
{
    FColdSteelTurboRamp R;if(!Enhancement||!Item)return R;
    const double Start=Enhancement->Effect(*Item,TEXT("turboRampStartMul"));
    const double Peak=Enhancement->Effect(*Item,TEXT("turboRampPeakMul"));
    const double Seconds=Enhancement->Effect(*Item,TEXT("turboRampSeconds"));
    // 三个数值同属一次附魔；缺一项就不成立，避免半套数据把射速改成未定义状态。
    if(Start<=0.||Peak<=0.||Seconds<=0.)return R;
    R.Enabled=true;R.StartMultiplier=Start;R.PeakMultiplier=Peak;R.Seconds=Seconds;return R;
}
double ColdSteelCombat::TurboIntervalMultiplier(const FColdSteelTurboRamp& Ramp,double HeldSeconds)
{
    if(!Ramp.Enabled)return 1.;
    const double Progress=FMath::Clamp(HeldSeconds/FMath::Max(.01,Ramp.Seconds),0.,1.);
    return Ramp.StartMultiplier+(Ramp.PeakMultiplier-Ramp.StartMultiplier)*Progress;
}
FColdSteelConvergence ColdSteelCombat::Convergence(const UColdSteelEnhancementSystem* Enhancement,const FColdSteelItem* Item)
{
    FColdSteelConvergence R;if(!Enhancement||!Item)return R;
    const double Scale=Enhancement->Effect(*Item,TEXT("convergenceDamageScale"));
    // 开关与倍率同属一次附魔；缺一项就不成立，避免半套数据把射击模式改成未定义状态。
    if(Enhancement->Effect(*Item,TEXT("convergenceShot"))<=0.||Scale<=0.)return R;
    R.Enabled=true;R.DamageScale=Scale;return R;
}
double ColdSteelCombat::ConvergenceShotScale(const FColdSteelConvergence& Convergence,int32 Rounds)
{
    if(!Convergence.Enabled)return 1.;
    return Convergence.DamageScale*FMath::Max(0,Rounds);
}
void ColdSteelCombat::OnHit(AActor* Target,AActor* Shooter,int32 Poison)
{
    if(!IsValid(Target)||Target==Shooter||Target->ActorHasTag(TEXT("Friendly"))||Target->ActorHasTag(TEXT("Companion"))||!Target->HasAuthority()||!Cast<APawn>(Target)||Poison<=0)return;
    auto* C=Target->FindComponentByClass<UColdSteelPoisonComponent>();if(!C){C=NewObject<UColdSteelPoisonComponent>(Target);Target->AddInstanceComponent(C);C->RegisterComponent();}C->AddStacks(Shooter,Poison);
}
void UColdSteelPoisonComponent::AddStacks(AActor* Source,int32 Amount)
{
    if(!GetOwner()->HasAuthority()||Amount<=0)return;
    if(const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();Status&&Status->IsImmune())return;
    Stacks+=Amount;TicksLeft=5;Shooter=Source;
    if(const auto* P=Cast<APawn>(Source))Instigator=P->GetController();
    if(!GetWorld()->GetTimerManager().IsTimerActive(Timer))GetWorld()->GetTimerManager().SetTimer(Timer,this,&ThisClass::Pulse,1.f,true);
}
void UColdSteelPoisonComponent::Pulse()
{
    if(Stacks<=0||TicksLeft<=0)return;
    // 中毒跳伤不进入硬直闸门（伤害类型不变，避免影响减伤结算）。
    auto Deal=[&](){ return UGameplayStatics::ApplyDamage(GetOwner(),Stacks,Instigator.Get(),Shooter.Get(),UCombatDirectDamage::StaticClass()); };
    if(auto* Combat=GetOwner()->FindComponentByClass<UMonsterCombatComponent>())Combat->ApplyHitWithReactionScale(0.f,Deal);else Deal();
    if(--TicksLeft<=0){--Stacks;TicksLeft=5;if(Stacks<=0)GetWorld()->GetTimerManager().ClearTimer(Timer);}
}
void UColdSteelPoisonComponent::EndPlay(const EEndPlayReason::Type R){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::EndPlay(R);}
