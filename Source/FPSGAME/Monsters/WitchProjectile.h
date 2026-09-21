#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Skills/EnemyAttackDamage.h"
#include "WitchProjectile.generated.h"

class AWitchMonster;
class UStaticMeshComponent;

UCLASS()
class FPSGAME_API UWitchMagicDamage : public UEnemyRangedDamage { GENERATED_BODY() };

/** One swept magic bolt or arcing bottle; a landed bottle owns its timed pool. */
UCLASS()
class FPSGAME_API AWitchProjectile : public AActor
{
    GENERATED_BODY()
public:
    AWitchProjectile();
    void Launch(AWitchMonster* Source, bool Bottle, FVector Destination, float Speed, float Damage, float Radius);
    virtual void Tick(float Delta) override;
private:
    void Land(FVector Position, FVector Normal);
    void Pulse();
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
    TWeakObjectPtr<AWitchMonster> Shooter;
    FVector Origin = FVector::ZeroVector, Goal = FVector::ZeroVector, Velocity = FVector::ZeroVector;
    bool bBottle = false, bPool = false;
    float Age = 0, HitDamage = 0, PoolRadius = 200.f, NextPulse = .5f;
};
