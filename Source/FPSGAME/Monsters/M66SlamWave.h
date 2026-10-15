#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M66SlamWave.generated.h"

class USceneComponent;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;

USTRUCT()
struct FM66GroundWaveState
{
    GENERATED_BODY()
    UPROPERTY() bool Ready=false;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() float Radius=400.f;
    UPROPERTY() float Seconds=.55f;
    UPROPERTY() TObjectPtr<UMaterialInterface> Material;
};

/** Short, server-owned ground wave. Visual front and damage share the same clock. */
UCLASS()
class FPSGAME_API AM66SlamWave : public AActor
{
    GENERATED_BODY()
public:
    AM66SlamWave();
    void Setup(float Damage,float Radius,float Seconds,float Stun,UMaterialInterface* Material,double StartedAt);
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    double Clock() const;
    void ApplyWave(float Radius);
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Origin;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Ring;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Dynamic;
    UPROPERTY(Replicated) FM66GroundWaveState Wave;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    float Damage=135.f,StunSeconds=2.f,PreviousRadius=0.f;
    bool bDamageFinished=false;
};
