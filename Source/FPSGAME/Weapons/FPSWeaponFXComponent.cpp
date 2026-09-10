#include "FPSWeaponFXComponent.h"
#include "../FPSGAMECharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace WeaponFX
{
    enum : uint8 { FlashCore, FlashTongue, Smoke, Spark, Casing, Dust };
    const FLinearColor Flame(1.0f, 0.42f, 0.075f);
    const FLinearColor HotCore(1.0f, 0.76f, 0.27f);
    constexpr double SmokePeriod = 0.11;
    constexpr float SmokeMaxLifetime = 1.25f;
    constexpr float HeatThreshold = 0.10f;
    constexpr float HeatCoolingRate = 0.28f;
    constexpr float SmokeDrag = 1.3f;
}

UFPSWeaponFXComponent::UFPSWeaponFXComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    SetIsReplicatedByDefault(false);
    // Default object references retain the owned materials/geometry for cooking.
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Card(TEXT("/Engine/BasicShapes/Plane.Plane"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Flash(TEXT("/Game/Weapons/GunplayFX/M_GunFlash_Exposure.M_GunFlash_Exposure"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Smoke(TEXT("/Game/Weapons/GunplayFX/M_GunSmoke.M_GunSmoke"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Brass(TEXT("/Game/Weapons/GunplayFX/M_CasingBrass.M_CasingBrass"));
    CardMesh = Card.Object;
    CylinderMesh = Cylinder.Object;
    FlashMaterial = Flash.Object;
    SmokeMaterial = Smoke.Object;
    BrassMaterial = Brass.Object;
}

void UFPSWeaponFXComponent::Initialize(USkeletalMeshComponent* InWeaponMesh, UCameraComponent* InCamera)
{
    if (WeaponMesh) RemoveTickPrerequisiteComponent(WeaponMesh);
    StopEmission();
    for (FFPSWeaponFXParticle& P : Particles) Release(P);
    WeaponMesh = InWeaponMesh;
    Camera = InCamera;
    bReady = false;
    if (!GetWorld() || GetWorld()->GetNetMode() == NM_DedicatedServer || !WeaponMesh || !Camera) return;
    AddTickPrerequisiteComponent(WeaponMesh);
    bReady = CardMesh && CylinderMesh && FlashMaterial && SmokeMaterial && BrassMaterial
        && WeaponMesh->DoesSocketExist(MuzzleSocket) && WeaponMesh->DoesSocketExist(EjectSocket);
    if (!bReady)
    {
        UE_LOG(LogTemp, Error, TEXT("GUNPLAY_FX_NOT_READY materials=%d muzzle=%d eject=%d. Run Tools/AssetPipeline/build_gunplay_fx.py."),
            !!(FlashMaterial && SmokeMaterial && BrassMaterial), WeaponMesh->DoesSocketExist(MuzzleSocket), WeaponMesh->DoesSocketExist(EjectSocket));
        return;
    }
    if (!FlashLight)
    {
        FlashLight = NewObject<UPointLightComponent>(GetOwner(), TEXT("WeaponMuzzleLight"));
        GetOwner()->AddInstanceComponent(FlashLight);
        FlashLight->SetMobility(EComponentMobility::Movable);
        FlashLight->SetCastShadows(false);
        FlashLight->SetIntensityUnits(ELightUnits::Lumens);
        FlashLight->SetAttenuationRadius(125.0f);
        FlashLight->SetLightColor(FLinearColor(1.0f, 0.56f, 0.20f));
        FlashLight->SetVisibility(false);
        FlashLight->RegisterComponent();
    }
    Particles.Reserve(MaxParticles);
    PreviousMuzzlePosition = MuzzleLocation();
    PreviousMuzzleForward = MuzzleForward();
    UE_LOG(LogTemp, Display, TEXT("GUNPLAY_FX_READY muzzle=%s eject=%s max_particles=%d"), *MuzzleSocket.ToString(), *EjectSocket.ToString(), MaxParticles);
}

FVector UFPSWeaponFXComponent::MuzzleLocation() const { if(const auto* C=Cast<AFPSGAMECharacter>(GetOwner()))return C->GetEffectiveMuzzleLocation();return WeaponMesh->GetSocketLocation(MuzzleSocket); }

FVector UFPSWeaponFXComponent::MuzzleForward() const
{
    if(const auto* C=Cast<AFPSGAMECharacter>(GetOwner()))return C->GetEffectiveMuzzleForward();
    // Imported WPN local Y lies along the bore; mirrored source rigs need a sign correction.
    FVector Forward = WeaponMesh->GetSocketQuaternion(MuzzleSocket).GetAxisY();
    if (FVector::DotProduct(Forward, Camera->GetForwardVector()) < 0.0f) Forward *= -1.0f;
    return Forward.GetSafeNormal();
}

FFPSWeaponFXParticle* UFPSWeaponFXComponent::Acquire(uint8 Kind, UStaticMesh* Geometry, UMaterialInterface* BaseMaterial)
{
    FFPSWeaponFXParticle* Result = Particles.FindByPredicate([](const FFPSWeaponFXParticle& P) { return !P.bActive; });
    if (!Result)
    {
        if (Particles.Num() >= MaxParticles) return nullptr;
        Result = &Particles.AddDefaulted_GetRef();
        Result->Mesh = NewObject<UStaticMeshComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Result->Mesh);
        Result->Mesh->SetMobility(EComponentMobility::Movable);
        Result->Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Result->Mesh->SetGenerateOverlapEvents(false);
        Result->Mesh->SetCastShadow(false);
        Result->Mesh->bReceivesDecals = false;
        Result->Mesh->SetCanEverAffectNavigation(false);
        Result->Mesh->RegisterComponent();
    }
    Result->Mesh->SetStaticMesh(Geometry);
    if (!Result->Material || Result->Material->Parent != BaseMaterial)
        Result->Material = UMaterialInstanceDynamic::Create(BaseMaterial, Result->Mesh);
    Result->Mesh->SetMaterial(0, Result->Material);
    Result->Mesh->SetVisibility(true);
    Result->Material->SetScalarParameterValue(TEXT("Opacity"), 1.0f);
    Result->Material->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.0f, 50.0f));
    Result->Material->SetVectorParameterValue(TEXT("Tint"), WeaponFX::Flame);
    Result->Material->SetScalarParameterValue(TEXT("Emission"), 3.0f);
    Result->Position = FVector::ZeroVector;
    Result->Velocity = FVector::ZeroVector;
    Result->Acceleration = FVector::ZeroVector;
    Result->Rotation = FRotator::ZeroRotator;
    Result->Spin = FRotator::ZeroRotator;
    Result->Size = FVector::OneVector;
    Result->Age = 0.0f;
    Result->BirthFrame = GFrameCounter;
    Result->Lifetime = 1.0f;
    Result->Opacity = 1.0f;
    Result->ForwardOffset = 0.0f;
    Result->Kind = Kind;
    Result->bActive = true;
    Result->bBounced = false;
    SetComponentTickEnabled(true);
    return Result;
}

void UFPSWeaponFXComponent::Release(FFPSWeaponFXParticle& P)
{
    P.bActive = false;
    if (P.Mesh) P.Mesh->SetVisibility(false);
}

void UFPSWeaponFXComponent::OnShot(bool bADS)
{
    if (!bReady) return;
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const float Suppression=Character&&Character->IsMuzzleSuppressed()?.12f:1.f;
    LastSuppression=Suppression;
    LastADSMultiplier = bADS ? 0.78f : 1.0f;
    const float Scale = FMath::Clamp(FlashScale, 0.0f, 2.0f) * LastADSMultiplier;
    for (int32 Layer = 0; Layer < 2; ++Layer)
    {
        if (FFPSWeaponFXParticle* P = Acquire(Layer == 0 ? WeaponFX::FlashCore : WeaponFX::FlashTongue, CardMesh, FlashMaterial))
        {
            P->Lifetime = Layer == 0 ? 0.045f : 0.065f;
            P->ForwardOffset = Layer == 0 ? 1.2f : 5.0f;
            // The bore is below the sight line: let a short outer lobe clear
            // the sight housing, while keeping its center translucent in ADS.
            P->Size = FVector(Layer == 0 ? 6.0f : 21.0f) * Scale;
            P->Rotation.Roll = FMath::FRandRange(-180.0f, 180.0f);
            P->Material->SetVectorParameterValue(TEXT("Tint"), Layer == 0 ? WeaponFX::HotCore : WeaponFX::Flame);
            P->Material->SetScalarParameterValue(TEXT("Emission"), Layer == 0 ? 5.0f : 3.0f);
            P->Opacity = (Layer == 0 ? 0.8f : 0.42f)*Suppression;
            P->Position = MuzzleLocation() + MuzzleForward() * P->ForwardOffset;
            ApplyParticleTransform(*P);
        }
    }
    for (int32 I = 0; I < (Suppression<1.f?0:2); ++I)
    {
        if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Spark, CardMesh, FlashMaterial))
        {
            P->Position = MuzzleLocation();
            P->Velocity = MuzzleForward() * FMath::FRandRange(270.0f, 480.0f) + FMath::VRand() * 75.0f;
            P->Acceleration = FVector(0.0f, 0.0f, -340.0f);
            P->Lifetime = FMath::FRandRange(0.075f, 0.13f);
            P->Size = FVector(0.30f, 1.6f, 1.0f) * LastADSMultiplier;
            ApplyParticleTransform(*P);
        }
    }
    if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Casing, CylinderMesh, BrassMaterial))
    {
        P->Position = WeaponMesh->GetSocketLocation(EjectSocket);
        P->Velocity = Camera->GetRightVector() * FMath::FRandRange(140.0f, 215.0f)
            + Camera->GetUpVector() * FMath::FRandRange(75.0f, 125.0f) - MuzzleForward() * 30.0f;
        P->Acceleration = FVector(0.0f, 0.0f, -650.0f);
        P->Size = FVector(0.80f, 0.80f, 2.6f);
        P->Spin = FRotator(400.0f, 650.0f, 100.0f);
        P->Lifetime = 1.25f;
        P->Material->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.42f, 0.25f, 0.075f));
        ApplyParticleTransform(*P);
    }
    PendingHeat = FMath::Min(1.0f, PendingHeat + 0.18f);
    SpawnSmoke(true, 0.0f, MuzzleLocation(), MuzzleForward(), FMath::Min(1.0f, BarrelHeat + PendingHeat));
    FlashTime = 0.045f;
    FlashBirthFrame = GFrameCounter;
    FlashLight->SetWorldLocation(MuzzleLocation() + MuzzleForward() * 2.0f);
    FlashLight->SetIntensity(950.0f * Scale * LastSuppression);
    FlashLight->SetVisibility(Scale > 0.0f);
    SetComponentTickEnabled(true);
}

