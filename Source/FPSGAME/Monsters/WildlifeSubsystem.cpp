#include "WildlifeSubsystem.h"
#include "WildlifeAnimal.h"
#include "HillsWildlifeAudio.h"
#include "QuadrupedAnimationTemplate.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "WildlifeDistanceActivity.h"
#include "FPSCombatHealthComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../FPSWeatherManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "UObject/Package.h"

bool UWildlifeSubsystem::IsWildlifeMap(const UWorld* World)
{
    if (!World) return false;
    const FString PackageName = World->GetPackage()->GetName();
    const FString MapName = World->WorldType == EWorldType::PIE ? UWorld::RemovePIEPrefix(PackageName) : PackageName;
    return MapName == TEXT("/Game/GameMaps/L_TemperateHills_Initial");
}

bool UWildlifeSubsystem::IsCatalogClass(const FSoftObjectPath& ClassPath)
{
    return WildlifeCatalog::Get().Species.ContainsByPredicate([&ClassPath](const FWildlifeSpecies& Species)
    {
        return FSoftObjectPath(Species.CharacterClass) == ClassPath;
    });
}

bool UWildlifeSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    return Super::ShouldCreateSubsystem(Outer) && IsWildlifeMap(Cast<UWorld>(Outer));
}

bool UWildlifeSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UWildlifeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    for(const auto& Row:WildlifeCatalog::Get().Species)
        if(Row.SpawnWeight>0&&!Row.CharacterClass.IsEmpty())
        {
            // The native audio component's soft paths are not class dependencies.
            // Request the same ambient manifest on receiving clients as well.
            if(GetWorld()->GetNetMode()!=NM_DedicatedServer)
                AmbientAudioLoads.Add(Row.Id,UAssetManager::GetStreamableManager().RequestAsyncLoad(UHillsWildlifeAudio::AssetPaths(Row.Id)));
            if(GetWorld()->GetNetMode()!=NM_Client)PrepareAmbientClass(Row);
        }
    FWorldDelegates::OnWorldBeginTearDown.AddUObject(this, &UWildlifeSubsystem::OnWorldBeginTearDown);
}

void UWildlifeSubsystem::OnWorldBeginTearDown(UWorld* World)
{
    // Covers deaths in the last frame after travel was accepted. Dependencies
    // are still alive here; Deinitialize is too late to commit inventory.
    if (World == GetWorld() && !FlushLoot())
        UE_LOG(LogTemp, Error, TEXT("Wildlife loot could not be saved before world teardown (%d pending)"), PendingLoot.Num());
}

void UWildlifeSubsystem::Deinitialize()
{
    AmbientClassLoads.Reset();
    AmbientAudioLoads.Reset();
    FWorldDelegates::OnWorldBeginTearDown.RemoveAll(this);
    Spawned.Reset();
    ActivityMembers.Reset();
    PendingLoot.Reset();
    HillsGroups.Reset();
    Hills.Reset();
    Super::Deinitialize();
}

bool UWildlifeSubsystem::PrepareAmbientClass(const FWildlifeSpecies& Row)
{
    const FSoftObjectPath Path(Row.CharacterClass);
    auto& Request=AmbientClassLoads.FindOrAdd(Path);
    if(!Request)Request=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path);
    if(!Request||!Request->HasLoadCompleted())return false;
    if(const auto* Audio=AmbientAudioLoads.Find(Row.Id);Audio&&*Audio&&!(*Audio)->HasLoadCompleted())return false;
    auto* Class=Cast<UClass>(Path.ResolveObject());
    if(!Class||!Class->IsChildOf(ACharacter::StaticClass()))
    {
        if(!bLoggedMissingClass)
        {
            bLoggedMissingClass=true;
            UE_LOG(LogTemp,Error,TEXT("WILDLIFE_CLASS_MISSING species=%s path=%s"),*Row.Id,*Row.CharacterClass);
        }
        return false;
    }
#if WITH_EDITOR
    // A completed package can still have a skeletal compiler worker running.
    // Registering the character in this state synchronously joins that worker.
    const ACharacter* Defaults=Class->GetDefaultObject<ACharacter>();
    const USkeletalMesh* Skin=Defaults->GetMesh()->GetSkeletalMeshAsset();
    if(Skin&&Skin->IsCompiling())return false;
    const auto* Animal=Cast<AColdSteelAnimal>(Defaults);
    if(Animal&&Animal->AnimationSet&&Animal->AnimationSet->ReferenceMesh&&Animal->AnimationSet->ReferenceMesh->IsCompiling())return false;
