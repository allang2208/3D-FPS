#pragma once

#include "CoreMinimal.h"
#include "Components/StaticMeshComponent.h"
#include "Subsystems/WorldSubsystem.h"
#include "../Building/ColdSteelDoor.h"
#include "WardBreakableGlass.generated.h"

class UNiagaraSystem;
class UNiagaraComponent;
class UAudioComponent;
class USoundBase;
class UMaterialInstanceDynamic;

/** One pane owns the obstacle. Cosmetic fragments never own query collision. */
UCLASS(ClassGroup=(Dungeon), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UWardBreakableGlass : public UStaticMeshComponent
{
    GENERATED_BODY()
public:
    UWardBreakableGlass();
    virtual void ReceiveComponentDamage(float DamageAmount, const FDamageEvent& DamageEvent,
        AController* EventInstigator, AActor* DamageCauser) override;
    void HandleDamage(float DamageAmount,const FDamageEvent& DamageEvent,AActor* DamageCauser);
    bool BreakAt(const FVector& HitPoint,const FVector& Direction);
    static bool BreakHit(const FHitResult& Hit,const FVector& Direction);
    static void BreakInRadius(UWorld* World,const FVector& Center,float Radius,AActor* DamageCauser);
    static UWardBreakableGlass* IntactPane(AActor* Actor);
    static FVector TargetPoint(AActor* Actor);
    UPROPERTY(EditAnywhere, Category="Glass") TObjectPtr<UStaticMesh> FractureMesh;
    UPROPERTY(EditAnywhere, Category="Glass") TObjectPtr<UMaterialInterface> FractureMaterial;
    UPROPERTY(EditAnywhere, Category="Glass") TObjectPtr<UNiagaraSystem> ImpactParticles;
    UPROPERTY(EditAnywhere, Category="Glass") TObjectPtr<USoundBase> BreakSound;
    /** Width, height, thickness in centimetres. The pane normal is local X. */
    UPROPERTY(EditAnywhere, Category="Glass") FVector PaneDimensions=FVector(142.f,250.f,1.2f);
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Glass") bool bBroken=false;
};

UCLASS()
class FPSGAME_API AWardGlassDoor : public AColdSteelDoor
{
    GENERATED_BODY()
public:
    AWardGlassDoor();
    virtual float TakeDamage(float DamageAmount,const FDamageEvent& DamageEvent,AController* EventInstigator,AActor* DamageCauser) override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Glass") TObjectPtr<UWardBreakableGlass> GlassPane;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> MetalLeaf;
};

UCLASS()
class FPSGAME_API AWardGlassWindow : public AActor
{
    GENERATED_BODY()
public:
    AWardGlassWindow();
    virtual float TakeDamage(float DamageAmount,const FDamageEvent& DamageEvent,AController* EventInstigator,AActor* DamageCauser) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Glass") TObjectPtr<UWardBreakableGlass> GlassPane;
};

/** A reusable four-second world-space visual snapshot. No per-frame CPU work. */
UCLASS(NotPlaceable, Transient)
class FPSGAME_API AWardGlassBurst : public AActor
{
    GENERATED_BODY()
public:
    AWardGlassBurst();
    void Play(const UWardBreakableGlass* Pane,const FVector& HitPoint,const FVector& ShotDirection);
private:
    void Park();
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Fragments;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Glints;
    UPROPERTY() TObjectPtr<UAudioComponent> Audio;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Material;
    UPROPERTY() TObjectPtr<UMaterialInterface> MaterialSource;
    FTimerHandle ReleaseTimer;
};

/** At most six simultaneous whole-pane bursts; complete panes allocate no FX. */
UCLASS()
class FPSGAME_API UWardGlassFXSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void BreakPane(const UWardBreakableGlass* Pane,const FVector& HitPoint,const FVector& ShotDirection);
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<AWardGlassBurst>> Bursts;
    int32 Cursor=0;
};
