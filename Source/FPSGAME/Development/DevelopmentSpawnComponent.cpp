#include "DevelopmentSpawnComponent.h"
#include "../Monsters/FatZombiePusPool.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "NavigationData.h"
#include "NavigationSystem.h"

UDevelopmentSpawnComponent::UDevelopmentSpawnComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    auto Add = [this](const TCHAR* Id, const TCHAR* Name, const TCHAR* Path, float Radius)
    {
        auto& Entry = Monsters.AddDefaulted_GetRef();
        Entry.Id = Id; Entry.Name = FText::FromString(Name);
        Entry.CharacterClass = TSoftClassPtr<ACharacter>(FSoftObjectPath(Path));
        Entry.FootprintRadius = Radius;
    };
    Add(TEXT("FatZombie"), TEXT("胖子僵尸"), TEXT("/Script/FPSGAME.FatZombie"), 60.f);
    Add(TEXT("Mutant3"), TEXT("突变体-3"), TEXT("/Script/FPSGAME.Mutant3"), 50.f);
    Add(TEXT("NurseZombie"), TEXT("护士僵尸"), TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"), 44.f);
    Add(TEXT("WitchRebuilt"), TEXT("巫婆·重建候选"), TEXT("/Script/FPSGAME.WitchRebuiltMonster"), 65.f);
    Add(TEXT("HandBrain"), TEXT("手脑"), TEXT("/Game/Monsters/HandBrain/BP_HandBrain.BP_HandBrain_C"), 125.f);
    Add(TEXT("PoisonMaggot"), TEXT("毒蛆"), TEXT("/Game/Monsters/PoisonMaggot/BP_PoisonMaggot.BP_PoisonMaggot_C"), 120.f);
    Add(TEXT("Wolf"), TEXT("野狼"), TEXT("/Game/Monsters/Wolf/BP_WolfMonster.BP_WolfMonster_C"), 100.f);
    Add(TEXT("ZombieDog"), TEXT("僵尸犬"), TEXT("/Game/Monsters/ZombieDog/V1/BP_ZombieDog.BP_ZombieDog_C"), 100.f);
    Add(TEXT("InfectedDog"), TEXT("感染犬"), TEXT("/Game/Monsters/InfectedDog/BP_InfectedDog.BP_InfectedDog_C"), 100.f);
}

bool UDevelopmentSpawnComponent::FindLocation(APlayerController* Player, const ACharacter* Defaults,
    float Distance, float Footprint, int32 Attempt, const UNavigationSystemV1* Navigation,
    const ANavigationData* NavData, FVector& Location, FRotator& Facing) const
{
    APawn* Pawn = Player->GetPawn();
    const UCapsuleComponent* Capsule = Defaults->GetCapsuleComponent();
    const float Radius = Capsule->GetScaledCapsuleRadius();
    const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    FVector View; FRotator Look;
    Player->GetPlayerViewPoint(View, Look);
    const FVector Forward = FRotator(0, Look.Yaw, 0).Vector();
    const FVector Right(-Forward.Y, Forward.X, 0);
    // Centre first, then adjacent positions in rows that remain in front of the player.
    const int32 Column = Attempt % 5;
    const int32 Side = Column == 0 ? 0 : (Column % 2 ? (Column + 1) / 2 : -Column / 2);
    const float Spacing = 2.f * FMath::Max(Radius, Footprint) + 30.f;
    FVector Near = Pawn->GetActorLocation() + Forward * (Distance + (Attempt / 5) * Spacing * .5f)
        + Right * Side * Spacing;
    const float FloorZ = Pawn->GetActorLocation().Z - Pawn->GetSimpleCollisionHalfHeight();
    Near.Z = FloorZ;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DeveloperSpawnPlacement), false, Pawn);
    FHitResult Ground;
    if (!GetWorld()->LineTraceSingleByChannel(Ground, Near + FVector(0,0,200), Near - FVector(0,0,350), ECC_Pawn, Query)) return false;
    if (Ground.GetActor() && Ground.GetActor()->IsA<APawn>()) return false;
    const float MinSlope = FMath::Max(.72f, Defaults->GetCharacterMovement()->GetWalkableFloorZ());
    if (Ground.ImpactNormal.Z < MinSlope || FMath::Abs(Ground.ImpactPoint.Z - FloorZ) > 180.f) return false;
    // A physically empty floor is not necessarily covered by this body's navmesh.
    // Keep placement on the selected spot; do not warp to a distant nav polygon.
    FNavLocation Navigable;
    if (!Navigation->ProjectPointToNavigation(Ground.ImpactPoint, Navigable, FVector(10,10,80), NavData)
        || FVector::DistSquared2D(Navigable.Location, Ground.ImpactPoint) > FMath::Square(10.f)) return false;
    Location = Ground.ImpactPoint + FVector(0,0,HalfHeight + 3.f);
    if (GetWorld()->OverlapBlockingTestByChannel(Location, FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeCapsule(Radius + 2.f, HalfHeight), Query)) return false;
    for (const FVector Offset : { Forward * Footprint, -Forward * Footprint, Right * Footprint, -Right * Footprint })
    {
        FHitResult Edge;
        const FVector Probe = Ground.ImpactPoint + Offset;
        if (!GetWorld()->LineTraceSingleByChannel(Edge, Probe + FVector(0,0,60), Probe - FVector(0,0,80), ECC_Pawn, Query)
            || Edge.ImpactNormal.Z < MinSlope || FMath::Abs(Edge.ImpactPoint.Z - Ground.ImpactPoint.Z) > 35.f
            || (Edge.GetActor() && Edge.GetActor()->IsA<APawn>())) return false;
    }
    FHitResult Obstacle;
    if (GetWorld()->LineTraceSingleByChannel(Obstacle, View, Location, ECC_Visibility, Query)) return false;
    Facing = FRotator(0, (Pawn->GetActorLocation() - Location).Rotation().Yaw, 0);
    return true;
}

