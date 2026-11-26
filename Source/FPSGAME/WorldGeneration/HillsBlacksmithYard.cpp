#include "HillsBlacksmith.h"
#include "SmithYardFurnace.h"
#include "TemperateHillsWorld.h"
#include "../Building/VillageFurnaceKeys.h"
#include "../Building/VoxelBuildWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInterface.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "UObject/ConstructorHelpers.h"

ASmithYardFurnace::ASmithYardFurnace()
{
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(TEXT("/Game/Props/BlastFurnace20260923/SM_BlastFurnace"));
    Body()->SetStaticMesh(Mesh.Object);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Brick(TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard/Wear/M_SmithFurnaceBrick"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Stone(TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard/Wear/M_SmithFurnaceStone"));
    Body()->SetMaterialByName(TEXT("BlastFurnace_Firebrick"), Brick.Object);
    Body()->SetMaterialByName(TEXT("BlastFurnace_Masonry"), Stone.Object);
}

void ASmithYardFurnace::OpenBay(int32 Bay)
{
    Configure(VoxelSmeltingFurnaceId, VillageFurnaceKeys::ForBay(Bay), 0, Body()->GetStaticMesh(), nullptr, nullptr);
    RegisterBay();
    ForceNetUpdate();
}

bool ASmithYardFurnace::IsSceneStationAvailable() const
{
    return PrefabId() == VoxelSmeltingFurnaceId && VillageFurnaceKeys::Contains(AnchorCell()) && !IsFalling();
}

void ASmithYardFurnace::RegisterBay()
{
    if (auto* World = Cast<AVoxelBuildWorld>(GetOwner()))
        if (IsSceneStationAvailable()) World->RegisterSceneStation(this);
}

void ASmithYardFurnace::OnRep_Owner()
{
    Super::OnRep_Owner();
    RegisterBay();
}

void ASmithYardFurnace::OnRep_Configuration()
{
    Super::OnRep_Configuration();
    RegisterBay();
}

void ASmithYardFurnace::EndPlay(const EEndPlayReason::Type Reason)
{
    if (auto* World = Cast<AVoxelBuildWorld>(GetOwner())) World->UnregisterSceneStation(this);
    Super::EndPlay(Reason);
}

ASmithYardShelter::ASmithYardShelter()
{
    bReplicates = true;
    SetReplicateMovement(true);
    auto* Part = GetStaticMeshComponent();
    Part->SetMobility(EComponentMobility::Movable);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard/SM_SmithSmeltingCanopy"));
    Part->SetStaticMesh(Mesh.Object);
    Part->SetCollisionProfileName(TEXT("BlockAll"));

    static ConstructorHelpers::FObjectFinder<UMaterialInterface> GroundWear(TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard/Wear/M_SmithApronWear"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> WallWear(TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard/Wear/M_SmithWallBloom"));
    auto AttachWear = [this, Part](FName Socket, UMaterialInterface* Material, const FVector& Extent)
    {
        auto* Decal = CreateDefaultSubobject<UDecalComponent>(Socket);
        Decal->SetupAttachment(Part, Socket);
        Decal->SetDecalMaterial(Material);
        Decal->DecalSize = Extent;
        Decal->SetFadeScreenSize(.002f);
        Decal->SetSortOrder(3);
    };
    AttachWear(TEXT("ApronWear"), GroundWear.Object, FVector(12., 390., 510.));
    AttachWear(TEXT("WallBloom"), WallWear.Object, FVector(23., 226., 176.));
}

void AHillsBlacksmith::UpdateSmeltingYard(bool bRepaired)
{
    if (!HasAuthority()) return;
    if (!bRepaired)
    {
        if (YardShelter.IsValid()) YardShelter->Destroy();
        YardShelter.Reset();
        for (auto& Furnace : YardFurnaces)
        {
            if (Furnace.IsValid()) Furnace->Destroy();
            Furnace.Reset();
        }
        return;
    }
    const auto* Landscape = Hills.Get();
    auto* Building = Cast<AVoxelBuildWorld>(GetOwner());
    if (!Landscape || !Building) return;
    const auto& Site = Landscape->GetVillageSite();
    // Village coordinates in centimetres. The west gate is at Y=0; the smith lane lies east of the apron.
    const FVector2D Yard(-4390., -900.);
    const FRotator Facing(0., FMath::RadiansToDegrees(FMath::Atan2(Site.Axis.Y, Site.Axis.X)), 0.);
    auto Placement = [&](double X, double Y)
    {
        const FVector2D P = Site.World(Yard.X + X, Yard.Y + Y);
        return FTransform(Facing, FVector(P, Landscape->Height(P.X, P.Y)));
    };
    FActorSpawnParameters Spawn;
    Spawn.Owner = Building;
    Spawn.OverrideLevel = GetLevel();
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (!YardShelter.IsValid())
        YardShelter = GetWorld()->SpawnActor<ASmithYardShelter>(ASmithYardShelter::StaticClass(), Placement(0., 0.), Spawn);
    if (!YardShelter.IsValid()) return;
    const auto* ShelterMesh = YardShelter->GetStaticMeshComponent();
    static const FName BaySockets[] = {TEXT("FurnaceBay0"), TEXT("FurnaceBay1")};
    for (int32 Bay = 0; Bay < UE_ARRAY_COUNT(YardFurnaces); ++Bay)
    {
        if (YardFurnaces[Bay].IsValid()) continue;
        if (!ShelterMesh->DoesSocketExist(BaySockets[Bay])) continue;
        auto Pose = ShelterMesh->GetSocketTransform(BaySockets[Bay]);
        auto Position = Pose.GetLocation();
        Position.Z = Landscape->Height(Position.X, Position.Y);
        Pose.SetLocation(Position);
        if (auto* Furnace = GetWorld()->SpawnActor<ASmithYardFurnace>(ASmithYardFurnace::StaticClass(), Pose, Spawn))
        {
            YardFurnaces[Bay] = Furnace;
            Furnace->OpenBay(Bay);
        }
    }
}
