#pragma once

#include "CoreMinimal.h"

class ABronzeTorch;
class IConsoleVariable;
class UPrimitiveComponent;
class UWorld;

// Optional F6 observation for a fixed view near lit exterior fixtures.
class FVillageShadowCapture
{
public:
    bool FindFixtures(UWorld* World);
    void Start(UWorld& World);
    void Sample();
    void Finish(const FString& Directory);

private:
    struct FCaster
    {
        TWeakObjectPtr<UPrimitiveComponent> Component;
        FString Path, Mesh;
        int32 LightIndex = INDEX_NONE;
        FTransform Transform;
        FBox Bounds{ForceInit};
        FVector InitialExtent = FVector::ZeroVector;
        float BoundsScale = 1.f;
        bool bParentBounds = false;
        FString Invalidation;
        TArray<int32> Moved, Resized;
        int32 GoneAt = INDEX_NONE;
    };
    struct FFixture
    {
        FString Path;
        FVector Center;
        double Radius;
    };
    TArray<FFixture> Fixtures;
    TArray<FCaster> Casters;
    TArray<double> SampleTimes;
    FVector Eye = FVector::ZeroVector;
    FString WorldName;
    int32 CandidateCount = 0;
    int32 PageSlots = 0;
    int32 PageThreshold = -1;
    double NextSample = 0.;
    IConsoleVariable* OwnedSlots = nullptr;
    IConsoleVariable* OwnedThreshold = nullptr;
    bool bActive = false;
};
