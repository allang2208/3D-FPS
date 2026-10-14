#pragma once
#include "CoreMinimal.h"
class APawn;
class UMaterialInstanceDynamic;

/** Blizzard-only environment queries. Geometry remains authoritative; cosmetic
 *  cloud/ice collisions never decide whether a region deals damage. */
namespace BlizzardEnvironment
{
// Each cell stores floor Z relative to the centre, headroom and usable width.
constexpr int32 CellCount=25;
constexpr int32 MaxLayers=3;
constexpr int32 VolumeCellCount=CellCount*MaxLayers;
// Preserve the existing cloud-height scale as a bounded vertical damage reach.
float VerticalReach(float RadiusY);
void BuildVolumeCells(APawn* Caster,const FVector& Center,const FVector& Axis,float RadiusX,float RadiusY,TArray<FVector>& Cells);
void SightOrigins(APawn* Caster,const FVector& Center,TArray<FVector,TInlineAllocator<3>>& Origins);
bool VolumeExposure(APawn* Caster,const AActor* Target,const FVector& Center,const FVector& Axis,
    float RadiusX,float RadiusY,const TArray<FVector,TInlineAllocator<3>>& Origins);
FName CellParameter(int32 Index,bool bNiagara=false);
FVector CellOffset(int32 Index,float RadiusX,float RadiusY,const FVector& Axis);
int32 CellAt(const FVector& Offset,float RadiusX,float RadiusY,const FVector& Axis);
void BuildCells(APawn* Caster,const FVector& Center,const FVector& Axis,float RadiusX,float RadiusY,TArray<FVector>& Cells);
void MaterialCells(UMaterialInstanceDynamic* Material,const FVector& Center,const FVector& Axis,float RadiusX,float RadiusY,const TArray<FVector>& Cells);
// Area sight passes open barriers; vertical floor/headroom probes keep physical geometry.
bool Trace(APawn* Caster,const FVector& Start,const FVector& End,FHitResult& Hit,bool bAreaSight=false);
bool Floor(APawn* Caster,const FVector& Near,float Rise,float Drop,FHitResult& Hit);
bool GroundRoute(APawn* Caster,const FVector& From,const FVector& To);
bool Validate(APawn* Caster,float Range,FVector& Point,FVector& Normal,FVector& Axis,FString& Failure);
bool Select(APawn* Caster,float Range,const FVector& View,const FVector& Direction,FVector& Point,FVector& Normal,FVector& Axis,FString& Failure);
}
