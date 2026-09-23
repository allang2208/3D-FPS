#pragma once

#include "CoreMinimal.h"

class UPointLightComponent;

namespace AuthoredDungeonLighting
{
    bool IsOptimizationEnabled();
}

struct FAuthoredDungeonLight
{
    TWeakObjectPtr<UPointLightComponent> Component;
    float FullIntensity = 0.f;
    float Alpha = 1.f;
};

struct FAuthoredDungeonLightPortal
{
    int32 Neighbor = INDEX_NONE;
    FVector Center = FVector::ZeroVector;
    FVector Extent = FVector::ZeroVector;
};

struct FAuthoredDungeonLightModule
{
    TArray<FBox> Cells;
    TArray<FAuthoredDungeonLightPortal> Portals;
    TArray<FAuthoredDungeonLight> Lights;
    bool bConnector = false;
    double LastWantedSeconds = -1.0;
};
