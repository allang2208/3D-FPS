#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelWarehouseChest.generated.h"
UCLASS()
class UColdSteelChestPrompt : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual void NativeOnInitialized() override;
};
/** Original rigid GLB clips converted to a rigid skin, retaining all source keys. */
UCLASS()
class FPSGAME_API AColdSteelWarehouseChest : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelWarehouseChest();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    bool CanInteract(const APawn* Pawn) const;
    bool IsWithinReach(const APawn* Pawn) const;
    void SetOpen(bool Open);
    bool IsOpen()const{return bIsOpen;}
    bool IsAnimating()const{return bAnimating;}
    UPROPERTY(EditAnywhere,Category="Warehouse") float InteractionRadius=240;
    UPROPERTY(EditAnywhere,Category="Warehouse") TObjectPtr<class USkeletalMesh> ChestAsset;
    UPROPERTY(EditAnywhere,Category="Warehouse") TObjectPtr<class UAnimSequence> OpenClip;
    UPROPERTY(EditAnywhere,Category="Warehouse") TObjectPtr<class UAnimSequence> CloseClip;
    UPROPERTY(VisibleAnywhere,Category="Warehouse") TObjectPtr<class USkeletalMeshComponent> Mesh;
private:
    UPROPERTY() TObjectPtr<class UBoxComponent> Collision;
    UPROPERTY() TObjectPtr<class UWidgetComponent> Prompt;
    bool bDesiredOpen=false,bIsOpen=false,bAnimating=false,bPlayingOpen=false;
    float Elapsed=0;
};
