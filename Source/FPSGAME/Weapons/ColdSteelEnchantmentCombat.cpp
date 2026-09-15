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

FColdSteelShotEffects ColdSteelCombat::Snapshot(AActor* Source,const FColdSteelItem* Item)
{
    FColdSteelShotEffects R;auto* Pawn=Cast<AFPSGAMECharacter>(Source);if(!Pawn||!Pawn->GetController()||!Pawn->IsPlayerControlled())return R;
    auto* P=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* E=Pawn->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    if(P&&E)if(const auto* I=Item?Item:P->Equipped()){R.Piercing=FMath::Clamp(int32(E->Effect(*I,TEXT("piercingBonus"))),0,8);R.Poison=E->Effect(*I,TEXT("poisonOnHit"))?FMath::Max(1,int32(E->Effect(*I,TEXT("poisonStacks"),1))):0;}return R;
}
void ColdSteelCombat::OnHit(AActor* Target,AActor* Shooter,int32 Poison)
{
    if(!IsValid(Target)||Target==Shooter||!Target->HasAuthority()||!Cast<APawn>(Target)||Poison<=0)return;
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
    UGameplayStatics::ApplyDamage(GetOwner(),Stacks,Instigator.Get(),Shooter.Get(),UCombatDirectDamage::StaticClass());
    if(--TicksLeft<=0){--Stacks;TicksLeft=5;if(Stacks<=0)GetWorld()->GetTimerManager().ClearTimer(Timer);}
}
void UColdSteelPoisonComponent::EndPlay(const EEndPlayReason::Type R){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::EndPlay(R);}
