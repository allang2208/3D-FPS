#pragma once
#include "CoreMinimal.h"

class AActor;
class UWorld;

/** A physical support point and the free-space body position above it. */
struct FLurkerSurfacePoint
{
    FVector Center = FVector::ZeroVector;
    FVector Normal = FVector::UpVector;
};

/** M09-style collision support extended to floors, walls, roofs and convex edges. */
namespace LurkerSurfaceRoute
{
    bool Support(UWorld* World, const AActor* Owner, FVector From, FVector To, float Radius, FLurkerSurfacePoint& Out);
    bool Clear(UWorld* World, const AActor* Owner, FVector Center, float Radius);
    bool Segment(UWorld* World, const AActor* Owner, FVector From, FVector To, float Radius);
    /** Optional floor corridor guide; physical surface search still works without NavMesh. */
    bool GroundGuide(UWorld* World, const AActor* Owner, const FLurkerSurfacePoint& Start,
        FVector Goal, float Radius, FVector& Guide);
    bool Build(UWorld* World, const AActor* Owner, const FLurkerSurfacePoint& Start, FVector Goal,
        float Radius, const TArray<FVector>& Recent, TArray<FLurkerSurfacePoint>& Out);
    FVector Arc(FVector Start, FVector End, FVector Outward, float Height, float Alpha);
    bool ClearArc(UWorld* World, const AActor* Owner, FVector Start, FVector End, FVector Outward, float Height, float Radius);
}
