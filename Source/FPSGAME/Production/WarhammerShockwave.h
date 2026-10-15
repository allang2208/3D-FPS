#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "WarhammerShockwave.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class USoundBase;

/** One authoritative, expanding ground pulse; clients render the same radius clock. */
UCLASS()
class FPSGAME_API AWarhammerShockwave : public AActor
{
    GENERATED_BODY()
public:
    AWarhammerShockwave();
    void Setup(const FColdSteelSkillShot& InShot,float Radius,float StunSeconds);
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Ring;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Material;
    UPROPERTY() TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Replicated) float MaxRadius=300.f;
    UPROPERTY(Replicated) double StartedAt=0.;
    FColdSteelSkillShot Shot;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    bool bConfigured=false,bSoundPlayed=false;
    float PreviousRadius=0.f;
    float HeavyStunSeconds=0.f;
    void ApplyWave(float Radius);
    double Clock() const;
};
