#pragma once

#include "CoreMinimal.h"

#if WITH_EDITOR
class AForestVillageRegion;
class UStaticMesh;

namespace ForestWoodDressing
{
enum class EKind : uint8 { None, Branch, Stump, Log, Trunk, Large, ReferenceTwig };
EKind Kind(const UStaticMesh* Mesh);
int32 CullEndCm(EKind Type);

struct FSupport
{
    EKind Type=EKind::None;
    FVector2D Center=FVector2D::ZeroVector;
    double AxisAngle=0.;
    double Length=0.;
    double Height=0.;
    TArray<FVector,TInlineAllocator<15>> Feet;
    TArray<FVector,TInlineAllocator<5>> TerrainChecks;
    TArray<FVector,TInlineAllocator<5>> Body;
};
FSupport Measure(UStaticMesh* Mesh);
bool Fit(const AForestVillageRegion& Region,const FSupport& Support,FVector2D Center,double Heading,double Scale,FTransform& Out);
}
#endif
