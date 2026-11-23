#include "FireParticleView.h"
#include "VillagePresentationView.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "SceneView.h"

void FFireParticleViews::Refresh(UWorld& World)
{
    const double Now = World.GetTimeSeconds();
    if (Now < RefreshAt) return;
    RefreshAt = Now + .10;
    int32 Count = 0;
    for (auto It = World.GetPlayerControllerIterator(); It; ++It)
    {
        const auto* PC = It->Get();
        if (!PC || !PC->IsLocalController() || !PC->GetViewTarget()) continue;
        const auto* Player = PC->GetLocalPlayer();
        if (!Player) continue;
        if (Count == Views.Num()) Views.AddDefaulted();
        auto& View = Views[Count++];
        FRotator Rotation;
        PC->GetPlayerViewPoint(View.Eye, Rotation);
        FSceneViewProjectionData Projection;
        View.bHasProjection = Player->ViewportClient && Player->ViewportClient->Viewport &&
            Player->GetProjectionData(Player->ViewportClient->Viewport, Projection);
        if (View.bHasProjection)
        {
            View.Eye = Projection.ViewOrigin;
            GetViewFrustumBounds(View.Frustum, Projection.ComputeViewProjectionMatrix(), true);
        }
    }
    Views.SetNum(Count, EAllowShrinking::No);
}

double FFireParticleViews::NearestDistanceSquared(UWorld& World, const FVector& Position)
{
    Refresh(World);
    double Nearest = TNumericLimits<double>::Max();
    for (const auto& View : Views) Nearest = FMath::Min(Nearest, FVector::DistSquared(Position, View.Eye));
    return Nearest;
}

EFireParticleDetail FFireParticleViews::Classify(UWorld& World, const FVector& Source, float Radius,
    float VerticalOffset, float FullRange, float MaxRange, const UNiagaraComponent* Effect, bool bWasFull)
{
    Refresh(World);
    const FVector Center = Source + FVector(0, 0, VerticalOffset);
    const double MaxDistSq = FMath::Square(double(MaxRange));
    const bool bInView = Views.ContainsByPredicate([&](const FView& View)
    {
        return FVector::DistSquared(Source, View.Eye) <= MaxDistSq &&
            (!View.bHasProjection || View.Frustum.IntersectSphere(Center, Radius));
    });
    if (!bInView) return EFireParticleDetail::Off;

    const double Range = VillagePresentationView::Distance(World, Source);
    if (Range > FullRange * (bWasFull ? 1.08 : 1.)) return EFireParticleDetail::Simple;
    // A primary emitter survives occlusion inside the frustum. The renderer can report it
    // on screen again even when every decorative emitter is asleep.
    if (Effect && Effect->IsActive() && World.GetTimeSeconds() - Effect->GetLastRenderTimeOnScreen() > .65)
        return EFireParticleDetail::Simple;
    return EFireParticleDetail::Full;
}
