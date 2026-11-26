#pragma once
#include "VoxelBuildTypes.h"

class AVillageDefenseSection;
class ATemperateHillsWorld;
class AVoxelBuildWorld;

namespace VillageGateReplacement
{
    inline constexpr int32 ReplacementSocket=10;
    // Native player-built portal shoulder and curtain centreline in gate space.
    inline constexpr double PlacedPortalHalfWidth=434.;
    inline constexpr double PlacedPortalWallY=-37.;
    AVillageDefenseSection* WallFor(FName Gate,const AActor* Actor);
    bool Layout(FName Gate,const AActor* Target,FIntVector Footprint,FTransform& Pose,FIntVector& Anchor,int32& Yaw);
    struct FOpening
    {
        TArray<FVillageGateCut> Cuts;
        TArray<AActor*> Walls;
        TSet<FIntVector> WallAnchors;
    };
    bool Collect(const AVoxelBuildWorld& Builder,const ATemperateHillsWorld& Hills,FName Gate,
        const AActor* Target,const FTransform& Pose,FOpening& Out,TArray<FTransform>* PreviewBars);
    uint32 WallSelection(TConstArrayView<FVillageGateCut> Cuts);
    bool IntervalFor(const AVillageDefenseSection& Wall,const FVoxelBuildPrefabInstance& Gate,FVector2D& Remaining);
    FTransform Trim(const FTransform& Original,FVector2D Interval);
}
