#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BellowSacProjectile.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

/** A visible, ballistic membrane capsule. Contact arms a fuse; contact itself does no damage. */
UCLASS()
class FPSGAME_API ABellowSacProjectile : public AActor
{
    GENERATED_BODY()
public:
    ABellowSacProjectile();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    void Launch(APawn* Source, FVector LaunchVelocity, float Damage, float Radius, float Fuse,
        UStaticMesh* SacMesh, UStaticMesh* RingMesh, UMaterialInterface* Material, UMaterialInterface* RingMaterial);
    static bool Sweep(UWorld* World, const AActor* Ignore, const AActor* Shooter,
        const FVector& Start, const FVector& End, float Radius, FHitResult& Hit, const AActor* IntendedTarget = nullptr);
    bool IsSpent() const { return BurstAt >= 0.; }
    bool IsArmed() const { return ContactAt >= 0.; }
    float GetBlastRadius() const { return BlastRadius; }
    float FuseRemaining() const;
    float FuseProgress() const;
    bool ExposureTo(APawn* Player, float& Distance) const;
    static constexpr float CollisionRadius = 8.f;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UDynamicMeshComponent> WarningRing;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UInstancedStaticMeshComponent> Fragments;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UAudioComponent> PressureAudio;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<UStaticMesh> CapsuleMesh;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<UStaticMesh> TelegraphMesh;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<UMaterialInterface> CapsuleMaterial;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<UMaterialInterface> TelegraphMaterial;
    UPROPERTY(Replicated) float BlastRadius = 140.f;
    UPROPERTY(Replicated) float FuseSeconds = .65f;
    UPROPERTY(Replicated) FVector SurfaceNormal = FVector::UpVector;
    UPROPERTY(Replicated) FVector ContactPoint = FVector::ZeroVector;
    UPROPERTY(Replicated) bool bSceneContact = false;
    UPROPERTY(Replicated) double ContactAt = -1.;
    UPROPERTY(Replicated) double BurstAt = -1.;
    UFUNCTION() void OnRep_Visuals();
    FVector Velocity = FVector::ZeroVector;
    TWeakObjectPtr<AController> DamageController;
    TWeakObjectPtr<AActor> DamageSource;
    float BlastDamage = 24.f;
    UPROPERTY(Replicated) double BornAt = 0.;
    bool bFragmentsCreated = false;
    bool bFlightSoundStarted = false, bContactPresented = false, bBurstPresented = false;
    bool bWarningSurfaceBuilt = false;
    double Clock() const;
    void Rupture();
    void Present();
    static bool IsWarningSceneSurface(const FHitResult& Hit);
    void BuildWarningSurface();
};
