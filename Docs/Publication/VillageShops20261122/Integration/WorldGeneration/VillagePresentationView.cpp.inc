#include "VillagePresentationView.h"
#include "../FPSGAMECharacter.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

namespace
{
struct FLocalView
{
    FVector Eye, Forward;
    double FovScale, ScopePower;
};

const TArray<FLocalView,TInlineAllocator<2>>& LocalViews(UWorld& World)
{
    // The shop actors and PCG groups all sample the same local cameras on the game thread.
    static TWeakObjectPtr<UWorld> LastWorld;
    static uint64 LastFrame = MAX_uint64;
    static TArray<FLocalView,TInlineAllocator<2>> Views;
    if (LastWorld.Get() == &World && LastFrame == GFrameCounter) return Views;
    LastWorld = &World;
    LastFrame = GFrameCounter;
    Views.Reset();
    for (auto It = World.GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get();
        if (!PC || !PC->IsLocalController() || !PC->PlayerCameraManager || !PC->GetViewTarget() ||
            (!PC->GetPawn() && PC->GetViewTarget() == PC)) continue;
        auto* Camera = PC->PlayerCameraManager.Get();
        double Power = 1.;
        auto* Character = Cast<AFPSGAMECharacter>(PC->GetPawn());
        if (Character && PC->GetViewTarget() == Character && Character->UsesPhysicalScope() &&
            (Character->IsAiming() || Character->GetScopePresentationAlpha() > .001f))
            Power = FMath::Max(1.f, Character->GetPhysicalScopeMagnification());
        const double Scale = FMath::Min(1., FMath::Tan(FMath::DegreesToRadians(
            FMath::Clamp(double(Camera->GetFOVAngle()), 5., 140.) * .5)));
        Views.Add({Camera->GetCameraLocation(), Camera->GetCameraRotation().Vector(), Scale, Power});
    }
    return Views;
}
}

double VillagePresentationView::Distance(UWorld& World, const FVector& Center, double Radius, bool* HasView)
{
    const auto& Views = LocalViews(World);
    if (HasView) *HasView = !Views.IsEmpty();
    if (Views.IsEmpty()) return 0.;
    double Nearest = TNumericLimits<double>::Max();
    for (const auto& View : Views)
    {
        const FVector Offset = Center - View.Eye;
        const double Range = Offset.Size();
        // Include a margin outside the optic for a pan over roofs or a doorway.
        const double Power = FVector::DotProduct(View.Forward, Offset) > .80 * Range - Radius ? View.ScopePower : 1.;
        Nearest = FMath::Min(Nearest, FMath::Max(0., Range - Radius) * View.FovScale / Power);
    }
    return Nearest;
}
