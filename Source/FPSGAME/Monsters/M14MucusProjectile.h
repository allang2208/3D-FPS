#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M14MucusProjectile.generated.h"

class ASpiralPillarM14;
class UStaticMeshComponent;
class UMaterialInterface;
class USoundBase;

/** One visible nonhoming shot; shared liquid FX are cosmetic only. */
UCLASS()
class FPSGAME_API AM14MucusProjectile : public AActor
{
    GENERATED_BODY()
public:
    AM14MucusProjectile();
    void Launch(ASpiralPillarM14* Source,const FVector& Direction,float Speed,float Range,float Damage,
        float SlowPercent,float SlowSeconds,UMaterialInterface* Shell,UMaterialInterface* Core);
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> LiquidCore;
    UPROPERTY(ReplicatedUsing=OnRep_Materials) TObjectPtr<UMaterialInterface> ShellMaterial;
    UPROPERTY(ReplicatedUsing=OnRep_Materials) TObjectPtr<UMaterialInterface> CoreMaterial;
    UFUNCTION() void OnRep_Materials();
    UFUNCTION(NetMulticast,Unreliable) void ShowImpact(const FHitResult& Hit,FVector IncomingVelocity);
    void UpdateLiquidVisual(float Dt,const FVector& Start,const FVector& End);
    TWeakObjectPtr<ASpiralPillarM14> Shooter;
    UPROPERTY(EditDefaultsOnly,Category="M14|Audio") TObjectPtr<USoundBase> ImpactSound;
    FVector Velocity=FVector::ZeroVector,PreviousVisualPosition=FVector::ZeroVector;
    float Remaining=0.f,HitDamage=0.f,SlowAmount=0.f,SlowDuration=0.f,VisualAge=0.f,TrailRemainder=0.f;
    int32 TrailSamples=0;
    bool bMuzzleShown=false;
};
