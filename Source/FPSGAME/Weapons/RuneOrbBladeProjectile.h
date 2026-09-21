// One orbiting energy blade of the rune sword special attack. The owning component
// steers it while hovering; a G press launches it straight at the crosshair contact.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RuneOrbBladeProjectile.generated.h"

class URuneOrbBladesComponent;
class UNiagaraComponent;
class UPointLightComponent;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;

UCLASS()
class FPSGAME_API ARuneOrbBlade : public AActor
{
    GENERATED_BODY()
public:
    ARuneOrbBlade();
    void Setup(URuneOrbBladesComponent* InSource, APawn* InOwner, float InDamage, UStaticMesh* Mesh);
    void Launch(const FVector& TargetPoint);
    void StartFade();
    bool IsFlying() const { return bFlying; }
    bool IsFinished() const { return bFinished; }
    bool CanLaunch() const { return !bFlying && !bFinished && FadeAge < 0.f; }
    virtual void Tick(float Delta) override;

private:
    void ApplyHit(const FHitResult& Hit);

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Aura;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
    UPROPERTY() TObjectPtr<UStaticMesh> ShardMesh;
    UPROPERTY() TObjectPtr<UMaterialInterface> ShardMaterial;
    TWeakObjectPtr<URuneOrbBladesComponent> Source;
    TWeakObjectPtr<APawn> Shooter;
    FVector Velocity = FVector::ZeroVector;
    float Damage = 0.f;
    float Distance = 0.f;
    float MaxDistance = Range;
    int32 VulnerabilityStacks = 0;
    float FadeAge = -1.f;
    bool bFlying = false;
    bool bFinished = false;

    static constexpr float Speed = 2000.f;       // cm/s
    static constexpr float Range = 1600.f;       // cm
    static constexpr float HitRadius = 20.f;     // sweep sphere
    static constexpr float FadeSeconds = .3f;    // matches the 2D 300 ms fade
};
