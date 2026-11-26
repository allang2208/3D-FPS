#pragma once

#include "CoreMinimal.h"

class ULevel;
class AForestVillageRegion;

namespace ForestVillageRelief
{
    // World centimetres and the one-metre grid shared by the annex and its apron.
    constexpr int32 MinX = -17200, MinY = 25200, Step = 100, Columns = 119, Rows = 146;

    int32 VertexOffset(int32 Column, int32 Row);
    double OffsetAt(double X, double Y);
    double SurfaceAt(TConstArrayView<float> Surface, double X, double Y);
    int32 SitedVertexOffset(TConstArrayView<int16> Offsets,int32 Column,int32 Row);
    double SampleOffsets(TConstArrayView<int16> Offsets,double X,double Y);
    void FitLevelDressing(ULevel& Level,const AForestVillageRegion& Region);
}
