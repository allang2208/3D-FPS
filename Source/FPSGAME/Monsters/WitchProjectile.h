#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Skills/EnemyAttackDamage.h"
#include "WitchProjectile.generated.h"

class AWitchMonster;
class UStaticMesh;
class UStaticMeshComponent;
class UDecalComponent;
class UMaterialInterface;

UCLASS()
class FPSGAME_API UWitchMagicDamage : public UEnemyRangedDamage { GENERATED_BODY() };

USTRUCT()
struct FWitchProjectilePresentation
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UStaticMesh> Mesh=nullptr;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> Materials;
    UPROPERTY() FTransform VisualTransform;
    UPROPERTY() bool Bottle=false;
    UPROPERTY() bool Pool=false;
    UPROPERTY() float Radius=200.f;
    UPROPERTY() float Phase=0.f;
    UPROPERTY() FVector Velocity=FVector::ZeroVector;
    UPROPERTY() FVector Point=FVector::ZeroVector;
    UPROPERTY() FVector Normal=FVector::UpVector;
    UPROPERTY() double PoolStarted=0.;
    UPROPERTY() TArray<float> Reach;
};

/** One swept magic bolt or arcing bottle; a landed bottle owns its timed pool. */
UCLASS()
class FPSGAME_API AWitchProjectile : public AActor
{
    GENERATED_BODY()
public:
    AWitchProjectile();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    void Launch(AWitchMonster* Source, bool Bottle, FVector Destination, float Speed, float Damage, float Radius);
    virtual void Tick(float Delta) override;
private:
    void Land(const FHitResult& Contact, const FVector& IncomingVelocity);
    void BuildPoolVisual(const FVector& Position,const FVector& Normal);
    void PublishPresentation();
    UFUNCTION() void OnRep_Presentation();
    UFUNCTION(NetMulticast,Unreliable) void MulticastImpact(const FHitResult& Hit,FVector_NetQuantize Incoming,bool BottleImpact);
    UPROPERTY(ReplicatedUsing=OnRep_Presentation) FWitchProjectilePresentation NetworkPresentation;
    FVector LastVisualLocation=FVector::ZeroVector;
    bool bHasVisualLocation=false;
    void Pulse();
    void BuildPoolFootprint();
    void RefreshPoolFootprint();
    float SamplePoolSector(int32 Index) const;
    void PushPoolFootprint();
    float PoolBoundary(const FVector& Position) const;
    void UpdateLiquidVisual(float DeltaTime, const FVector& Start, const FVector& End);
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> LiquidCore;
    UPROPERTY() TObjectPtr<UMaterialInterface> PoolMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> BottleLiquidMaterial;
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> PoolSurface;
    TWeakObjectPtr<AWitchMonster> Shooter;
    FVector Origin = FVector::ZeroVector, Goal = FVector::ZeroVector, Velocity = FVector::ZeroVector;
    FQuat BottleReleaseRotation = FQuat::Identity;
    FVector BottleSpinAxis = FVector::RightVector;
    bool bBottle = false, bPool = false;
    float Age = 0, HitDamage = 0, PoolRadius = 200.f, NextPulse = .5f;
    float LiquidAge = 0.f, LiquidPhase = 0.f, NextTrail = 0.f;
    float NextPoolVapor = .35f;
    int32 TrailCount = 0;
    float PoolReach[16] = {};
    FVector PoolSlope=FVector::UpVector;
    int32 FootprintCursor=0;
    float NextFootprintUpdate=.10f;
};
