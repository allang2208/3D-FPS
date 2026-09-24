#include "InfectedDogMonster.h"
#include "QuadrupedAnimationTemplate.h"
#include "ZombieDogAppearanceComponent.h"
#include "MonsterCombatComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
// The shared combat component is migrating from Poise to Toughness. Keep this
// independently published canine usable with both versions during that change.
template<class T> void SetCanineHitThreshold(T* Component)
{
    if constexpr (requires { Component->ToughnessThreshold; }) Component->ToughnessThreshold=55.f;
    else Component->PoiseThreshold=55.f;
}
}

AInfectedDogMonster::AInfectedDogMonster(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    MonsterDisplayName=FText::FromString(TEXT("感染犬"));
    Level=7; Rank=EMonsterRank::Normal; ExperienceReward=240;
    MaxHealth=190.f; BiteDamage=28.f; PounceDamage=46.f;
    PhysicalDefense=34.f; MagicDefense=13.f; CriticalResistance=18.f;
    ChaseSpeed=400.f; WalkSpeed=100.f;
    bUsePredictiveHunting=true;
    SetCanineHitThreshold(Combat.Get());   // TObjectPtr 不能推模板裸指针参数（C2672）；.Get() 语义不变
    WoundAppearance->bEnabled=false;
    Tags.Add(TEXT("InfectedDog")); Tags.Add(TEXT("Undead"));
    // Same body as Wolf. Reuse the existing Nurse navigation clearance profile,
    // including its headroom; no new nav-agent index or map rebuild is needed.
    auto* Movement=GetCharacterMovement();
    auto& Agent=Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius=34.f; Agent.AgentHeight=184.f; Agent.AgentStepHeight=40.f;
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
}
CoreCombatFormula::Attributes AInfectedDogMonster::BaseAttributes() const
{
    return {Strength,Dexterity,Intelligence,Constitution,Wisdom,Luck};
}
void AInfectedDogMonster::BeginPlay()
{
    const auto Stats=CoreCombatFormula::Enemy(BaseAttributes());
    MaxHealth=Stats.MaxHp; BiteDamage=Stats.Atk; PounceDamage=FMath::RoundToFloat(Stats.Atk*1.65);
    PhysicalDefense=Stats.Def; MagicDefense=Stats.Mdef; CriticalResistance=Stats.CritRes;
    Super::BeginPlay();
}
void AInfectedDogMonster::OnAttackLanded(APawn* Victim)
{
    if (auto* Effect=UProgressiveInfectionComponent::GetOrAdd(Victim)) Effect->Infect(this,Infection);
}
