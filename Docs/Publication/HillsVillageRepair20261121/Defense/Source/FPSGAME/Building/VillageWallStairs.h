#pragma once

#include "CoreMinimal.h"

class AHighVillageWall;
class AActor;
class AVillageDefenseSection;
class UWorld;
struct FVoxelBuildPrefabInstance;

namespace VillageWallStairs
{
    inline const FName Id(TEXT("village_wall_stairs"));

    struct FDock
    {
        FTransform Pose=FTransform::Identity;
        FIntVector Anchor=FIntVector::ZeroValue;
        int32 Yaw=0;
        int32 Socket=INDEX_NONE;
        AVillageDefenseSection* Target=nullptr;
    };

    bool CanDock(FName PieceId);
    /** Fixed gatehouse flight, mating the side of its upper landing to the courtyard gallery. */
    FTransform GatehouseFlight(const FTransform& Gate,bool bWest,bool bRightPier);
    FBox EntranceBounds();
    bool HasClearStairEntrance(UWorld& World,const FTransform& Stair);
    /** Resolve a generated section, a placed prefab wrapper or its attached logic actor. */
    AVillageDefenseSection* ResolveTarget(const AActor* Actor);
    /** WheelTurns is relative to the target. Yaw in the result is the world grid address. */
    bool MakeDock(FName PieceId,FIntVector Footprint,const AActor* Target,const FVector& AimPoint,int32 WheelTurns,FDock& Out);
    /** Resolve a selected side and wheel setting against the authority's live host transform. */
    bool MakeDockAtSocket(FName PieceId,FIntVector Footprint,const AActor* Target,int32 Socket,FDock& Out);
    /** Recompute canonical transforms from live collision geometry; no client pose is trusted. */
    bool FindDock(UWorld* World,FName PieceId,FIntVector Footprint,FIntVector Anchor,int32 Yaw,FDock& Out,
        const AActor* ExpectedTarget=nullptr);

    FTransform Placement(const FVoxelBuildPrefabInstance& Instance);
    /** The pose is the exact stair base. Anchor and QuarterTurns are its build-grid address. */
    bool MakeDock(const AHighVillageWall& Wall, FTransform& WorldPose, FIntVector& Anchor, int32& QuarterTurns);
    AHighVillageWall* FindDock(UWorld* World, FIntVector Anchor, int32 QuarterTurns, FTransform& OutPose);
}
