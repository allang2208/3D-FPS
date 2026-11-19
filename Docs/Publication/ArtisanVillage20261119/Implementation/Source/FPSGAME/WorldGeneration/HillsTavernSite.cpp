#include "HillsTavernSite.h"

#include "HillsTavernInterior.h"
#include "TemperateHillsStreamingPrivate.h"
#include "AI/NavigationSystemBase.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Level.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/World.h"

void ATemperateHillsWorld::BindStreamedVillageTavern()
{
    ULevelStreamingDynamic* Stream = Streaming ? Streaming->VillageLevel.Get() : nullptr;
    ULevel* Level = Stream ? Stream->GetLoadedLevel() : nullptr;
    if (!Level) return;
    for (AActor* Actor : Level->Actors)
    {
        if (!IsValid(Actor) || !Actor->ActorHasTag(TEXT("VillageTavern.Site"))) continue;
        UHillsTavernSite* Site = Actor->FindComponentByClass<UHillsTavernSite>();
        if (!Site)
        {
            Site = NewObject<UHillsTavernSite>(Actor);
            Actor->AddInstanceComponent(Site);
            Site->RegisterComponent();
        }
        Site->Bind(*this);
        return;
    }
}

void UHillsTavernSite::Bind(ATemperateHillsWorld& WorldOwner)
{
    if (Hills.Get() != &WorldOwner)
    {
        if (Hills.IsValid())
        {
            Hills->OnTavernRepairChanged.RemoveAll(this);
            if (Hills->TavernAreaOccupied.IsBoundToObject(this)) Hills->TavernAreaOccupied.Unbind();
        }
        Hills = &WorldOwner;
        WorldOwner.OnTavernRepairChanged.AddUObject(this,&UHillsTavernSite::Refresh);
        if (WorldOwner.HasAuthority())
            WorldOwner.TavernAreaOccupied.BindUObject(this,&UHillsTavernSite::RepairAreaOccupied);
    }
    Refresh();
}

bool UHillsTavernSite::RepairAreaOccupied() const
{
    // Also cover the roof and eaves that will be replaced. A character standing
    // on the ridge has its capsule bottom slightly above the mesh.
    const AActor* Shell = GetOwner();
    const FTransform& Frame = Shell->GetActorTransform();
    FBox Footprint(FVector(-670.,-450.,-10.),FVector(670.,450.,670.));
    TInlineComponentArray<UStaticMeshComponent*> Parts(Shell);
    for (const UStaticMeshComponent* Part : Parts)
    {
        if (Part->ComponentHasTag(TEXT("VillageTavern.NoCollision"))) continue;
        if (Part->ComponentHasTag(TEXT("VillageTavern.Ruined")) || Part->ComponentHasTag(TEXT("VillageTavern.Repaired")))
            Footprint += Part->CalcBounds(Part->GetComponentTransform().GetRelativeTransform(Frame)).GetBox();
    }
    Footprint.Max.Z += 4.;
    return GetWorld()->OverlapAnyTestByObjectType(Frame.TransformPosition(Footprint.GetCenter()),Frame.GetRotation(),
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Footprint.GetExtent() * Frame.GetScale3D().GetAbs()),
        FCollisionQueryParams(SCENE_QUERY_STAT(VillageTavernRepair),false,Shell));
}

void UHillsTavernSite::Refresh()
{
    if (!Hills.IsValid()) return;
    const bool bRepaired = Hills->IsTavernRepaired();
    if (Furnishings.IsValid() && bShowingRepaired == bRepaired) return;

    AActor* Shell = GetOwner();
    TInlineComponentArray<UStaticMeshComponent*> Parts(Shell);
    for (UStaticMeshComponent* Part : Parts)
    {
        const bool bRuin = Part->ComponentHasTag(TEXT("VillageTavern.Ruined"));
        if (!bRuin && !Part->ComponentHasTag(TEXT("VillageTavern.Repaired"))) continue;
        const bool bPresent = bRuin != bRepaired;
        Part->SetVisibility(bPresent);
        Part->SetHiddenInGame(!bPresent);
        const bool bSolid = bPresent && !Part->ComponentHasTag(TEXT("VillageTavern.NoCollision"));
        const auto Collision = bSolid ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
        if (Part->GetCollisionEnabled() != Collision)
        {
            Part->SetCollisionEnabled(Collision);
            // ISM physics creation/destruction already updates its cached navigation
            // relevance, so the primitive's change notification can skip the octree.
            if (Hills->HasAuthority() && Part->CanEverAffectNavigation())
                FNavigationSystem::UpdateComponentData(*Part);
        }
    }

    if (Furnishings.IsValid()) Furnishings->Destroy();
    FActorSpawnParameters Spawn;
    Spawn.Owner = Shell;
    Spawn.OverrideLevel = Shell->GetLevel();
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AActor* Interior = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),Shell->GetActorTransform(),Spawn);
    if (!Interior) return;
    USceneComponent* RoomRoot = NewObject<USceneComponent>(Interior,TEXT("TavernFloor"));
    RoomRoot->SetMobility(EComponentMobility::Static);
    Interior->SetRootComponent(RoomRoot);
    Interior->AddInstanceComponent(RoomRoot);
    RoomRoot->SetupAttachment(Shell->GetRootComponent());
    RoomRoot->SetRelativeTransform(FTransform::Identity);
    RoomRoot->RegisterComponent();
    Interior->Tags.Add(TEXT("VillageTavern.Interior"));
    Furnishings = Interior;
    bShowingRepaired = bRepaired;
    FHillsTavernInterior::Populate(*Interior,*RoomRoot,bRepaired);
}

void UHillsTavernSite::EndPlay(EEndPlayReason::Type Reason)
{
    if (Hills.IsValid())
    {
        Hills->OnTavernRepairChanged.RemoveAll(this);
        if (Hills->TavernAreaOccupied.IsBoundToObject(this)) Hills->TavernAreaOccupied.Unbind();
    }
    if (Furnishings.IsValid()) Furnishings->Destroy();
    Furnishings.Reset();
    Hills.Reset();
    Super::EndPlay(Reason);
}
