#pragma once

#include "CoreMinimal.h"
#include "TemperateEcologyConfig.h"
#include "TemperateLakeShoreDetail.h"
#include "TemperateQuarryLakeSlope.h"

namespace UE::Geometry { class FDynamicMesh3; }
struct FTemperateVillageSite;

/** Immutable numerical river data shared by terrain workers and PCG sampling.
 * Units are centimetres. No UObject, physics queries or editor dependencies.
 */
namespace TemperateRiver
{
inline constexpr double MaxChannelBankCm=3200.;
struct FPoint
{
    FVector2D XY = FVector2D::ZeroVector;
    FVector2D Side = FVector2D(0, 1);
    double WaterZ = 0;
    double HalfWidth = 450;
    double Depth = 65;
    double Distance = 0;
    double LeftWidth = 450;
    double RightWidth = 450;
    double Bend = 0;
    double Speed = 50; // cm/s, visual flow only
};

inline double ChannelReach(const FPoint& A,const FPoint& B)
{
    return FMath::Max(FMath::Max(A.LeftWidth,A.RightWidth),FMath::Max(B.LeftWidth,B.RightWidth))+MaxChannelBankCm;
}

struct FSample
{
    bool bLake = false;
    double CliffWeight=0;
    double Distance = DBL_MAX;
    double WaterZ = 0;
    double HalfWidth = 0;
    double Depth = 0;
    double Along = 0;
    FVector2D Flow=FVector2D::ZeroVector;
    double Bank = 0;
    double Wet = 0;
    double SignedDistance = 0;
    double Bend = 0;
    double Speed = 50;
    double BankExtent = MaxChannelBankCm;
    double ShoreRock = 0; // exposed lake headland, independent of the quarry mask
    LakeShoreDetail::FProfile LocalShore;
};

struct FPlan
{
    // Applied after the unchanged settlement survey. The original plan preserves
    // the village shoulder and both existing approach routes exactly.
    TSharedPtr<const FPlan, ESPMode::ThreadSafe> SettlementBaseline;
    TArray<uint8> ProtectedLand;
    // Signed centimetres on the legacy survey lattice, or quarter-centimetres
    // on the fixed map's doubled lattice. The element count identifies the grid.
    TArray<int16> UplandReliefCm;
    int32 ProtectedSize=0;
    double WorldHalf=0;
    bool bRiverLake=false;
    struct FLake
    {
        bool Valid=false;
        bool bNaturalShore=false;
        int32 LandformSeed=0;
        FVector2D Center=FVector2D::ZeroVector, Axis=FVector2D(1,0);
        double RadiusX=13000,RadiusY=9000,WaterZ=0,Depth=140,Phase=0,Along=0;
        TArray<FVector2D> RiverMouths;
        static constexpr double MaxBankExtent=9600.;
        struct FShore { double Reach=3200.,Shelf=1800.,Rock=0.,Beach=0.; };
        enum class EBankForm : uint8 { Outlet, Shingle, RockShelf };
        struct FBankPatch
        {
            LakeShoreDetail::FSection Frame;
            double HalfLength=0.,HalfDepth=0.,CrossScale=1.,Hand=1.,Strength=1.;
            float StoneYaw=0.f;
            EBankForm Form=EBankForm::Shingle;
        };
        TArray<FBankPatch> BankPatches;
        TMap<FIntPoint,TArray<int32,TInlineAllocator<4>>> BankTiles;
        void BuildBankPatches();
        bool HasBankTile(double X,double Y) const;
        LakeShoreDetail::FProfile BankProfile(double X,double Y,double SignedEdge) const;
        LakeShoreDetail::FProfile BankAtChannel(double X,double Y,double SignedEdge,const FSample& Channel) const;
        double LayoutEdge(double X,double Y) const;
        double Edge(double X,double Y) const;
        double NaturalEdge(double X,double Y) const;
        FShore Shore(double X,double Y) const;
        double WaterDepth(double X,double Y,double SignedEdge,const FShore& Shore,const LakeShoreDetail::FProfile& Profile) const;
        double Ground(double X,double Y,double Base,const FSample& Sample,const FShore& Shore) const;
    } Lake;
    struct FWhiteCliffs
    {
        bool Valid=false;
        FVector2D Center=FVector2D::ZeroVector,Axis=FVector2D(1,0);
        double FloorZ=0;
        FVector2D Local(double X,double Y) const;
        FVector2D World(double X,double Y) const;
        double Weight(double X,double Y) const;
        double Ground(double X,double Y,double Base) const;
        double TrailDistance(double X,double Y) const;
    } WhiteCliffs;
    TemperateQuarryLakeSlope::FField QuarryLakeSlope;
    void BuildRiverLake(int32 Seed,double Half,const FTemperateVillageSite& Village,const FVector2D& Entry,
        TSharedPtr<const FPlan, ESPMode::ThreadSafe> Original);
    double Protection(double X,double Y) const;
    void BuildUplandRelief(int32 Seed);
    double UplandOffset(double X,double Y) const;
    void RebuildBuckets();
    void BuildRiverLakeMesh(double X,double Y,double Size,UE::Geometry::FDynamicMesh3& Mesh) const;
    bool IntersectRiverLake(const FVector& Start,const FVector& End,FVector& Position,FVector& Normal,double& Along) const;
    TemperateEcology::FProfile Ecology;
    double BankReliefCm = 22;
    int32 GenerationVersion = 1;
    TArray<FPoint> Points;
    TMap<FIntPoint, TArray<int32>> Buckets;
    // Cell-centred land mask, prepared once alongside the drainage plan.
    TArray<uint8> RainforestMask;
    int32 ForestGridSize = 0;
    double ForestHalfSize = 0;
    FVector2D ForestAnchor = FVector2D::ZeroVector;
    // V3: yellow village hill / approach corridor, rainforest everywhere around it.
    bool bVillageRainforest = false;
    void BuildRainforest(int32 Seed, double HalfSize);
    void BuildVillageRainforest(int32 Seed,double HalfSize,const FTemperateVillageSite& Village,const FVector2D& Entry);
    double RainforestWeight(double X, double Y) const;
    FSample Sample(double X, double Y) const;
    FSample SampleChannel(double X, double Y) const;
    double NaturalGround(double X,double Y,int32 Seed) const;
    double Height(double X, double Y, int32 Seed) const;
    FVector Normal(double X, double Y, int32 Seed) const;
    bool IntersectsCell(double X, double Y, double Size) const;
    void BuildWaterMesh(double X, double Y, double Size, UE::Geometry::FDynamicMesh3& Mesh) const;
    /** Cosmetic downward crossing of the same ribbon triangles used by BuildWaterMesh. */
    bool IntersectWaterSegment(const FVector& Start, const FVector& End, double AlongMin, double AlongMax,
        FVector& Position, FVector& Normal, double& Along) const;
};

using FPlanPtr = TSharedPtr<const FPlan, ESPMode::ThreadSafe>;
FPlanPtr Generate(int32 Seed, double HalfSize, const FVector2D& ProtectedSpawn, double BankReliefCm=22, int32 Version=1,
    const TemperateEcology::FProfile& Ecology=TemperateEcology::Get());
// Shared sediment patches for ground shading, small stones and plant spacing.
double PebbleCover(double X,double Y,int32 Seed,const FSample& River);
}