void UFPSWeaponFXComponent::SpawnSmoke(bool bImmediate, float InitialAge, const FVector& BirthPosition,
    const FVector& BirthForward, float HeatAtBirth)
{
    const float Lifetime = FMath::FRandRange(0.80f, WeaponFX::SmokeMaxLifetime);
    if (InitialAge >= Lifetime) return; // Do not occupy the pool with already expired catch-up particles.
    if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Smoke, CardMesh, SmokeMaterial))
    {
        P->Position = BirthPosition + BirthForward * 2.0f;
        P->Velocity = BirthForward * (bImmediate ? 36.0f : 10.0f) + FVector(3.5f, -2.0f, 22.0f);
        P->Acceleration = FVector(0.8f, 0.0f, 7.0f);
        P->Lifetime = Lifetime;
        P->Size = FVector(bImmediate ? 9.0f : 7.0f);
        P->Rotation.Roll = FMath::FRandRange(-180.0f, 180.0f);
        P->Spin.Roll = FMath::FRandRange(-25.0f, 25.0f);
        P->Opacity = FMath::Clamp(SmokeOpacity, 0.0f, 1.0f) * FMath::Lerp(0.32f, 1.0f, HeatAtBirth) * LastADSMultiplier;
        P->Material->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.24f, 0.26f, 0.28f));
        P->Material->SetScalarParameterValue(TEXT("Emission"), 0.12f);
        AdvanceParticle(*P, InitialAge);
        ApplyParticleTransform(*P);
    }
}

