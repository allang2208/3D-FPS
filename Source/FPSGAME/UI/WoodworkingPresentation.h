#pragma once
#include "CoreMinimal.h"

namespace WoodworkingPresentation
{
// Appearance budgets only. Gameplay kerf, target tolerance and rewards live elsewhere.
constexpr int32 MaximumChips=32,ChipsPerContact=6;
constexpr double ChipInterval=.045,ChipLifetime=.48,SoundInterval=.10;
// Empty/single-point paths stay unchanged; an already closed path is not closed twice.
void ClosePolyline(TArray<FVector2D>& Points);
void TargetContours(const TArray<uint8>& Mask,int32 Width,int32 Height,TArray<TArray<FVector2D>>& Out);
}
