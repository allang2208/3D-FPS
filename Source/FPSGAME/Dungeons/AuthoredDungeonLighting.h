#pragma once

#include "CoreMinimal.h"

class ULocalLightComponent;
class UPrimitiveComponent;

namespace AuthoredDungeonLighting
{
    bool IsOptimizationEnabled();
}

struct FAuthoredDungeonLight
{
    TWeakObjectPtr<ULocalLightComponent> Component;
    float FullIntensity = 0.f;
    float Alpha = 1.f;
    bool bPreservedActor = false;
    float OriginalDrawDistance = 0.f;
    float OriginalFadeRange = 0.f;
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

/** One render component may contain instances belonging to several connected rooms. */
struct FAuthoredDungeonRenderGroup
{
    TWeakObjectPtr<UPrimitiveComponent> Component;
    TArray<int32> Modules;
    bool bHiddenByScheduler = false;
};
