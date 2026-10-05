#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M08AirCannonProjectile.generated.h"

class ALurkerM08Monster;
class UStaticMeshComponent;

/** Finite swept pressure wave: one physical impact, never a homing projectile. */
UCLASS()
class FPSGAME_API AM08AirCannonProjectile : public AActor
{
    GENERATED_BODY()
public:
    AM08AirCannonProjectile();
    void Launch(ALurkerM08Monster* Source, const FVector& Direction, const FTransform& MuzzleFrame);
    virtual void Tick(float Dt) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION() void OnRep_Visuals();
    UFUNCTION() void OnRep_Impact();
    void Impact(const FHitResult& Hit);
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Rings;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<class UStaticMesh> RingMesh;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<class UMaterialInterface> RingMaterial;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<class USoundBase> ReleaseSound;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) TObjectPtr<class USoundAttenuation> SoundAttenuation;
    UPROPERTY(ReplicatedUsing=OnRep_Impact) bool bSpent = false;
    TWeakObjectPtr<ALurkerM08Monster> Shooter;
    FVector Velocity = FVector::ZeroVector;
    float Remaining = 0.f, Damage = 0.f, StunSeconds = 3.f, Age = 0.f, ImpactAge = 0.f;
    bool bSoundPlayed = false;
    UPROPERTY(ReplicatedUsing=OnRep_Visuals) FTransform EmissionFrame;
};
