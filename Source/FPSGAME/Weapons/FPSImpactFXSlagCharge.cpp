#include "FPSImpactFXSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"

void UFPSImpactFXSubsystem::SpawnSlagSlam(const FHitResult& Ground, const FVector& Forward,
    float Radius, UCameraComponent* ViewCamera, const AActor* Source)
{
    if (!bReady || !Ground.bBlockingHit || !IsValid(ViewCamera)) return;
    const float Distance = FVector::Dist(Ground.ImpactPoint, ViewCamera->GetComponentLocation());
    if (Distance > 2800.f) return;
    constexpr float Strength = 1.f;
    SpawnPounceLanding(Ground, Forward, Radius, 360.f, ViewCamera, Source);
    if (FVector::DotProduct(Ground.ImpactPoint-ViewCamera->GetComponentLocation(), ViewCamera->GetForwardVector()) < -150.f) return;
    if (BudgetFrame != GFrameCounter) { BudgetFrame = GFrameCounter; FrameBursts = 0; }
    if (FrameBursts >= 8) return;
    ++FrameBursts; Camera = ViewCamera;
    const double Now = GetWorld()->GetTimeSeconds();
    const FVector Normal = Ground.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
    const FVector Heading = FVector::VectorPlaneProject(Forward, Normal).GetSafeNormal();
    const FVector Side = FVector::CrossProduct(Heading, Normal);
    // Reuse the existing world particle pools/materials: no new emitter, actor,
    // permanent decal, dynamic light or per-monster cosmetic Tick.
    for (int32 Group = 0; Group < 3; ++Group)
    {
        if (!ParticleMaterials[Group]) continue;
        const int32 Start = Group == 0 ? 0 : Group == 1 ? SparkSlots : SparkSlots+DustSlots;
        const int32 End = Start + (Group == 0 ? SparkSlots : Group == 1 ? DustSlots : ChipSlots);
        const int32 Count = Group == 0 ? 5 : Group == 1 ? 3 : 4;
        int32 Emitted = 0;
        for (int32 Slot = Start; Slot < End && Emitted < (Distance > 1600.f ? FMath::Min(1,Count) : Count)
            && ActiveParticles < MaxActiveParticles; ++Slot)
        {
            if (Particles[Slot].Life > 0.f) continue;
            auto& P = Particles[Slot]; P = FParticle();
            P.Born = Now; P.Position = Ground.ImpactPoint+Normal*(Group == 0 ? 20.f : 10.f)+Side*FMath::FRandRange(-30.f,30.f);
            P.Velocity = -Heading*FMath::FRandRange(35.f,95.f)*Strength+Side*FMath::FRandRange(-65.f,65.f)+Normal*FMath::FRandRange(25.f,90.f);
            P.Rotation = FRotator(0,0,FMath::FRandRange(-180.f,180.f));
            if (Group == 0)
            { P.Life=.24f; P.Gravity=-220.f; P.Size=FVector(.55f,2.6f,1.f); P.Color=FLinearColor(1.f,.22f,.035f); P.Opacity=.8f; }
            else if (Group == 1)
            { P.Life=.42f; P.Gravity=8.f; P.Size=FVector(18.f+20.f*Strength); P.Color=FLinearColor(.16f,.13f,.11f); P.Opacity=.35f; }
            else
            { P.Life=.36f; P.Gravity=-620.f; P.Size=FVector(.8f,1.1f,.65f); P.Color=FLinearColor(.08f,.045f,.025f); P.Opacity=1.f; P.Spin=FRotator(420.f,250.f,310.f); }
            ++ActiveParticles; ++Emitted;
        }
    }
}
