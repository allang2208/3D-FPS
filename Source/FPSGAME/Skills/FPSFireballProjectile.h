#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FireballTypes.h"
#include "FPSFireballProjectile.generated.h"
class UFPSFireballComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USphereComponent;
class USoundBase;
class UMaterialInterface;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInstanceDynamic;

UCLASS()
class FPSGAME_API AFPSFireballProjectile : public AActor
{
    GENERATED_BODY()
public:
    AFPSFireballProjectile();
    void Prepare(UFPSFireballComponent* Ability,APawn* Caster,const FFireballCast& Snapshot,UNiagaraSystem* CoreFX,UNiagaraSystem* TrailFX,UNiagaraSystem* ImpactFX,UMaterialInterface* WaveMaterial,USoundBase* HitSound);
    void Launch(const FVector& AimPoint);
    bool IsFlying() const { return bFlying; }
    /** Hold-to-preview: red segment from the hovering orb to its predicted contact. */
    void SetAimPreviewActive(bool bActive);
    bool IsAimPreviewActive() const {return bAimPreview;}
    static FVector HoverPosition(APawn* Caster);
    virtual void Tick(float Delta) override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Core;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Trail;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> Explosion;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> Wave;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    TWeakObjectPtr<UFPSFireballComponent> Source;
    TWeakObjectPtr<APawn> Shooter;
    FFireballCast Cast;
    FVector Velocity=FVector::ZeroVector;
    /** Ballistic launch state: the flight and the preview share this integration exactly. */
    FVector LaunchPosition=FVector::ZeroVector,LaunchVelocity=FVector::ZeroVector;
    TArray<FVector> PreviewPoints;
    bool bWaterContact=false;
    float Age=0,Distance=0,FlightAge=0,ImpactAge=0,ImpactLightPeak=0;
    bool bFlying=false,bFinished=false;
    bool bAimPreview=false;
    UPROPERTY(Transient) TObjectPtr<class ULineBatchComponent> AimPreviewLines;
    void UpdateFlightFX(const FVector& PreviousPosition);
    void RefreshAimPreview();
    void Explode(const FHitResult* Hit);
};

/** Short, world-depth-tested shockwave. Its visual lifetime is independent of damage. */
UCLASS()
class FPSGAME_API AFireballShockwave : public AActor
{
    GENERATED_BODY()
public:
    AFireballShockwave();
    void Setup(UMaterialInterface* Material,float Radius,bool bSurfaceHit);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Dynamic;
    UPROPERTY() TObjectPtr<UStaticMesh> AirShell;
    float Age=0,MaxRadius=100;
};
