#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EnhancementRitualEffect.generated.h"

class UMaterialBillboardComponent;
class UMaterialInstanceDynamic;
class UCameraComponent;
class UStaticMeshComponent;
class UMaterialInterface;
struct FStreamableHandle;

/** Local, bounded cosmetic motes. Never changes the displayed item's materials. */
UCLASS(Transient, NotBlueprintable)
class FPSGAME_API AEnhancementRitualEffect : public AActor
{
    GENERATED_BODY()
public:
    AEnhancementRitualEffect();
    void Play(AActor* Weapon, UCameraComponent* Camera, bool bEnchant, UStaticMeshComponent* Table);
    void Stop();
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void PrepareMaterial();
    void PrepareRunes(UStaticMeshComponent* Table);
    void UpdateRunes(float DeltaSeconds);
    bool PrepareContour(AActor* Weapon, UCameraComponent* Camera);
    struct FMote
    {
        FVector Target, Offset;
        float Delay=0, Size=1, Phase=0;
        bool bHalo=false;
    };
    TArray<FMote> Motes;
    UPROPERTY() TArray<TObjectPtr<UMaterialBillboardComponent>> Sprites;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Material;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> HaloMaterial;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> RuneMaterials;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> OriginalRuneMaterials;
    TArray<int32> RuneSlots;
    TWeakObjectPtr<UStaticMeshComponent> RuneTable;
    TWeakObjectPtr<AActor> Source;
    TWeakObjectPtr<UCameraComponent> PendingCamera;
    TSharedPtr<FStreamableHandle> MaterialLoad;
    double ReadyDeadline=0, NextPrepareTime=0;
    int32 PrepareAttempts=0;
    float Age=0, RuneAge=0;
    bool bBlue=false, bPending=false;
};