int32 UDevelopmentSpawnComponent::SpawnInFront(FName Id, int32 Count, float DistanceMeters, FText& Result)
{
    auto* Player = Cast<APlayerController>(GetOwner());
    if (!Player || !Player->GetPawn()) { Result = FText::FromString(TEXT("当前没有可用的玩家角色")); return 0; }
    if (!Player->HasAuthority()) { Result = FText::FromString(TEXT("当前连接没有怪物生成权限")); return 0; }
    const auto* Entry = Monsters.FindByPredicate([Id](const auto& Item) { return Item.Id == Id; });
    if (!Entry) { Result = FText::FromString(TEXT("请先选择怪物")); return 0; }
    UClass* Class = Entry->CharacterClass.LoadSynchronous();
    if (!Class || Class->HasAnyClassFlags(CLASS_Abstract)) { Result = FText::FromString(TEXT("该怪物的角色资源尚未准备好")); return 0; }
    const auto* Defaults = Class->GetDefaultObject<ACharacter>();
    const auto* Capsule = Defaults->GetCapsuleComponent();
    const auto* Movement = Defaults->GetCharacterMovement();
    FNavAgentProperties Agent = Movement->GetNavAgentPropertiesRef();
    // Match the runtime movement component's policy. Some monsters deliberately
    // reserve extra clearance; the unregistered CDO must retain that profile.
    const bool bFromCapsule = Movement->ShouldUpdateNavAgentWithOwnersCollision();
    Agent.AgentRadius = bFromCapsule ? Capsule->GetScaledCapsuleRadius()
        : FMath::Max(Agent.AgentRadius, Capsule->GetScaledCapsuleRadius());
    Agent.AgentHeight = bFromCapsule ? Capsule->GetScaledCapsuleHalfHeight() * 2.f
        : FMath::Max(Agent.AgentHeight, Capsule->GetScaledCapsuleHalfHeight() * 2.f);
    const auto* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const ANavigationData* NavData = Navigation ? Navigation->GetNavDataForProps(Agent) : nullptr;
    if (!NavData || NavData->GetConfig().AgentRadius + KINDA_SMALL_NUMBER < Agent.AgentRadius
        || NavData->GetConfig().AgentHeight + KINDA_SMALL_NUMBER < Agent.AgentHeight)
    {
        Result = FText::FromString(TEXT("当前场景缺少适合该怪物体型的导航网格，请先生成场景导航"));
        return 0;
    }
    Count = FMath::Clamp(Count, 1, 10);
    const float Distance = FMath::Clamp(DistanceMeters, 3.f, 15.f) * 100.f;
    int32 Created = 0;
    Spawned.RemoveAll([](const auto& Item) { return !Item.IsValid(); });
    for (int32 Attempt = 0; Attempt < 25 && Created < Count; ++Attempt)
    {
        FVector At; FRotator Rotation;
        if (!FindLocation(Player, Defaults, Distance, Entry->FootprintRadius, Attempt, Navigation, NavData, At, Rotation)) continue;
        FActorSpawnParameters Params;
        Params.Owner = Player;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
        if (auto* Monster = GetWorld()->SpawnActor<ACharacter>(Class, At, Rotation, Params))
        {
            Monster->Tags.AddUnique(TEXT("DevelopmentSpawned"));
            Spawned.Add(Monster); ++Created;
        }
    }
    Result = FText::FromString(Created == 0
        ? TEXT("玩家前方没有同时满足落脚和导航覆盖的位置，请面向可行走区域后重试")
        : FString::Printf(TEXT("已生成 %d / %d 只%s%s"), Created, Count, *Entry->Name.ToString(),
            Created < Count ? TEXT("，其余位置被地形或其他物体占用") : TEXT("，面向玩家")));
    return Created;
}

int32 UDevelopmentSpawnComponent::GetSpawnedCount() const
{
    int32 Count = 0;
    for (const auto& Actor : Spawned) if (Actor.IsValid()) ++Count;
    return Count;
}

int32 UDevelopmentSpawnComponent::ClearSpawned()
{
    int32 Count = 0;
    for (const auto& Actor : Spawned) if (Actor.IsValid() && Actor->Destroy()) ++Count;
    for (TActorIterator<AFatZombiePusPool> It(GetWorld()); It; ++It)
        if (It->GetOwner() == GetOwner() && It->ActorHasTag(TEXT("DevelopmentSpawned"))) It->Destroy();
    Spawned.Reset();
    return Count;
}

void UDevelopmentSpawnComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Spawned.Reset();
    Super::EndPlay(Reason);
}
