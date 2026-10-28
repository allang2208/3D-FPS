#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "KukriBerserkerVFXComponent.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UStaticMesh;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class ULocalPlayer;
class SKukriBerserkerEdge;
struct FStreamableHandle;

/** Cosmetic presentation; the rune component owns all combat state. */
UCLASS()
class FPSGAME_API UKukriBerserkerVFXComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UKukriBerserkerVFXComponent();
    void UseFrostRaven(){bFrostRaven=true;}
    void SetState(bool Equipped,float Seconds,uint8 Hands,const TArray<FString>& Instances={});
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void RequestAssets();
    void CreatePresentation();
    void ResolveHands();
    bool UsesWorldBody() const;
    void UpdateHands(const FTransform& View);
    void RefreshWeaponOverlays();
    void RestoreWeaponOverlays();
    void Hide();
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> EdgeMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> EmberMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> WeaponMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> EdgeMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WeaponMID;
    UPROPERTY(Transient) TMap<TObjectPtr<UStaticMeshComponent>,TObjectPtr<UMaterialInterface>> WeaponOverlays;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> Plane;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Emitters;
    TArray<FTransform> ParticleTransforms[2];
    TWeakObjectPtr<USkeletalMeshComponent> HandSources[2];
    TWeakObjectPtr<ULocalPlayer> HudPlayer;
    TSharedPtr<SKukriBerserkerEdge> Overlay;
    TSharedPtr<FStreamableHandle> Load;
    bool bEquipped=false,bActive=false,bRequested=false;
    bool bFrostRaven=false;
    uint8 HandMask=0;
    TArray<FString> WeaponInstances;
    float Age=0.f,EntryAge=0.f,Strength=0.f,ResolveAge=0.f;
};
