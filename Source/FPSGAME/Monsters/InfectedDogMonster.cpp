#include "InfectedDogMonster.h"
#include "ZombieDogAppearanceComponent.h"
#include "MonsterCombatComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

AInfectedDogMonster::AInfectedDogMonster(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    MonsterDisplayName=FText::FromString(TEXT("感染犬"));
    Level=7; Rank=EMonsterRank::Normal; ExperienceReward=240;
    MaxHealth=220.f; BiteDamage=28.f; PounceDamage=46.f;
    PhysicalDefense=34.f; MagicDefense=13.f; CriticalResistance=18.f;
    ChaseSpeed=400.f; WalkSpeed=100.f;
    bUsePredictiveHunting=true;
    WoundAppearance->bEnabled=false;
    Tags.Add(TEXT("InfectedDog")); Tags.Add(TEXT("Undead"));
    // Same body as Wolf. Reuse the existing Nurse navigation clearance profile,
    // including its headroom; no new nav-agent index or map rebuild is needed.
    auto* Movement=GetCharacterMovement();
    auto& Agent=Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius=34.f; Agent.AgentHeight=184.f; Agent.AgentStepHeight=40.f;
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
}
void AInfectedDogMonster::OnAttackLanded(APawn* Victim)
{
    if (auto* Effect=UProgressiveInfectionComponent::GetOrAdd(Victim)) Effect->Infect(this,Infection);
}
