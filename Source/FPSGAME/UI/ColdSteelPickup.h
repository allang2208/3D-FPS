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
    friend class UColdSteelPickupStudio;
    bool BuildWeapon(const FColdSteelItem& Item,class UGameInstance* Context=nullptr);
    bool BuildConsumable(const FColdSteelItem& Item);
    bool BuildProductionTool(const FColdSteelItem& Item);
    bool BuildProductionMaterial(const FColdSteelItem& Item);
    void InstallProductionMaterial(class UStaticMesh* Asset,bool Wood);
    void TickProductionMaterial(float Delta);
    /** Voxel blocks drop as the 20 cm cube of their palette material, so the pickup matches the build. */
    bool BuildVoxelBlock(const FColdSteelItem& Item);
    bool bVoxelBlock=false;
    bool bProductionMaterial=false;
    bool bProductionMaterialReady=false;
    float ProductionSettleSeconds=0;
    float ProductionQuietSeconds=0;
    float ProductionMassKg=1.2f;
    TSharedPtr<struct FStreamableHandle> ProductionToolLoad;
    void BuildLootGlow(const FColdSteelItem& Item);
    void FaceLootBeam(const class APlayerController* PC);
    UPROPERTY() TObjectPtr<class USceneComponent> LootFXRoot;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> LootBeam;
    UPROPERTY() TObjectPtr<class UMaterialBillboardComponent> LootCenter;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Mesh;
    UPROPERTY() TObjectPtr<class UWidgetComponent> Prompt;
};