#endif
    return true;
}

TStatId UWildlifeSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UWildlifeSubsystem, STATGROUP_Tickables);
}

bool UWildlifeSubsystem::IsDay() const
{
    const UWorld* World = GetWorld();
    if (!World) return true;
    const FWildlifeSpawnSettings& S = WildlifeCatalog::Get().Spawn;
    const bool bCached = CachedDayValue >= S.DayStart && CachedDayValue < S.DayEnd;
    const double Now = World->GetTimeSeconds();
    if (Now - CachedDaySampleTime < .5) return bCached;
    CachedDaySampleTime = Now;
    for (TActorIterator<AFPSWeatherManager> It(World); It; ++It)
    {
        CachedDayValue = It->NormalizedDayTime;
        return CachedDayValue >= S.DayStart && CachedDayValue < S.DayEnd;
    }
    CachedDayValue = .5f;
    return true;
}

int32 UWildlifeSubsystem::GetLiveCount() const
{
    int32 Count = 0;
    for (const TWeakObjectPtr<AActor>& Actor : Spawned)
        if (Actor.IsValid()) ++Count;
    return Count;
}

bool UWildlifeSubsystem::FindSpawnPoint(const FVector& Center, const FWildlifeSpecies& Species, FVector& OutLocation)
{
    const FWildlifeSpawnSettings& S = WildlifeCatalog::Get().Spawn;
    UWorld* World = GetWorld();
    if (!World) return false;
    for (int32 Attempt = 0; Attempt < 8; ++Attempt)
    {
        const float Angle = FMath::FRandRange(0.f, 2.f * PI);
        const float Distance = FMath::FRandRange(S.SpawnMinDistance, S.SpawnMaxDistance);
        const FVector Probe = Center + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * Distance;
        if (!ResolveSpawnCenter(Species, Probe, OutLocation)) continue;
        // Keep the herd clear of every player, not just the sampled one.
        bool bTooClose = false;
        for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
        {
            const APlayerController* PC = It->Get();
            const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
            if (Pawn && FVector::Dist2D(Pawn->GetActorLocation(), OutLocation) < S.MinPlayerDistance)
            {
                bTooClose = true;
                break;
            }
        }
        if (bTooClose) continue;
        return true;
    }
    return false;
}

AActor* UWildlifeSubsystem::SpawnOne(const FWildlifeSpecies& Row, const FVector& Location, const FRotator& Facing,
    ESpawnActorCollisionHandlingMethod CollisionHandling)
{
    UWorld* World = GetWorld();
    if (!IsWildlifeMap(World) || World->GetNetMode() == NM_Client || Row.CharacterClass.IsEmpty()) return nullptr;
    UClass* Class = Cast<UClass>(FSoftObjectPath(Row.CharacterClass).ResolveObject());
    // Explicit developer spawns still work immediately for uncached species.
    if(!Class)Class=LoadObject<UClass>(nullptr,*Row.CharacterClass);
    if (!Class || !Class->IsChildOf(ACharacter::StaticClass()))
    {
        if (!bLoggedMissingClass)
        {
            bLoggedMissingClass = true;
            UE_LOG(LogTemp, Error, TEXT("WILDLIFE_CLASS_MISSING species=%s path=%s"), *Row.Id, *Row.CharacterClass);
        }
        return nullptr;
    }
    const FTransform Transform(Facing, Location);
    AActor* Actor = nullptr;
    if (Class->IsChildOf(AColdSteelAnimal::StaticClass()))
    {
        // Species must be applied before BeginPlay so the capsule and mesh exist on spawn.
        AColdSteelAnimal* Animal = World->SpawnActorDeferred<AColdSteelAnimal>(Class, Transform, nullptr, nullptr,
            CollisionHandling);
        if (!Animal) return nullptr;
        Animal->ApplySpecies(Row.Id);
        Animal->FinishSpawning(Transform);
        Actor = Animal;
    }
    else
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = CollisionHandling;
        Actor = World->SpawnActor<AActor>(Class, Transform, Params);
    }
    if (!IsValid(Actor) || Actor->IsActorBeingDestroyed()) return nullptr;
    // Collision adjustment can move a valid candidate across the village boundary.
    if (!AllowsSpawnAt(Actor->GetActorLocation(), Actor->GetSimpleCollisionRadius()))
    {
        Actor->Destroy();
        return nullptr;
    }
    Actor->Tags.AddUnique(TEXT("WildlifeSpawned"));
    Spawned.Add(Actor);
    return Actor;
}

