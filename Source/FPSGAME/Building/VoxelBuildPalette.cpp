#include "VoxelBuildPalette.h"
#include "VillageBuildDefense.h"
#include "../WorldGeneration/VillageHotOil.h"
#include "../WorldGeneration/VillageSiegeEngine.h"
#include "../WorldGeneration/VillageMasonry.h"
#include "Engine/StaticMesh.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../WorldGeneration/HighVillageDefense.h"

void UVoxelBuildPalette::PostLoad()
{
    Super::PostLoad();
    // Extend only the live catalog, including server/save-load consumers. This
    // keeps authored entries and their order intact without resaving the asset.
    if(GetPathName()!=TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette"))return;
    const FName Id(TEXT("planting_bed"));
    const FSoftObjectPath MeshPath(TEXT("/Game/Building/PlantingBed20261017/SM_PlantingBed_2m_V2.SM_PlantingBed_2m_V2"));
    if(!FindComponent(Id)&&!Components.ContainsByPredicate([&MeshPath](const FVoxelBuildPrefab& Entry)
        {return Entry.Mesh.ToSoftObjectPath()==MeshPath;}))
    {
        FVoxelBuildPrefab Entry;
        Entry.Id=Id;
        Entry.DisplayName=NSLOCTEXT("VoxelBuilding", "PlantingBed", "种植地（2米×2米）");
        Entry.Mesh=TSoftObjectPtr<UStaticMesh>(MeshPath);
        Entry.Footprint=FIntVector(10,10,2);
        // Center the 29.6 cm mesh in the 40 cm placement envelope, then align its base to the grid.
        Entry.PivotOffsetCm=FVector(0.,0.,-5.2);
        Components.Add(MoveTemp(Entry));
    }

    auto RegisterVillagePiece=[this](FName PieceId,FText Caption,const FSoftObjectPath& AssetPath,
        FIntVector Size,UClass* LogicClass)
    {
        if(FindComponent(PieceId))return;
        FVoxelBuildPrefab& Piece=Components.AddDefaulted_GetRef();
        Piece.Id=PieceId;
        Piece.DisplayName=MoveTemp(Caption);
        Piece.Mesh=TSoftObjectPtr<UStaticMesh>(AssetPath);
        Piece.Footprint=Size;
        Piece.ActorClass=LogicClass;
    };
    RegisterVillagePiece(VillageBuildDefense::StoneWall,NSLOCTEXT("VoxelBuilding","VillageStoneWall","石头围墙"),
        VillageMasonry::CastleMesh(TEXT("SM_VillageWallRepairedA")),
        FIntVector(15,3,11),AVillageDefenseSection::StaticClass());
    // Include both gate leaves and the hardware that reaches past each hinge.
    RegisterVillagePiece(VillageBuildDefense::WoodGate,NSLOCTEXT("VoxelBuilding","VillageWoodGate","木质大门"),
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateNarrow.SM_GateNarrow")),
        FIntVector(38,3,11),AVillageDefenseGate::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::HighWall,NSLOCTEXT("VoxelBuilding","VillageHighWall","石砌高墙"),
        AHighVillageWall::WallMeshPath(),FIntVector(15,10,24),AHighVillageWall::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::StoneGate,NSLOCTEXT("VoxelBuilding","VillageStoneGate","石城门 · 升降铁闸"),
        AHighVillageGate::PlacedPortalMeshPath(),FIntVector(51,34,51),AHighVillageGate::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::HighTower,NSLOCTEXT("VoxelBuilding","VillageHighTower","石砌高塔楼"),
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/ChapelGatehouse/SquareKeep/SM_HighWatchtower.SM_HighWatchtower")),
        FIntVector(50,50,98),AVillageDefenseSection::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::Ballista,NSLOCTEXT("VoxelBuilding","VillageBallista","固定式弩炮"),
        AVillageSiegeEngine::MeshAsset(TEXT("BallistaPreview")),FIntVector(28,14,12),AVillageSiegeEngine::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::Trebuchet,NSLOCTEXT("VoxelBuilding","VillageTrebuchet","配重投石机"),
        AVillageSiegeEngine::MeshAsset(TEXT("TrebuchetPreview")),FIntVector(37,19,38),AVillageSiegeEngine::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::OilPot,NSLOCTEXT("VoxelBuilding","VillageOilPot","热油锅"),
        AVillageOilKettle::MeshPath(),FIntVector(8,9,5),AVillageOilKettle::StaticClass());
    RegisterVillagePiece(VillageWallStairs::Id,NSLOCTEXT("VoxelBuilding","VillageWallStairs","城墙石阶"),
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SM_WallAccessStairs.SM_WallAccessStairs")),
        FIntVector(16,28,18),AVillageDefenseStairs::StaticClass());
}

FVoxelPhysicalMaterial UVoxelBuildPalette::Physical(FName Id) const
{
    const auto* Definition=Find(Id);
    if(Definition&&Definition->bOverridePhysics)return Definition->Physics;
    // Balance values, not a material certificate. Tension is what limits unsupported spans.
    // Contract (Docs/Building/voxel-build-workflow.md): every voxel material must guarantee a
    // 2.0 m clear span, with a 100 kg player standing mid-span, and fail before roughly 3-4 m.
    // Re-measure with Tools/Building/voxel_stress_probe.cpp after changing density or tension.
    // 2026-09-16: all three strengths doubled at the user's request, so a 1 m hanging wall section
    // survives its own placement. Re-run Tools/Building/run_voxel_stress_probe.ps1 after any change.
    // 2026-09-16 (third pass, user request): every voxel weighs a quarter of what it did - wood
    // 600 -> 150 kg/m3, stone/marble 2600 -> 650 kg/m3 (1.2 kg and 5.2 kg per 20 cm cube). Same
    // strength limits, so spans grow by roughly the same factor; re-run the probe before publishing
    // the span numbers.
    // 2026-09-16 (second pass): stone/marble shear 80 -> 300 kPa. Measured on the player's saved wall
    // (Docs/Building/voxel-vertical-build-diagnosis-20260916.md): every "cannot build past 1 m"
    // roll-back was governed by shear across a 20x20 cm face, not by weight. Tension/compression are
    // unchanged, so the 2 m clear-span contract still fails in the same 3-4 m band.
    FVoxelPhysicalMaterial Result;
    if(Id==TEXT("stone")||Id==TEXT("marble"))
    {
        Result.DensityKgM3=650;Result.CompressionPa=6000000;Result.TensionPa=900000;
        Result.ShearPa=300000;Result.Durability=500;Result.JoulesPerDamage=15;
    }
    else
    {
        Result.DensityKgM3=150;Result.CompressionPa=700000;Result.TensionPa=260000;
        Result.ShearPa=120000;Result.Durability=180;Result.JoulesPerDamage=6;
    }
    return Result;
}

const FVoxelBuildMaterial* UVoxelBuildPalette::Find(FName Id) const
{
    return Materials.FindByPredicate([Id](const FVoxelBuildMaterial& Entry){return Entry.Id==Id;});
}