void UFPSWeaponFXComponent::OnImpact(const FHitResult& Hit)
{
    if (!bReady || !Hit.bBlockingHit) return;
    FString SurfaceName;
    if (Hit.Component.IsValid() && Hit.Component->GetMaterial(0)) SurfaceName = Hit.Component->GetMaterial(0)->GetName();
    const bool bMetal = (Hit.Component.IsValid() && Hit.Component->ComponentHasTag(TEXT("Metal"))) || SurfaceName.Contains(TEXT("Metal"), ESearchCase::IgnoreCase);
    const bool bWood = SurfaceName.Contains(TEXT("Wood"), ESearchCase::IgnoreCase);
    const FVector Normal = Hit.ImpactNormal.GetSafeNormal();
    const int32 Count = bMetal ? 4 : 2;
    for (int32 I = 0; I < Count; ++I)
    {
        if (FFPSWeaponFXParticle* P = Acquire(bMetal ? WeaponFX::Spark : WeaponFX::Dust, CardMesh, bMetal ? FlashMaterial : SmokeMaterial))
        {
            P->Position = Hit.ImpactPoint + Normal * 1.0f;
            P->Velocity = Normal * FMath::FRandRange(40.0f, bMetal ? 220.0f : 65.0f) + FMath::VRand() * 35.0f;
            P->Acceleration = FVector(0.0f, 0.0f, bMetal ? -430.0f : -20.0f);
            P->Lifetime = bMetal ? 0.22f : 0.48f;
            P->Size = bMetal ? FVector(0.4f, 2.2f, 1.0f) : FVector(4.0f);
            P->Opacity = bMetal ? 0.85f : 0.32f;
            P->Material->SetVectorParameterValue(TEXT("Tint"), bMetal ? WeaponFX::HotCore : bWood ? FLinearColor(0.25f,0.17f,0.10f) : FLinearColor(0.30f,0.29f,0.26f));
            P->Material->SetScalarParameterValue(TEXT("Emission"), bMetal ? 3.0f : 0.0f);
            ApplyParticleTransform(*P);
        }
    }
}