void UWildlifeSubsystem::RegisterActivity(UWildlifeDistanceActivity* Activity)
{
    ActivityMembers.AddUnique(Activity);
}

void UWildlifeSubsystem::UnregisterActivity(UWildlifeDistanceActivity* Activity)
{
    ActivityMembers.RemoveSingleSwap(Activity);
}

void UWildlifeSubsystem::UpdateActivity(TConstArrayView<FVector> Players)
{
    const double ActiveRadiusSq = FMath::Square(WildlifeCatalog::Get().Spawn.ActivityRadius);
    for (int32 Index = ActivityMembers.Num()-1; Index >= 0; --Index)
    {
        auto* Member = ActivityMembers[Index].Get();
        if (!Member) { ActivityMembers.RemoveAtSwap(Index); continue; }
        const FVector Here = Member->GetOwner()->GetActorLocation();
        const bool bNearPlayer = Players.ContainsByPredicate([&](const FVector& Player)
        {
            return FVector::DistSquared2D(Here, Player) <= ActiveRadiusSq;
        });
        Member->SetDistancePaused(!bNearPlayer);
    }
}

void UWildlifeSubsystem::PruneAndDespawn(TConstArrayView<FVector> Players)
{
    const double DespawnDistanceSq = FMath::Square(WildlifeCatalog::Get().Spawn.DespawnDistance);
    for (int32 Index = Spawned.Num() - 1; Index >= 0; --Index)
    {
        AActor* Actor = Spawned[Index].Get();
        if (!Actor || Actor->IsActorBeingDestroyed()) { Spawned.RemoveAtSwap(Index); continue; }
        if (Players.IsEmpty()) continue;
        const FVector Here = Actor->GetActorLocation();
        if (!Players.ContainsByPredicate([&](const FVector& Player) { return FVector::DistSquared2D(Player, Here) <= DespawnDistanceSq; }))
        {
            Actor->Destroy();
            Spawned.RemoveAtSwap(Index);
        }
    }
}

int32 UWildlifeSubsystem::SpawnHerd(const FString& SpeciesId, const FVector& Near, int32 Count)
{
    const FWildlifeSpecies* Row = WildlifeCatalog::Get().Find(SpeciesId);
    if (!Row || !IsWildlifeMap(GetWorld()) || GetWorld()->GetNetMode() == NM_Client) return 0;
    int32 Created = 0;
    TArray<AColdSteelAnimal*> Members;
    const int32 Wanted = FMath::Clamp(Count, 1, 8);
    for (int32 Index = 0; Index < Wanted * 4 && Created < Wanted; ++Index)
    {
        const float Angle = FMath::FRandRange(0.f, 2.f * PI);
        const float Distance = FMath::FRandRange(250.f, 900.f);
        const FVector Probe = Near + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * Distance;
        FVector SpawnCenter;
        if (!ResolveSpawnCenter(*Row, Probe, SpawnCenter)) continue;
        const FRotator Facing(0.f, FMath::FRandRange(0.f, 360.f), 0.f);
        if (AActor* Spawn = SpawnOne(*Row, SpawnCenter, Facing))
        {
            ++Created;
            if (auto* Animal = Cast<AColdSteelAnimal>(Spawn)) Members.Add(Animal);
        }
    }
    RegisterHillsGroup(Members);
    return Created;
}

