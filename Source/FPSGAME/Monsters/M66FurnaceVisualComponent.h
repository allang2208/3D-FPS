#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M66FurnaceVisualComponent.generated.h"
class AM66IncineratorMonster;
class UNiagaraComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UAudioComponent;

/** One prewarmed gas volume per M66; damage is owned by the monster's clock. */
UCLASS()
class FPSGAME_API UM66FurnaceVisualComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM66FurnaceVisualComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function) override;
    bool IsReady() const;
    void Wake();
private:
    bool Prepare();
    void Configure();
    void UpdateOcclusion(const FVector& Origin,const FQuat& Rotation);
    void StopVisuals();
    UPROPERTY(Transient) TObjectPtr<AM66IncineratorMonster> Monster;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Jet;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Glow;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GlowMaterial;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Sound;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Inhale;
    UPROPERTY() TObjectPtr<UStaticMesh> Plane;
    uint32 Serial=0;
    bool bCompileRequested=false,bPrepared=false,bJetStarted=false,bSoundPlayed=false,bInhalePlayed=false,bWasBreathing=false;
    float ProbeClock=0.f,TailLeft=0.f,LastMouth=-1.f;
};
