#include "HolyLightTargets.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"

namespace
{
    bool Vitals(AActor* Target,float*& Health,float& Maximum)
    {
        if(!IsValid(Target)||Target->IsActorBeingDestroyed())return false;
        if(auto* C=Target->FindComponentByClass<UFPSCombatHealthComponent>()){Health=&C->Health;Maximum=C->MaxHealth;return true;}
        if(auto* C=Cast<ANurseZombie>(Target)){Health=&C->Health;Maximum=C->MaxHealth;return true;}
        if(auto* C=Cast<AHandBrainMonster>(Target)){Health=&C->Health;Maximum=C->MaxHealth;return true;}
        if(auto* C=Cast<AWolfMonster>(Target)){Health=&C->Health;Maximum=C->MaxHealth;return true;}
        if(auto* C=Cast<APoisonMaggotMonster>(Target)){Health=&C->Health;Maximum=C->MaxHealth;return true;}
        return false;
    }
}
bool HolyLightTargets::IsFriendly(const AActor* Target)
{
    return IsValid(Target)&&(Target->IsA<AFPSGAMECharacter>()||Target->ActorHasTag(TEXT("Friendly"))||Target->ActorHasTag(TEXT("Player"))||Target->ActorHasTag(TEXT("Companion")));
}
bool HolyLightTargets::IsAlive(AActor* Target)
{
    float* Health=nullptr,Maximum=0;
    if(!Vitals(Target,Health,Maximum)||*Health<=0||Target->ActorHasTag(TEXT("DefenseStructure")))return false;
    const auto* C=Target->FindComponentByClass<UMonsterCombatComponent>();return !C||!C->IsDead();
}
bool HolyLightTargets::IsZombie(const AActor* Target)
{
    // game-dev enemy-config families include these variants in the zombie family.
    return Target&&(Target->ActorHasTag(TEXT("Zombie"))||Target->ActorHasTag(TEXT("NurseZombie"))||Target->ActorHasTag(TEXT("FatZombie"))||Target->ActorHasTag(TEXT("HandBrain"))||Target->ActorHasTag(TEXT("Mutant3"))||Target->ActorHasTag(TEXT("Witch")));
}
float HolyLightTargets::Heal(AActor* Target,float Amount)
{
    if(Amount<=0||!IsAlive(Target))return 0;
    float* Health=nullptr,Maximum=0;if(!Vitals(Target,Health,Maximum))return 0;
    const float Before=*Health;*Health=FMath::Min(Maximum,Before+Amount);return FMath::Max(0.f,*Health-Before);
}
float HolyLightTargets::MaximumHealth(AActor* Target)
{float* Health=nullptr,Maximum=0;return Vitals(Target,Health,Maximum)?Maximum:0;}
