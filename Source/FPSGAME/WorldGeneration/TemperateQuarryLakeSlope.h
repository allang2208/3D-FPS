#pragma once
#include "CoreMinimal.h"

namespace TemperateRiver { struct FPlan; }

namespace TemperateQuarryLakeSlope
{
// All masks already include the shore, haul-road and site-edge fades. Height is
// signed centimetres, measured from the original surveyed lake/quarry surface.
struct FProfile
{
    float HeightCm=0, Coverage=0, Gully=0, Gravel=0, Ledge=0, Turf=0, Damp=0;
};

struct FField
{
    FVector2D Origin=FVector2D::ZeroVector, Across=FVector2D(1.,0.);
    double MinY=0.;
    int32 Rows=0;
    struct FCell { int16 HeightCm; uint8 Coverage,Gully,Gravel,Ledge,Turf,Damp; };
    TArray<FCell> Cells;
    // Quarry-local centres of separated bedrock exposures, for the mid-distance silhouette.
    TArray<FVector2D> Outcrops;

    void Build(const TemperateRiver::FPlan& Plan,int32 Seed);
    bool IntersectsCell(double WorldMinX,double WorldMinY,double Size) const;
    double Height(double X,double Y) const;
    FProfile Sample(double X,double Y) const;
private:
    bool GridPosition(double X,double Y,int32& Index,float& U,float& V) const;
};
}
