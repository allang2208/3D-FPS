#include "FPSHolyRenewalComponent.h"
#include "HolyLightTargets.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Combat/CombatStatusFormula.h"

UFPSHolyRenewalComponent::UFPSHolyRenewalComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UFPSHolyRenewalComponent::Apply(AActor* Target,int32 Stacks,float Seconds)
{
    if(Stacks<=0||Seconds<=0||!HolyLightTargets::IsAlive(Target))return;
    if(const auto* Status=Target->FindComponentByClass<UCombatStatusFormula>();Status&&Status->IsImmune())return;
    auto* C=Target->FindComponentByClass<UFPSHolyRenewalComponent>();
    if(!C){C=NewObject<UFPSHolyRenewalComponent>(Target);Target->AddInstanceComponent(C);C->RegisterComponent();}
    if(C->Remaining<=0)C->UntilTick=1;
    C->Count+=Stacks;C->Remaining+=Seconds;
    C->SetComponentTickEnabled(true);
    UStatusEffectsComponent::GetOrCreate(Target)->SetTimed(TEXT("holyRenewal"),C->Remaining,C->Count);
}
void UFPSHolyRenewalComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!HolyLightTargets::IsAlive(GetOwner()))Remaining=0;
    UntilTick-=FMath::Min(Delta,Remaining);Remaining=FMath::Max(0.f,Remaining-Delta);
    while(UntilTick<=0){HolyLightTargets::Heal(GetOwner(),FMath::FloorToFloat(HolyLightTargets::MaximumHealth(GetOwner())*.01f*Count));UntilTick+=1;}
    if(Remaining<=0){Count=0;UntilTick=1;SetComponentTickEnabled(false);UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("holyRenewal"));}
}
