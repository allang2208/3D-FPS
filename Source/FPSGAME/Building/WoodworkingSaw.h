#pragma once
#include "CoreMinimal.h"

namespace ColdSteelWoodworking
{
struct FDeviceGeometry
{
    static constexpr double StockBottom=95.65,StockThickness=1.2,BladeRadius=16.2,SawHeight=88.8;
};
/** Tunable virtual-device defaults in mask units, not real machinery specifications. */
struct FSawSettings
{
    double Kerf=3,ContactLength=128,RotationStep=1,MaximumFeedStep=8;
    double CentimetersPerPixel=.22;
};
struct FBoardPose
{
    FVector2D Offset=FVector2D::ZeroVector;
    double Angle=0;
    FVector2D ToWork(FVector2D Point,FVector2D Center) const
    {
        const FVector2D P=Point-Center;const double C=FMath::Cos(Angle),S=FMath::Sin(Angle);
        return Offset+FVector2D(C*P.X-S*P.Y,S*P.X+C*P.Y);
    }
    FVector2D ToBoard(FVector2D Point,FVector2D Center) const
    {
        const FVector2D P=Point-Offset;const double C=FMath::Cos(Angle),S=FMath::Sin(Angle);
        return Center+FVector2D(C*P.X+S*P.Y,-S*P.X+C*P.Y);
    }
};
}
