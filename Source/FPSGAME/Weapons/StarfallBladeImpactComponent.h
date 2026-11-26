#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StarfallBladeImpactComponent.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UPointLightComponent;
class USoundBase;

/** Cosmetic-only Starfall burst. Damage and replication remain on the projectile. */
UCLASS()
class FPSGAME_API UStarfallBladeImpactComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UStarfallBladeImpactComponent();
    void Prepare(UStaticMeshComponent* InBlade, UPointLightComponent* InLight);
    bool PlayImpact(const FHitResult& Hit, const FVector& Incoming, float Radius);
    virtual void TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* Function) override;
    static constexpr float Lifetime = 1.45f;

private:
    UPROPERTY() TObjectPtr<UStaticMesh> CrystalMesh;
    UPROPERTY() TObjectPtr<UStaticMesh> PlaneMesh;
    UPROPERTY() TObjectPtr<UStaticMesh> ShellMesh;
    UPROPERTY() TObjectPtr<UStaticMesh> WispMesh;
    UPROPERTY() TObjectPtr<UMaterialInterface> CrystalMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> LayerMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> ShellMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> BladeMaterial;
    UPROPERTY() TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Crystals;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Wisps;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Surface;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Shell;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> Light;
    struct FParticle
    {
        FTransform Initial;
        FVector Velocity;
        FVector SpinAxis;
        float Spin = 0.f;
        float Delay = 0.f;
        float Duration = 1.f;
        float Growth = 0.f;
    };
    TArray<FParticle> CrystalParticles;
    TArray<FParticle> WispParticles;
    FVector Origin = FVector::ZeroVector;
    FVector Normal = FVector::UpVector;
    FQuat SurfaceRotation = FQuat::Identity;
    float Age = -1.f;
    float BlastRadius = 300.f;
    bool bSurfaceImpact = false;
};
