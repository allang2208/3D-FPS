#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "CampfireCookingPresentation.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UNiagaraSystem;
class UNiagaraComponent;
class USoundCue;
class UAudioComponent;
struct FStreamableHandle;

/** Read-only view of the replicated station. Never owns ingredients or products. */
UCLASS()
class UCampfireCookingPresentation : public UActorComponent
{
    GENERATED_BODY()
public:
    void Update(bool bWithinBudget);
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void LoadAssets();
    void StopEffects();
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> Meshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Display;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SteamAsset;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Steam;
    UPROPERTY(Transient) TObjectPtr<USoundCue> SizzleLoop;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Sizzle;
    TSharedPtr<FStreamableHandle> LoadHandle;
    bool bAdmitted=false;
    double NextSteam=0;
};
