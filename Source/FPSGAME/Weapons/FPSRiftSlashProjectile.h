#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "FPSRiftSlashProjectile.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UNiagaraComponent;
class UNiagaraSystem;

/** One charged sword release. Pierces bodies once each; world cover ends flight. */
UCLASS(NotBlueprintable, Transient)
class FPSGAME_API AFPSRiftSlashProjectile : public AActor
{
    GENERATED_BODY()
public:
    AFPSRiftSlashProjectile();
    void Launch(const FTransform& Aim,float Damage,float RangeCM,float SpeedCM,
        const FColdSteelSkillShot& Snapshot,UStaticMesh* Mesh,UMaterialInterface* Material,UNiagaraSystem* Particles);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> Root;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Wake;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Motes;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BladeMaterial;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> WakeMaterial;
    FColdSteelSkillShot Shot;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    FVector Direction=FVector::ForwardVector;
    float HitDamage=0.f,Remaining=0.f,Speed=1800.f,Age=0.f,FadeAge=0.f,HitGlow=0.f;
    bool bFinished=false;
    void Advance(float Distance);
    void FinishFlight();
};
