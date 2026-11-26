#include "WildlifeSubsystem.h"
#include "WildlifeAnimal.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"

void UWildlifeSubsystem::BeginCorpse(ACharacter& Animal, const FWildlifeSpecies& Species)
{
    if (!Animal.HasAuthority()) return;
    Spawned.RemoveAllSwap([&Animal](const auto& Entry) { return Entry.Get() == &Animal; });
    Animal.SetLifeSpan(FMath::Max(1.f, Species.CorpseSeconds));
    Animal.ForceNetUpdate();
}

void UWildlifeSubsystem::DropLoot(const ACharacter& Animal, const FWildlifeSpecies& Species, const FVector& Ground)
{
    if (!Animal.HasAuthority()) return;
    float Angle = FMath::FRandRange(0.f, 360.f);
    const float Radius = FMath::Max(40.f, Animal.GetSimpleCollisionRadius() + 35.f);
    for (const FWildlifeLootRow& Entry : Species.Loot)
    {
        if (FMath::FRand() >= Entry.Chance) continue;
        PendingLoot.Add({Entry.Item, FMath::RandRange(Entry.Min, Entry.Max), Ground, Radius, Angle});
        Angle += 137.5f;
    }
    // Pool deaths in the same frame so a herd needs only one save.
}

bool UWildlifeSubsystem::FlushPendingLoot(UWorld* World)
{
    auto* Wildlife = World ? World->GetSubsystem<UWildlifeSubsystem>() : nullptr;
    return !Wildlife || Wildlife->FlushLoot();
}

bool UWildlifeSubsystem::FlushLoot()
{
    UWorld* World = GetWorld();
    if (PendingLoot.IsEmpty()) return true;
    if (!World || World->GetNetMode() == NM_Client) return false;
    NextLootAttempt = World->GetTimeSeconds() + 1.;
    const auto* Terrain = FindHills();
    auto* Model = World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Terrain || !Terrain->bSurfaceReady || !Terrain->WorldId.IsValid() || !Model) return false;

    const bool bPrivateWorld = World->GetNetMode() == NM_Standalone;
    const FString Map = UGameplayStatics::GetCurrentLevelName(World, true);
    TArray<FColdSteelItem> Drops;
    for (const FWildlifeGroundLoot& Roll : PendingLoot)
    {
        if (!Model->ItemDefinitions().Contains(Roll.Definition))
        {
            UE_LOG(LogTemp, Warning, TEXT("Wildlife loot definition missing: %s"), *Roll.Definition);
            return false;
        }
        int32 Remaining = Roll.Count;
        float Radius = Roll.Radius;
        const FVector Direction = FRotator(0, Roll.Angle, 0).Vector();
        while (Remaining > 0)
        {
            auto Item = Model->CreateItem(Roll.Definition);
            Item.Count = FMath::Min<int64>(Remaining, FMath::Max<int64>(1, Item.StackMax));
            Remaining -= int32(Item.Count);
            const FVector At = Roll.Origin + Direction * Radius;
            FVector Feet(At.X, At.Y, Terrain->Height(At.X, At.Y));
            // Account for a rock, raised floor, or other walkable support near the corpse.
            FHitResult Hit;
            const FVector Top(At.X, At.Y, Roll.Origin.Z + 65.);
            if (World->LineTraceSingleByObjectType(Hit, Top, Feet - FVector(0,0,90),
                FCollisionObjectQueryParams(ECC_WorldStatic)) && Hit.ImpactNormal.Z >= .50f)
                Feet = Hit.ImpactPoint;
            Item.Place = 2;
            Item.Cell = -1;
            Item.Map = Map;
            Item.Position = Feet + FVector(0,0,28);
            Item.WorldRotation = FRotator(0, Roll.Angle + (Radius - Roll.Radius), 0);
            if (bPrivateWorld) Item.HarvestWorldId = Terrain->WorldId;
            Drops.Add(MoveTemp(Item));
            Radius += 26.f;
        }
    }
    if (!Drops.IsEmpty())
    {
        if (bPrivateWorld)
        {
            Model->SyncRuntime();
            auto Profile = Model->Snapshot();
            Profile.Items.Append(Drops);
            if (!Model->CommitState(MoveTemp(Profile))) return false;
        }
        else
        {
            auto* Shared = World->GetSubsystem<UColdSteelSharedInventorySubsystem>();
            if (!Shared || !Shared->AddWorldDrops(Drops)) return false;
        }
    }
    PendingLoot.Reset();
    return true;
}
