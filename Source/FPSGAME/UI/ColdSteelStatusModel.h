#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelStatusModel.generated.h"

DECLARE_MULTICAST_DELEGATE(FColdSteelStatusChanged);

/** Local single-player profile; every inventory and progression mutation is saved before publication. */
UCLASS()
class FPSGAME_API UColdSteelStatusModel : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character") FString CharacterName = TEXT("轮回者");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character") FString CharacterClass = TEXT("初心者");
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Character") int32 Level = 1;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Character") int32 AttributePoints = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Character") TMap<FName, int32> Attributes;
    FColdSteelStatusChanged OnChanged;
    const FColdSteelSkillDefinition& RifleDefinition() const { return RifleSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress RifleProgress() const;
    FColdSteelSkillEffect RifleEffect(int32 AtLevel=-1) const;
    float RifleWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const;
    float ApplySkillWeaponHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot);
    bool PopProgressNotice(FColdSteelProgressNotice& Out);
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    int32 Attribute(FName Key) const;
    UFUNCTION(BlueprintCallable, Category="Character") bool AllocateAttribute(FName Key);
    UFUNCTION(BlueprintCallable, Category="Character") void GrantAttributePoints(int32 Amount);
    UFUNCTION(BlueprintCallable, Category="Character") void NotifyChanged() { OnChanged.Broadcast(); }
    float Derived(FName Key) const;
    UFUNCTION(BlueprintCallable, Category="Character") bool GainExperience(int64 Amount);
    UFUNCTION(BlueprintCallable, Category="Character") bool AwardKill(AActor* Victim, int64 ExperienceReward);
    int64 MaxExperience() const;
    int64 Experience() const { return Current.Experience; }
    int32 Kills() const { return Current.Kills; }
    float Mana() const { return Current.Mana; }
    const TArray<FColdSteelItem>& Items() const { return Current.Items; }
    const FColdSteelItem* FindItem(const FString& Id) const;
    const FColdSteelItem* Equipped(int32 Slot=-1) const;
    UFUNCTION(BlueprintCallable, Category="Inventory") bool CycleWeapon();
    const FColdSteelItem* ResolveHotbar(int32 Index) const;
    FColdSteelItem CreateItem(const FString& Definition, int64 Count=1) const;
    FColdSteelProposal ProposeMove(const FString& Id,int32 Place,int32 Cell) const;
    bool MoveItem(const FString& Id,int32 Place,int32 Cell);
    bool CommitProposal(const FColdSteelProposal& Proposal);
    UFUNCTION(BlueprintCallable, Category="Inventory") bool AddItem(const FString& Definition,int64 Count=1);
    bool Split(const FString& Id,int64 Count);
    bool Sort();
    bool BindHotbar(int32 Index,const FString& Id);
    bool SwapHotbar(int32 A,int32 B);
    bool UseItem(const FString& Id);
    bool UseHotbar(int32 Index);
    bool Drop(const FString& Id);
    bool Pickup(const FString& Id);
    bool DefaultAction(const FString& Id);
    FColdSteelProposal ProposeWarehouse(const FString& Id,int32 Place,int32 Cell=-1) const;
    bool TransferWarehouse(const FString& Id,int32 Place,int32 Cell=-1);
    bool WarehouseBatch(bool bMatching);
    bool SortWarehouse(const FString& Mode,int32 Category=-1);
    bool GrantStartingArmory();
    bool AddWarehouseItem(const FColdSteelItem& Item,int32 Preferred=-1);
    int64 WarehouseRemainingCapacity(const FColdSteelItem& Item) const;
    int64 DepositWarehouseAmount(const FColdSteelItem& Item);
    bool RetrieveAllFromWarehouse();
    int64 CountWarehouseMaterial(TFunctionRef<bool(const FColdSteelItem&)> Predicate) const;
    int64 ConsumeWarehouseMaterial(TFunctionRef<bool(const FColdSteelItem&)> Predicate,int64 Amount);
    int64 CountMaterial(const FString& Definition) const;
    bool ConsumeMaterial(const FString& Definition,int64 Amount);
    int32 WarehouseCapacity() const { return Current.WarehousePages*20; }
    int32 WarehousePage = 0;
    bool bWarehouseOpen = false;
    bool SaveNow();
    bool ReloadProfile();
    void AttachPawn(class AFPSGAMECharacter* Pawn);
    void TickRuntime(float Delta,class AFPSGAMECharacter* Pawn);
    void SyncRuntime();
    int32 ConsumeAmmo(int32 Requested);
    int32 AmmoCount() const;
    FString AmmoDefinition() const;
    const FString& ResultMessage() const { return Message; }
    FColdSteelProfile Snapshot() const;
    bool CommitState(FColdSteelProfile State);
    bool IsAudit() const { return bAudit; }
    bool AuditFailNextSave = false;
    FString ProfileSlot() const { return SaveSlot; }
private:
    FColdSteelSkillDefinition RifleSkill;
    TArray<FColdSteelProgressNotice> ProgressNotices;
    struct FTrainingHit { AActor* Victim=nullptr; bool bEligible=false,bCritical=false,bKillAttempted=false; };
    FTrainingHit* ActiveTrainingHit=nullptr;
    void QueueProgressNotices(const FColdSteelProfile& Before,const FColdSteelProfile& After);
    FColdSteelProfile Current;
    TMap<FString,FString> Definitions;
    TSet<TWeakObjectPtr<AActor>> RewardedVictims;
    TWeakObjectPtr<class AFPSGAMECharacter> CurrentPawn;
    FString SaveSlot;
    FString Message;
    bool bPersistenceBlocked=false;
    bool bAudit=false;
    float SaveAccumulator=0;
    void Publish(const FColdSteelProfile& State);
    void ApplyToPawn();
    void RefreshDrops();
    friend class AColdSteelPickup;
};
