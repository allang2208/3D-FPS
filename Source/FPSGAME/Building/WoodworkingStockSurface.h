#pragma once

#include "CoreMinimal.h"
#include "WoodworkingStockGeometry.h"

namespace UE::Geometry { class FDynamicMesh3; }

// Presentation geometry only; the authoritative cutting mask is never changed.
namespace WoodworkingStockSurface
{
void Quad(UE::Geometry::FDynamicMesh3& Mesh,FVector3d A,FVector3d B,FVector3d C,FVector3d D,
    FVector3f Normal,FVector4f Color,double UVScale);
bool Build(UE::Geometry::FDynamicMesh3& Mesh,const TArray<uint8>& Wood,int32 Width,int32 Height,
    double Units,double Thickness,const WoodworkingStockGeometry::FPlan& Plan,int32 QuadBudget);
}
