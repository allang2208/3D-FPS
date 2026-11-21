// Source/FPSGAME/Building/VoxelBuildPalette.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 2-3 | file scope
#include "VillageBuildDefense.h"
#include "../WorldGeneration/VillageMasonry.h"

// Lines 5-7 | file scope
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../WorldGeneration/HighVillageDefense.h"

// Lines 30-54 | void UVoxelBuildPalette::PostLoad()
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
        VillageMasonry::Mesh(TEXT("SM_VillageWallRepairedA")),
        FIntVector(15,3,11),AVillageDefenseSection::StaticClass());
    // Include both gate leaves and the hardware that reaches past each hinge.
    RegisterVillagePiece(VillageBuildDefense::WoodGate,NSLOCTEXT("VoxelBuilding","VillageWoodGate","木质大门"),
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateNarrow.SM_GateNarrow")),
        FIntVector(38,3,11),AVillageDefenseGate::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::HighWall,NSLOCTEXT("VoxelBuilding","VillageHighWall","石砌高墙"),
        AHighVillageWall::WallMeshPath(),FIntVector(15,10,24),AHighVillageWall::StaticClass());
    RegisterVillagePiece(VillageBuildDefense::StoneGate,NSLOCTEXT("VoxelBuilding","VillageStoneGate","石城门 · 升降铁闸"),
        AHighVillageGate::PlacedPortalMeshPath(),FIntVector(51,34,51),AHighVillageGate::StaticClass());
    RegisterVillagePiece(VillageWallStairs::Id,NSLOCTEXT("VoxelBuilding","VillageWallStairs","城墙石阶"),
        FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SM_WallAccessStairs.SM_WallAccessStairs")),
        FIntVector(16,28,18),AVillageDefenseStairs::StaticClass());
