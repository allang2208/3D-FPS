#include "RuneOrbBladesComponent.h"
#include "RuneOrbBladeProjectile.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"

void URuneOrbBladesComponent::ServerOrbitIntent_Implementation(uint8 Phase,int32 Slot,FVector_NetQuantize Target)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled())return;
    if(Phase==2){EndOrbit();return;}
    if(!SwordEquipped()||!Health||Health->IsDead()||Pawn->IsTraversing())
    {ClientOrbitRejected(Cooldown,CooldownDuration);return;}
    if(Phase==0)
    {
        if(bActive||Cooldown>0.f){ClientOrbitRejected(Cooldown,CooldownDuration);return;}
        OpenOrbit();if(!bActive)ClientOrbitRejected(Cooldown,CooldownDuration);
    }
    else if(Phase==1)
    {
        const FVector Aim=FVector(Target)-Pawn->GetPawnViewLocation();
        if(!bActive||!Slots.IsValidIndex(Slot)||Slots[Slot].bLaunched||!Slots[Slot].Orb.IsValid()
            ||Target.ContainsNaN()||Aim.IsNearlyZero()||Aim.SizeSquared()>FMath::Square(21000.f)
            ||FVector::DotProduct(Aim.GetSafeNormal(),Pawn->GetBaseAimRotation().Vector())<.5f
            ||GetWorld()->GetTimeSeconds()-LastLaunchTime<BurstInterval*.8f)
        {ClientOrbitRejected(Cooldown,CooldownDuration);return;}
        Slots[Slot].bLaunched=true;Slots[Slot].Orb->Launch(Target);LastLaunchTime=GetWorld()->GetTimeSeconds();
    }
}
void URuneOrbBladesComponent::ClientOrbitRejected_Implementation(float Remaining,float Duration)
{
    EndOrbit();Cooldown=FMath::Max(0.f,Remaining);
    CooldownDuration=Duration;
    if(auto* Model=Profile())Model->PostNotice(TEXT("飞剑未释放"),TEXT("武器状态或冷却尚未同步"));
}
void URuneOrbBladesComponent::ClientBladeKill_Implementation()
{
    if(auto* Model=Profile())Model->ReduceAllAbilityCooldowns(.5f);
}
