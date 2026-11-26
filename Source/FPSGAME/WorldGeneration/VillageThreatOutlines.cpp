#include "VillageThreatOutlines.h"
#include "ForestVillageMap.h"
#include "TemperateHillsWorld.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/WildlifeAnimal.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "../Monsters/WolfMonster.h"
#include "../Skills/IlluminationMarkComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"

bool UVillageThreatOutlines::ShouldCreateSubsystem(UObject* Outer) const
{
    return Super::ShouldCreateSubsystem(Outer)&&(ForestVillageMap::Is(Cast<UWorld>(Outer))||UWildlifeSubsystem::IsWildlifeMap(Cast<UWorld>(Outer)));
}

void UVillageThreatOutlines::RegisterMonster(UMonsterCombatComponent* Combat)
{
    AActor* Actor=Combat->GetOwner();
    if(!Actor->HasAuthority()||Actor->IsA<AColdSteelAnimal>())return;
    // The catalogued hill wolf shares its native class with hostile dungeon variants.
    if(Actor->IsA<AWolfMonster>()&&UWildlifeSubsystem::IsCatalogClass(FSoftObjectPath(Actor->GetClass())))return;
    Monsters.FindOrAdd(Combat);
    if(!GetWorld()->GetTimerManager().IsTimerActive(Timer))
        GetWorld()->GetTimerManager().SetTimer(Timer,this,&UVillageThreatOutlines::Update,.25f,true);
}

void UVillageThreatOutlines::UnregisterMonster(UMonsterCombatComponent* Combat)
{
    bool Marked=false;
    if(Monsters.RemoveAndCopyValue(Combat,Marked)&&Marked)
        UIlluminationMarkComponent::SetVillageThreat(Combat->GetOwner(),false);
    if(Monsters.IsEmpty())GetWorld()->GetTimerManager().ClearTimer(Timer);
}

void UVillageThreatOutlines::Update()
{
    if(!Hills.IsValid())
        for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
    const APlayerController* PC=GetWorld()->GetFirstPlayerController();
    const APawn* Player=PC?PC->GetPawn():nullptr;
    for(auto It=Monsters.CreateIterator();It;++It)
    {
        const UMonsterCombatComponent* Combat=It.Key().Get();
        if(!Combat){It.RemoveCurrent();continue;}
        APawn* Pawn=Cast<APawn>(Combat->GetOwner());
        const bool Mark=Pawn&&Hills.IsValid()&&Hills->GetVillageSite().ContainsVillage(Pawn->GetActorLocation())
            &&!Combat->IsDead()&&!Pawn->IsPlayerControlled()&&!Pawn->ActorHasTag(TEXT("NPC"))
            &&!Pawn->ActorHasTag(TEXT("Wildlife"))&&!Pawn->ActorHasTag(TEXT("WildlifeSpawned"))
            &&!Pawn->ActorHasTag(TEXT("Friendly"))&&!Pawn->ActorHasTag(TEXT("Companion"))
            &&!RangedAttackQuery::IsFriendlyUnit(Player,Pawn);
        if(Mark!=It.Value())
        {
            UIlluminationMarkComponent::SetVillageThreat(Combat->GetOwner(),Mark);
            It.Value()=Mark;
        }
    }
    if(Monsters.IsEmpty())GetWorld()->GetTimerManager().ClearTimer(Timer);
}

void UVillageThreatOutlines::Deinitialize()
{
    GetWorld()->GetTimerManager().ClearTimer(Timer);
    Monsters.Reset();
    Super::Deinitialize();
}
