#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Skills/LightningTypes.h"
#include "FPSMeleeLightningComponent.generated.h"

class AFPSLightningArc;
class UColdSteelStatusModel;
class UNiagaraSystem;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class USceneComponent;
struct FStreamableHandle;

/** Item-owned melee proc; independent of the active lightning cast/cooldown. */
UCLASS(ClassGroup=(Weapons),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSMeleeLightningComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSMeleeLightningComponent();
    static bool IsEnemy(AActor* Target,AActor* Owner);
    void QueueDischarge(const FHitResult& Hit,float RadiusCM,int32 MinimumLevel);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    struct FChain
    {
        FLightningCast Spell;
        float Radius=500.f;
        TSet<TWeakObjectPtr<AActor>> Visited;
    };
    struct FWave
    {
        TSharedPtr<FChain> Chain;
        TWeakObjectPtr<AActor> Origin;
        FVector Start=FVector::ZeroVector;
        int32 Depth=0;
        bool bRandomFirst=false;
        bool bOverload=false;
        double Due=0.;
    };
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UNiagaraSystem> ChainAsset;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UNiagaraSystem> BladeAsset;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UStaticMesh> OrbitMeshAsset;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UMaterialInterface> OrbitMaterialAsset;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ChainSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> BladeSystem;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> OrbitMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> OrbitMaterial;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> BladeAnchor;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> BladeRings;
    TSharedPtr<FStreamableHandle> LoadHandle;
    TWeakObjectPtr<UColdSteelStatusModel> Profile;
    FDelegateHandle ProfileChanged;
    TArray<FWave> Waves;
    TArray<TWeakObjectPtr<AFPSLightningArc>> WorldArcs;
    TArray<TWeakObjectPtr<AFPSLightningArc>> BladeArcs;
    FRandomStream CosmeticRandom;
    FString VisualItem;
    uint32 VisualDataHash=0;
    bool bBladeEnabled=false;
    float BladeCountdown=0.f;
    float BladeAge=0.f;
    void RefreshEquipment();
    void TickBlade(float Delta);
    void UpdateBladeRings(float Length);
    void ClearBlade();
    void ProcessWave(const FWave& Wave);
    void Gather(const FWave& Wave,TArray<AActor*>& Out) const;
    void ShowArc(const FVector& Start,const FVector& End,const FLightningCast& Spell,bool bOverload);
};
