#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GunsmithSystem.h"
#include "ZhenmoRuneComponent.generated.h"

class UColdSteelStatusModel;
class UDynamicMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UNiagaraSystem;
class UNiagaraComponent;
struct FStreamableHandle;
struct FZhenmoGroundCache;

/** One moving field per wielder. Proc time is authoritative; overlapping fields do not stack. */
UCLASS()
class FPSGAME_API UZhenmoRuneComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UZhenmoRuneComponent();
    void Configure(const UColdSteelStatusModel* InProfile);
    void ConfirmCritical(const FString& SourceInstance);
    bool Affects(const AActor* Target) const;
    float Remaining() const;
    float Duration() const {return Modifiers.ZhenmoSeconds;}
    float DamageBonus() const {return Modifiers.ZhenmoDamageTakenBonus;}
    float Slow() const {return Modifiers.ZhenmoSlow;}
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn) override;
private:
    bool Equipped() const;
    double Clock() const;
    void Pulse();
    void Clear();
    void RefreshVisual(float Delta=0.f);
    void RefreshGround(const FVector& Feet);
    FVector GroundMoteSlope() const;
    void LoadVisual();
    UFUNCTION() void OnRep_Field();
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    FString EquippedInstance;
    FMeleeModifiers Modifiers;
    TSet<TWeakObjectPtr<AActor>> Targets;
    FTimerHandle PulseTimer;
    TSharedPtr<FStreamableHandle> LoadHandle;
    UPROPERTY(ReplicatedUsing=OnRep_Field) double EndsAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_Field) float RadiusCM=1500.f;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> FieldMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FieldMID;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> FieldSurface;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> MoteSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> FieldMotes;
    bool bMotesActive=false;
    float VisualBlend=0.f;
    FVector GroundAnchor=FVector::ZeroVector;
    double NextGroundUpdate=0.;
    bool bGroundReady=false;
    TSharedPtr<FZhenmoGroundCache> GroundCache;
};