void UWildlifeSubsystem::Tick(float DeltaTime)
{
    const UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Client) return;
    if (!PendingLoot.IsEmpty() && World->GetTimeSeconds() >= NextLootAttempt) FlushLoot();
    const FWildlifeCatalog& Catalog = WildlifeCatalog::Get();
    const FWildlifeSpawnSettings& S = Catalog.Spawn;
    GroupAccumulator += DeltaTime;
    DespawnAccumulator += DeltaTime;
    SpawnAccumulator += DeltaTime;
    const bool bUpdateActivity = GroupAccumulator >= .25f;
    if (!bUpdateActivity && DespawnAccumulator < 5.f && SpawnAccumulator < S.IntervalSeconds) return;

    TArray<FVector, TInlineAllocator<4>> Players, LivingPlayers;
    for (auto It = World->GetPlayerControllerIterator(); It; ++It)
    {
        const auto* PC = It->Get();
        const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
        if (!Pawn) continue;
        const FVector Here = Pawn->GetActorLocation();
        Players.Add(Here);
        if (bUpdateActivity && !HillsGroups.IsEmpty())
        {
            const auto* Vitals = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
            if (!Vitals || !Vitals->IsDead()) LivingPlayers.Add(Here);
        }
    }
    if (DespawnAccumulator >= 5.f) { DespawnAccumulator = 0.f; PruneAndDespawn(Players); }
    if (bUpdateActivity)
    {
        GroupAccumulator = 0.f;
        UpdateActivity(Players);
        TickHillsGroups(LivingPlayers);
    }
    if (SpawnAccumulator < S.IntervalSeconds) return;
    SpawnAccumulator = 0.f;

    // Only the temperate hills own an ambient population. Gate all species before selecting or spawning a herd.
    const ATemperateHillsWorld* Terrain = FindHills();
    // Collision is ready before vegetation packages and entry materials. Loading
    // animal Blueprint classes here synchronously pulls their meshes/animations
    // into the same queue while the player is still waiting behind the overlay.
    if (!Terrain || !Terrain->bReady) return;
    if (const auto* GameInstance = World->GetGameInstance())
        if (const auto* Loading = GameInstance->GetSubsystem<UTransitLoadingSubsystem>(); Loading && Loading->IsHoldingGameplayInput()) return;

    if (Players.IsEmpty()) return;
    if (GetLiveCount() >= S.MaxGlobal) return;

    int32 InRange = 0;
    for (const TWeakObjectPtr<AActor>& Weak : Spawned)
    {
        const AActor* Actor = Weak.Get();
        if (!Actor) continue;
        for (const FVector& Player : Players)
            if (FVector::Dist2D(Player, Actor->GetActorLocation()) <= S.PopulationRadius) { ++InRange; break; }
    }
    if (InRange >= S.TargetPopulation) return;

    const TArray<const FWildlifeSpecies*> Candidates = Catalog.ForActivity(IsDay());
    if (Candidates.IsEmpty()) return;
    int32 TotalWeight = 0;
    for (const FWildlifeSpecies* Row : Candidates) TotalWeight += FMath::Max(0, Row->SpawnWeight);
    if (TotalWeight <= 0) return;
    int32 Roll = FMath::RandRange(1, TotalWeight);
    const FWildlifeSpecies* Chosen = Candidates.Last();
    for (const FWildlifeSpecies* Row : Candidates)
    {
        Roll -= FMath::Max(0, Row->SpawnWeight);
        if (Roll <= 0) { Chosen = Row; break; }
    }

    if(!PrepareAmbientClass(*Chosen))return;
    const FVector Center = Players[FMath::RandRange(0, Players.Num() - 1)];
    const int32 Herd = FMath::Min(FMath::RandRange(Chosen->HerdMin, Chosen->HerdMax), S.MaxGlobal - GetLiveCount());
    if (Chosen->Id == TEXT("boar"))
    {
        SpawnRiverbankBoars(*Terrain, *Chosen, Players, Center, Herd);
        return;
    }
    FVector Feet;
    if (!FindSpawnPoint(Center, *Chosen, Feet)) return;
    const FRotator Facing(0.f, FMath::FRandRange(0.f, 360.f), 0.f);
    TArray<AColdSteelAnimal*> Members;
    if (auto* Animal = Cast<AColdSteelAnimal>(SpawnOne(*Chosen, Feet, Facing))) Members.Add(Animal);
    for (int32 Extra = 1; Extra < Herd; ++Extra)
    {
        const FVector Offset = FVector(FMath::FRandRange(-250.f, 250.f), FMath::FRandRange(-250.f, 250.f), 0.f);
        FVector SpawnCenter;
        if (!ResolveSpawnCenter(*Chosen, Feet + Offset, SpawnCenter)) continue;
        AActor* Spawn = SpawnOne(*Chosen, SpawnCenter,
            FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f));
        if (auto* Animal = Cast<AColdSteelAnimal>(Spawn)) Members.Add(Animal);
    }
    RegisterHillsGroup(Members);
}
