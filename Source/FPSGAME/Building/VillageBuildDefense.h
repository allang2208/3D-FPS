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
    inline const FName HighTower(TEXT("village_high_tower"));
    inline const FName Ballista(TEXT("village_ballista"));
    inline const FName Trebuchet(TEXT("village_trebuchet"));
    inline const FName OilPot(TEXT("village_oil_pot"));
    inline bool IsSiegeEngine(FName Id) { return Id==Ballista || Id==Trebuchet || Id==OilPot; }
    inline const FName MechanicsPlan(TEXT("garrison_mechanics"));
    inline const FName StoneGate(TEXT("village_stone_gate"));
    // The overhead camera and authority both measure construction reach from the builder.
    inline constexpr double SurveyRadius=12000.;
    inline constexpr double SurveyTraceLength=50000.;
    inline bool InSurveyRange(const FVector& Builder,const FVector& Site)
    {
        return !Site.ContainsNaN() && FVector::DistSquared(Builder,Site)<=FMath::Square(SurveyRadius);
    }
    inline FVector PlacementScale(FName Id){return Id==StoneWall?FVector(1.,1.,1.25):FVector::OneVector;}
    inline bool IsBasicWallOrGate(FName Id) { return Id==StoneWall||Id==WoodGate; }
    enum class ETier : uint8 { None, RepairedWall, HighCurtain, Fortifications, Mechanics };
    inline ETier RequiredTier(FName Id)
    {
        if(IsBasicWallOrGate(Id))return ETier::RepairedWall;
        if(Id==HighWall||Id==StoneGate||Id==VillageWallStairs::Id)return ETier::HighCurtain;
        if(Id==HighTower)return ETier::Fortifications;
        if(IsSiegeEngine(Id))return ETier::Mechanics;
        return ETier::None;
    }
    inline bool IsVillageRecipe(FName Id) { return RequiredTier(Id)!=ETier::None; }
    ETier UnlockedTier(const ATemperateHillsWorld* Hills);
    const TCHAR* ProjectName(ETier Tier);
    FString LockReason(ETier Tier);

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
