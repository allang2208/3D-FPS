#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Components/ActorComponent.h"
#include "PoisonMaggotProjectile.generated.h"
class UStaticMeshComponent; class APoisonMaggotMonster;
/** Swept visible venom droplet; one authoritative collision and no homing. */
UCLASS()
class FPSGAME_API APoisonMaggotProjectile : public AActor
{
 GENERATED_BODY()
public:
 APoisonMaggotProjectile();
 void Launch(APoisonMaggotMonster* Source,FVector Direction,float Speed,float Range,float Damage,float Chance);
 virtual void Tick(float Dt) override;
 UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Visual;
private:
 TWeakObjectPtr<APoisonMaggotMonster> Shooter;
 FVector Velocity;
 float Remaining=0,HitDamage=0,PoisonChance=0;
};
/** Player poison: first tick at one second, a layer decays every five seconds. */
UCLASS(ClassGroup=Combat,meta=(BlueprintSpawnableComponent))
class FPSGAME_API UMaggotPoisonComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UMaggotPoisonComponent();
 void AddStack(APoisonMaggotMonster* Source);
 virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick) override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Poison") int32 Stacks=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Poison") int32 TicksApplied=0;
private:
 TWeakObjectPtr<AController> DamageInstigator;
 TWeakObjectPtr<AActor> DamageSource;
 float NextTick=1,DecayLeft=5;
};
