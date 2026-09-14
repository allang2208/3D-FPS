#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FPSImpactFXSubsystem.generated.h"

class UCameraComponent;
class UInstancedStaticMeshComponent;
class UDecalComponent;
class UAudioComponent;
class UMaterialInterface;
class UStaticMesh;
class USoundBase;
class UPrimitiveComponent;

enum class EFPSImpactSurface : uint8 { Metal, Wood, Stone, Dirt, Glass, Flesh, Unknown };

/** One cosmetic budget per world; hits/damage never depend on FX availability. */
UCLASS()
class FPSGAME_API UFPSImpactFXSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    UFPSImpactFXSubsystem();
    void SpawnImpact(const FHitResult& Hit, UCameraComponent* ViewCamera);
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override { return bReady && ActiveParticles > 0; }
    virtual TStatId GetStatId() const override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    static constexpr int32 SparkSlots = 48;
    static constexpr int32 DustSlots = 24;
    static constexpr int32 ChipSlots = 32;
    static constexpr int32 BloodMistSlots = 24;
    static constexpr int32 BloodDropSlots = 96;
    static constexpr int32 MaxActiveParticles = 192;
    static constexpr int32 ParticleSlots = SparkSlots + DustSlots + ChipSlots + BloodMistSlots + BloodDropSlots;
    static constexpr int32 ParticleGroups = 5;
    static constexpr int32 DecalSlots = 24;
    static constexpr int32 BloodDecalSlots = 48;
    static constexpr int32 VoiceSlots = 6;
    struct FParticle
    {
        FVector Position = FVector::ZeroVector, Velocity = FVector::ZeroVector;
        FVector Size = FVector::OneVector;
        FRotator Rotation = FRotator::ZeroRotator, Spin = FRotator::ZeroRotator;
        FLinearColor Color = FLinearColor::White;
        double Born = 0.;
        float Life = 0.f, Gravity = 0.f, Opacity = 0.f, Variation = 0.f;
        FVector LandingPoint = FVector::ZeroVector, LandingNormal = FVector::UpVector;
        bool bHasLandingPlane = false;
    };
    struct FRecentHit
    {
        TWeakObjectPtr<UPrimitiveComponent> Component;
        FVector Position = FVector::ZeroVector;
        double Time = -10.;
    };
    EFPSImpactSurface ResolveSurface(const FHitResult& Hit);
    EFPSImpactSurface SurfaceForObject(const UObject* Object);
    void AddParticle(int32 Group, const FVector& Position, const FVector& Normal,
        EFPSImpactSurface Surface, float DetailScale);
    void AddFleshBurst(const FHitResult& Hit, const FVector& Normal, bool Full, bool Far, const FHitResult* Ground);
    bool FindBloodLanding(const FHitResult& Hit, UCameraComponent* ViewCamera, double Now, FHitResult& Ground);
    void AddBloodStain(const FHitResult& Ground, const FVector& Origin, double Now);
    void AddDecal(const FHitResult& Hit, EFPSImpactSurface Surface, double Now);
    void PlayImpactSound(const FVector& Position, EFPSImpactSurface Surface, float Distance, double Now);

    UPROPERTY() TObjectPtr<UStaticMesh> PlaneMesh;
    UPROPERTY() TObjectPtr<UStaticMesh> ChipMesh;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> ParticleMaterials;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> DecalMaterials;
    UPROPERTY() TObjectPtr<UMaterialInterface> BloodStainMaterial;
    UPROPERTY() TArray<TObjectPtr<USoundBase>> Sounds;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Renderers;
    UPROPERTY(Transient) TArray<TObjectPtr<UDecalComponent>> Decals;
    UPROPERTY(Transient) TArray<TObjectPtr<UDecalComponent>> BloodDecals;
    UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> Voices;
    TWeakObjectPtr<UCameraComponent> Camera;
    TMap<TWeakObjectPtr<const UObject>, EFPSImpactSurface> SurfaceCache;
    EFPSImpactSurface SurfaceTypes[SurfaceType_Max] = {};
    FParticle Particles[ParticleSlots];
    TArray<FTransform> Transforms[ParticleGroups];
    FRecentHit RecentHits[16];
    double VoiceUntil[VoiceSlots] = {};
    double DecalUntil[DecalSlots] = {};
    double BloodDecalUntil[BloodDecalSlots] = {};
    double LastBudgetTime = 0., LastSoundTime = -10.;
    double LastBloodStainTime = -10.;
    FHitResult LastBloodLanding;
    FVector LastBloodOrigin = FVector::ZeroVector;
    TWeakObjectPtr<AActor> LastBloodVictim;
    double LastBloodLandingTime = -10.;
    uint64 BudgetFrame = 0;
    int32 FrameBursts = 0, RecentCursor = 0, DecalCursor = 0, ActiveParticles = 0;
    int32 BloodDecalCursor = 0;
    int32 LastSoundVariant[6] = {-1,-1,-1,-1,-1,-1};
    float BurstTokens = 8.f;
    bool bReady = false;
};
