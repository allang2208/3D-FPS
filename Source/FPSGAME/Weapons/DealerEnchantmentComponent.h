#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DealerPokerTypes.h"
#include "DealerEnchantmentComponent.generated.h"

class UColdSteelStatusModel;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UCameraComponent;
class USoundBase;
class UAudioComponent;
struct FStreamableHandle;

/** Authoritative per-revolver hands; two upper hole cards and five lower board slots, with selected-card flames. */
UCLASS()
class FPSGAME_API UDealerEnchantmentComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDealerEnchantmentComponent();
    void Configure(UColdSteelStatusModel* Profile);
    float Hit(const FString& Instance,const DealerPoker::FShot& Shot,bool bCritical);
protected:
    virtual void TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UFUNCTION(Client,Reliable) void ClientHand(const FString& Instance,const TArray<uint8>& InCards,uint8 InSelectedMask,uint8 Result,bool bSettled);
    void RequestAssets();
    void CreateDisplay();
    void UpdateMaterials();
    void HideDisplay();
    void PlayHighResultAudio(float Tier,float DisplayAge);
    void StopResultAudio();
    TArray<FString> EquippedInstances;
    TMap<FString,TArray<uint8>> Hands;
    FString VisibleInstance;
    TArray<uint8> VisibleCards;
    uint8 VisibleResult=0;
    bool bResult=false,bCardsSettled=false,bLoading=false;
    float RevealAge=0.f,ResultAge=0.f,Sway=0.f,LastYaw=0.f;
    float FloatAge=0.f;
    bool bHaveYaw=false;
    TWeakObjectPtr<UCameraComponent> Camera;
    TSharedPtr<FStreamableHandle> AssetHandle;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> CardMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> BadgeMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> FaceMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> BackMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> EdgeMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> BadgeMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> BurstMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Cards;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Faces;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Backs;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Edges;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Badge;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BadgeMID;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Burst;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BurstMID;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ResultLaugh;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> LaughAudio;
    bool bPendingHighLaugh=false;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> SelectedFlameMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> SelectedFlames;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> SelectedFlameMIDs;
    uint8 SelectedMask=0;
    float HoleRevealAge=0.f;
};
