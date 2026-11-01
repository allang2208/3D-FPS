#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "ThunderHammerFX.generated.h"

class USplineComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USoundBase;
struct FStreamableHandle;

/** Local cosmetic pool entry. The replicated WarhammerShockwave owns all damage. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API AThunderHammerStrikeFX : public AActor
{
    GENERATED_BODY()
public:
    AThunderHammerStrikeFX();
    void Prepare(UNiagaraSystem* Bolt,UNiagaraSystem* Burst);
    void Play(const FVector& Point,const FVector& Normal,float Height,int32 Seed,float InitialAge,USoundBase* Sound,float Scale=1.f);
    virtual void Tick(float Delta) override;
    float Age=10.f;
private:
    UPROPERTY() TArray<TObjectPtr<USplineComponent>> Paths;
    UPROPERTY() TArray<TObjectPtr<UNiagaraComponent>> Bolts;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Impact;
    UPROPERTY() TObjectPtr<UPointLightComponent> Light;
    void UpdateEnvelope();
    float VisualScale=1.f;
};

/** Four reusable strikes; async residency and construction happen before contact. */
UCLASS()
class FPSGAME_API UThunderHammerFXSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
    bool Emit(const FVector& Point,const FVector& Normal,float Height,int32 Seed,float Age,float Scale=1.f);
    void EmitOverload(APawn* Owner,const FVector& Start,const FVector& End,const struct FLightningCast& Spell);
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    UPROPERTY() TArray<TObjectPtr<AThunderHammerStrikeFX>> Pool;
    TArray<TWeakObjectPtr<class AFPSLightningArc>> OverloadArcs;
    TSharedPtr<FStreamableHandle> Assets;
    FTimerHandle PreparationTimer;
    void PrepareNext();
};
