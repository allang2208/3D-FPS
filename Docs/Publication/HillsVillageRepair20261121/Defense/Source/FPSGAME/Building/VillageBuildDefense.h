#pragma once
#include "CoreMinimal.h"
#include "VillageWallStairs.h"

class AVillageDefenseSection;
class ATemperateHillsWorld;
struct FVoxelBuildPrefab;

namespace VillageBuildDefense
{
    inline const FName StoneWall(TEXT("village_stone_wall"));
    inline const FName WoodGate(TEXT("village_wood_gate"));
    inline const FName HighWall(TEXT("village_high_wall"));
    inline const FName StoneGate(TEXT("village_stone_gate"));
    inline FVector PlacementScale(FName Id){return Id==StoneWall?FVector(1.,1.,1.25):FVector::OneVector;}
    inline bool IsBasicWallOrGate(FName Id) { return Id==StoneWall||Id==WoodGate; }
    inline bool IsVillageRecipe(FName Id)
    {
        return IsBasicWallOrGate(Id)||Id==HighWall||Id==StoneGate||Id==VillageWallStairs::Id;
    }

    inline FTransform Placement(FName Id,FIntVector Cell,FIntVector RotatedFootprint,int32 Yaw,int32 GroundYawDegrees=INDEX_NONE)
    {
        // Fine ground turns keep the native footprint's centre on the aimed grid
        // column. Only the mesh (and the off-centre portal sill) turns around it.
        const FVector Center=FVector(Cell)*20.+FVector(RotatedFootprint.X*10.,RotatedFootprint.Y*10.,0.);
        const FQuat Rotation=FRotator(0.,GroundYawDegrees==INDEX_NONE?Yaw*90.:GroundYawDegrees,0.).Quaternion();
        // Keep the established sill-to-cell registration for existing saved
        // gates. The precise occupancy is rebuilt from the current portal mesh.
        const FVector Pivot=Id==StoneGate?Center-Rotation.RotateVector(FVector(70.,180.,0.)):Center;
        // Native village meshes use the ground plane as their origin. The
        // repaired masonry's buried foundation and 1.25 height match the perimeter.
        return FTransform(Rotation,Pivot,PlacementScale(Id));
    }

    AVillageDefenseSection* SpawnPlaced(const FVoxelBuildPrefab& Definition,ATemperateHillsWorld& Hills,
        const FGuid& InstanceId,const FTransform& Pose);
}