void UFPSWeaponFXComponent::ApplyParticleTransform(FFPSWeaponFXParticle& P)
{
    const float Life = FMath::Clamp(P.Age / P.Lifetime, 0.0f, 1.0f);
    FVector Size = P.Size;
    float Alpha = P.Opacity * (1.0f - Life);
    FRotator Rotation = P.Rotation;
    if (P.Kind != WeaponFX::Casing)
    {
        Rotation = FRotationMatrix::MakeFromZ(Camera->GetComponentLocation() - P.Position).Rotator();
        const FQuat Billboard = Rotation.Quaternion() * FQuat(FVector::UpVector, FMath::DegreesToRadians(P.Rotation.Roll));
        Rotation = Billboard.Rotator();
        if (P.Kind == WeaponFX::Smoke || P.Kind == WeaponFX::Dust)
        {
            Size *= 0.6f + Life * 2.4f;
            Alpha *= FMath::Min(1.0f, Life * 9.0f);
        }
        else Alpha *= 1.0f - Life;
        P.Material->SetScalarParameterValue(TEXT("Opacity"), Alpha);
    }
    P.Mesh->SetWorldLocationAndRotation(P.Position, Rotation);
    P.Mesh->SetWorldScale3D(Size / 100.0f);
}

void UFPSWeaponFXComponent::AdvanceParticle(FFPSWeaponFXParticle& P, float DeltaTime)
{
    if (DeltaTime <= 0.0f) return;
    if (P.Age + DeltaTime >= P.Lifetime) { Release(P); return; }
    // Only casings need swept collision substeps. Their <=1.25 s lifetime bounds
    // this loop; even the capped case consumes the entire interval, never discarding time.
    const int32 Steps = P.Kind == WeaponFX::Casing
        ? FMath::Clamp(FMath::CeilToInt(DeltaTime / 0.025f), 1, 64) : 1;
    const float Step = DeltaTime / Steps;
    for (int32 I = 0; I < Steps; ++I)
    {
        if (P.Age + Step >= P.Lifetime) { Release(P); return; }
        P.Age += Step;
        const FVector OldPosition = P.Position;
        if (P.Kind == WeaponFX::Smoke || P.Kind == WeaponFX::Dust)
        {
            // Exact solution of dv/dt = Acceleration - Drag * Velocity.
            const float Decay = FMath::Exp(-WeaponFX::SmokeDrag * Step);
            const float Travel = (1.0f - Decay) / WeaponFX::SmokeDrag;
            P.Position += P.Velocity * Travel + P.Acceleration / WeaponFX::SmokeDrag * (Step - Travel);
            P.Velocity = P.Velocity * Decay + P.Acceleration * Travel;
        }
        else if (P.Kind != WeaponFX::FlashCore && P.Kind != WeaponFX::FlashTongue)
        {
            P.Position += P.Velocity * Step + P.Acceleration * (0.5f * Step * Step);
            P.Velocity += P.Acceleration * Step;
        }
        P.Rotation += P.Spin * Step;
        if (P.Kind == WeaponFX::Casing && !P.bBounced)
        {
            FHitResult Bounce;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(WeaponCasing), false, GetOwner());
            if (GetWorld()->LineTraceSingleByChannel(Bounce, OldPosition, P.Position, ECC_Visibility, Params))
            {
                const float AfterHit = Step * (1.0f - FMath::Clamp(Bounce.Time, 0.0f, 1.0f));
                P.Position = Bounce.ImpactPoint + Bounce.ImpactNormal * 0.8f;
                const FVector HitVelocity = P.Velocity - P.Acceleration * AfterHit;
                P.Velocity = FMath::GetReflectionVector(HitVelocity, Bounce.ImpactNormal) * 0.24f;
                // Consume the post-impact part of this substep as well.
                P.Position += P.Velocity * AfterHit + P.Acceleration * (0.5f * AfterHit * AfterHit);
                P.Velocity += P.Acceleration * AfterHit;
                P.Rotation -= P.Spin * (AfterHit * 0.70f);
                P.Spin *= 0.30f;
                P.bBounced = true;
                P.Lifetime = FMath::Min(P.Lifetime, P.Age - AfterHit + 0.25f);
                if (P.Age >= P.Lifetime) { Release(P); return; }
            }
        }
    }
}

void UFPSWeaponFXComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!bReady || !IsValid(WeaponMesh) || !IsValid(Camera))
    {
        StopEmission();
        for (FFPSWeaponFXParticle& P : Particles) Release(P);
        SetComponentTickEnabled(false);
        return;
    }
    DeltaTime = FMath::Max(0.0f, DeltaTime);
    if (FlashBirthFrame != GFrameCounter) FlashTime = FMath::Max(0.0f, FlashTime - DeltaTime);
    if (FlashTime > 0.0f)
    {
        FlashLight->SetWorldLocation(MuzzleLocation() + MuzzleForward() * 2.0f);
        FlashLight->SetIntensity(950.0f * FMath::Clamp(FlashScale, 0.0f, 2.0f) * LastADSMultiplier * LastSuppression * FMath::Square(FlashTime / 0.045f));
    }
    else FlashLight->SetVisibility(false);
    for (FFPSWeaponFXParticle& P : Particles)
    {
        if (!P.bActive) continue;
        // An OnShot/OnImpact particle was born at this frame's current time.
        // Both its age and motion start next Tick, preserving a zero-age first display.
        if (P.BirthFrame != GFrameCounter) AdvanceParticle(P, DeltaTime);
        if (!P.bActive) continue;
        if (P.Kind == WeaponFX::FlashCore || P.Kind == WeaponFX::FlashTongue)
            P.Position = MuzzleLocation() + MuzzleForward() * P.ForwardOffset;
        ApplyParticleTransform(P);
    }

    const FVector CurrentMuzzlePosition = MuzzleLocation();
    const FVector CurrentMuzzleForward = MuzzleForward();
    const float HeatAtStart = BarrelHeat;
    const double HotDelta = FMath::Clamp((static_cast<double>(HeatAtStart) - WeaponFX::HeatThreshold)
        / WeaponFX::HeatCoolingRate, 0.0, static_cast<double>(DeltaTime));
    if (HotDelta > 0.0)
    {
        const double Total = SmokeClock + HotDelta;
        const int32 DueCount = FMath::FloorToInt((Total + 1.e-9) / WeaponFX::SmokePeriod);
        const double FirstOffset = WeaponFX::SmokePeriod - SmokeClock;
        // Skip history outside the maximum lifetime before iterating; at most
        // ceil(1.25 / 0.11) + 1 events can need a pool slot, even after a long hitch.
        const double SkippedHistory = FMath::Clamp(
            (DeltaTime - WeaponFX::SmokeMaxLifetime - FirstOffset) / WeaponFX::SmokePeriod, 0.0, static_cast<double>(DueCount));
        const int32 FirstVisible = FMath::CeilToInt(SkippedHistory);
        for (int32 I = FirstVisible; I < DueCount; ++I)
        {
            const double Offset = FirstOffset + I * WeaponFX::SmokePeriod;
            const float Age = FMath::Max(0.0f, DeltaTime - static_cast<float>(Offset));
            const float Fraction = DeltaTime > 0.0f ? FMath::Clamp(static_cast<float>(Offset) / DeltaTime, 0.0f, 1.0f) : 1.0f;
            // Socket history between samples is reconstructed linearly in world space.
            const FVector BirthPosition = FMath::Lerp(PreviousMuzzlePosition, CurrentMuzzlePosition, Fraction);
            FVector BirthForward = FMath::Lerp(PreviousMuzzleForward, CurrentMuzzleForward, Fraction).GetSafeNormal();
            if (BirthForward.IsNearlyZero()) BirthForward = CurrentMuzzleForward;
            const float BirthHeat = FMath::Max(WeaponFX::HeatThreshold,
                HeatAtStart - static_cast<float>(Offset) * WeaponFX::HeatCoolingRate);
            SpawnSmoke(false, Age, BirthPosition, BirthForward, BirthHeat);
        }
        SmokeClock = FMath::Max(0.0, Total - DueCount * WeaponFX::SmokePeriod);
    }
    const float CooledHeat = FMath::Max(0.0f, HeatAtStart - DeltaTime * WeaponFX::HeatCoolingRate);
    if (CooledHeat <= WeaponFX::HeatThreshold) SmokeClock = 0.0;
    // Heat added by this frame's shot is an endpoint event, not heat from the past interval.
    BarrelHeat = FMath::Min(1.0f, CooledHeat + PendingHeat);
    PendingHeat = 0.0f;
    PreviousMuzzlePosition = CurrentMuzzlePosition;
    PreviousMuzzleForward = CurrentMuzzleForward;
    if (BarrelHeat <= WeaponFX::HeatThreshold && FlashTime <= 0.0f && GetActiveParticleCount() == 0)
    {
        BarrelHeat = 0.0f;
        SmokeClock = 0.0;
        SetComponentTickEnabled(false);
    }
}

int32 UFPSWeaponFXComponent::GetActiveParticleCount() const
{
    int32 Count = 0;
    for (const FFPSWeaponFXParticle& P : Particles) if (P.bActive) ++Count;
    return Count;
}

void UFPSWeaponFXComponent::StopEmission()
{
    BarrelHeat = PendingHeat = FlashTime = 0.0f;
    SmokeClock = 0.0;
    if (FlashLight) FlashLight->SetVisibility(false);
}

void UFPSWeaponFXComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    StopEmission();
    for (FFPSWeaponFXParticle& P : Particles) if (P.Mesh) P.Mesh->DestroyComponent();
    Particles.Reset();
    if (FlashLight) FlashLight->DestroyComponent();
    Super::EndPlay(EndPlayReason);
}
