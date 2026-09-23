#include "FPSImpactFXSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

void UFPSImpactFXSubsystem::SpawnPounceLanding(const FHitResult& Ground, const FVector& Forward,
    float Radius, float Angle, UCameraComponent* ViewCamera, const AActor* Source)
{
    if (!bReady || !Ground.bBlockingHit || !IsValid(ViewCamera)) return;
    const float Distance = FVector::Dist(Ground.ImpactPoint, ViewCamera->GetComponentLocation());
    if (Distance > 4000.f) return;
    // Two preallocated, spatial voices preserve existing tails and cap overlap.
    // Sound remains audible when the impact is behind the viewer.
    if (PounceImpactSound && Distance < 2000.f)
        for (const auto& Voice : PounceVoices)
            if (Voice && !Voice->IsPlaying())
            {
                Voice->SetWorldLocation(Ground.ImpactPoint);
                Voice->SetVolumeMultiplier(.78f);
                Voice->SetPitchMultiplier(FMath::FRandRange(1.08f, 1.14f));
                Voice->Play();
                break;
            }
    if (FVector::DotProduct(Ground.ImpactPoint-ViewCamera->GetComponentLocation(), ViewCamera->GetForwardVector()) < -Radius) return;
    if (BudgetFrame != GFrameCounter) { BudgetFrame=GFrameCounter; FrameBursts=0; }
    if (FrameBursts >= 8) return;
    ++FrameBursts;
    Camera = ViewCamera;
    const double Now = GetWorld()->GetTimeSeconds();
    const FVector Normal = Ground.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
    const FVector Heading = FVector::VectorPlaneProject(Forward, Normal).GetSafeNormal();
    const float HalfAngle = FMath::Clamp(Angle, 1.f, 180.f)*.5f;
    const FVector Origin = Ground.ImpactPoint+Normal*3.f;
    // A four-slot world pool. No transient actors, per-hit material instances,
    // physics shards, lights, or permanent ground decals.
    constexpr int32 WaveStart = SparkSlots+DustSlots+ChipSlots+BloodMistSlots+BloodDropSlots;
    if (ParticleMaterials[5] && ActiveParticles < MaxActiveParticles)
        for (int32 Slot=WaveStart; Slot<WaveStart+GroundWaveSlots; ++Slot)
        {
            if (Particles[Slot].Life > 0.f) continue;
            auto& P=Particles[Slot]; P=FParticle();
            P.Born=Now; P.Life=.32f; P.Position=Origin;
            P.Rotation=FRotationMatrix::MakeFromZX(Normal, Heading).Rotator();
            P.Size=FVector(Radius*2.f, Radius*2.f, 100.f);
            P.Color=FLinearColor(.65f,.62f,.56f); P.Opacity=.52f;
            P.Variation=FMath::Cos(FMath::DegreesToRadians(HalfAngle));
            ++ActiveParticles;
            break;
        }
    // Dust shares the original 24 slots and the global particle budget. Spawn
    // on sampled ground inside the attack sector; skip walls and missing floor.
    const int32 Count=Distance<1800.f ? 8 : 4;
    constexpr int32 DustStart=SparkSlots;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Mutant3LandingDust), false);
    Params.AddIgnoredActor(ViewCamera->GetOwner());
    if (Source) Params.AddIgnoredActor(Source);
    for (int32 I=0; I<Count && ActiveParticles<MaxActiveParticles; ++I)
    {
        int32 Slot=INDEX_NONE;
        for (int32 J=DustStart; J<DustStart+DustSlots; ++J)
            if (Particles[J].Life<=0.f) {Slot=J;break;}
        if (Slot==INDEX_NONE) break;
        const float Yaw=FMath::Lerp(-HalfAngle*.88f, HalfAngle*.88f, (I+.5f)/Count);
        const FVector Direction=Heading.RotateAngleAxis(Yaw, Normal);
        const FVector Point=Ground.ImpactPoint+Direction*Radius*FMath::FRandRange(.18f,.68f);
        FHitResult Floor, Wall;
        if (GetWorld()->LineTraceSingleByChannel(Wall, Origin+Normal*15.f, Point+Normal*18.f, ECC_Visibility, Params)) continue;
        if (!GetWorld()->LineTraceSingleByChannel(Floor, Point+Normal*55.f, Point-Normal*90.f, ECC_Visibility, Params) ||
            FVector::DotProduct(Floor.ImpactNormal, Normal)<.6f || Cast<APawn>(Floor.GetActor())) continue;
        auto& P=Particles[Slot]; P=FParticle();
        P.Born=Now; P.Life=FMath::FRandRange(.38f,.52f);
        P.Position=Floor.ImpactPoint+Floor.ImpactNormal*12.f;
        P.Velocity=Direction*FMath::FRandRange(65.f,115.f)+Floor.ImpactNormal*45.f;
        P.Gravity=8.f; P.Size=FVector(FMath::FRandRange(38.f,56.f));
        P.Color=FLinearColor(.49f,.46f,.40f); P.Opacity=.34f;
        P.Rotation.Roll=FMath::FRandRange(-180.f,180.f);
        ++ActiveParticles;
    }
}
