#pragma once

#include "../Building/VoxelBuildPrefabActor.h"
#include "../NPC/ResidentConversation.h"
#include "VillageGunshopServices.generated.h"


UCLASS()
class FPSGAME_API AVillageGunshopWorkbench : public AVoxelBuildPrefabActor
{
    GENERATED_BODY()
public:
    AVillageGunshopWorkbench();
    UPROPERTY(EditInstanceOnly, Category="Village") TObjectPtr<UStaticMesh> StationMesh;
    virtual bool IsSceneStation() const override { return true; }
    virtual bool IsSceneStationAvailable() const override;
    virtual void SetActorHiddenInGame(bool bNewHidden) override;
    virtual void OnRep_Owner() override;
    virtual void OnRep_Configuration() override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void BindBuildingWorld();
    void RefreshRegistration();
    FTimerHandle BindTimer;
};

/** The order book and the customer-facing lip of the counter share one use target. */
UCLASS()
class FPSGAME_API AVillageGunshopCounter : public AActor
{
    GENERATED_BODY()
public:
    AVillageGunshopCounter();
    void SetLocalConversation(APlayerController* Player) { Facing.SetLocalPlayer(Player); }
    bool IsOpen() const { return !IsHidden() && GetActorEnableCollision(); }
    virtual void SetActorHiddenInGame(bool bNewHidden) override;

protected:
    virtual void BeginPlay() override;

private:
    void LoadGunsmith();
    void DressGunsmith();
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> ResidentBody;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> ResidentHead;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Workwear;
    FResidentConversationFacing Facing;
};
