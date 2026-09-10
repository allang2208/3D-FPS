#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelPickup.generated.h"
UCLASS()
class UColdSteelPickupPrompt : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetCaption(const FString& Caption);
protected:
    virtual void NativeOnInitialized() override;
private:
    UPROPERTY() TObjectPtr<class UTextBlock> Text;
};
UCLASS()
class FPSGAME_API AColdSteelPickup : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelPickup();
    FString ItemId;
    void InitializeItem(const FColdSteelItem& Item);
    virtual void Tick(float DeltaSeconds) override;
    bool CanInteract(const APawn* Pawn) const;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UBoxComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UPoseableMeshComponent> Weapon;
private:
    bool BuildWeapon(const FColdSteelItem& Item);
    bool BuildConsumable(const FColdSteelItem& Item);
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Mesh;
    UPROPERTY() TObjectPtr<class UWidgetComponent> Prompt;
};
