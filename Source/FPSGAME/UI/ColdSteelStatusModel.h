#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelWarehouseRules.h"
#include "../Movement/FPSStaminaTuning.h"
#include "ColdSteelStatusModel.generated.h"

class APawn;

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
    double EquipmentBonus(FName Key) const;
    const FColdSteelSkillDefinition& MasteryDefinition(FName Id) const;
    FColdSteelSkillProgress MasteryProgress(FName Id) const;
    FColdSteelSkillEffect MasteryEffect(FName Id,int32 AtLevel=-1) const;
    float AdditionalWeaponDamage(const FColdSteelItem& Item,float Damage) const;
    bool TrainHeavyStrike(int32 Hits,int32 Kills);
    FName WeaponMastery(const FColdSteelItem* Item) const;
    FString ArmorSet() const;
    double SetEffect(FName Key) const;
    double AdjustCombatStat(FName Key,double Value) const;
    double EquipmentMagicAttack() const;
    UFUNCTION(BlueprintPure) double TributeEffect(FName Key) const;
    UFUNCTION(BlueprintPure) double DungeonEffect(FName Key) const;
    float CombatMoveMultiplier() const;
    void TickFormulaBuffs(float Delta);
    UFUNCTION(BlueprintCallable) bool OfferTribute(const FString& ItemId);
    UFUNCTION(BlueprintCallable) bool ApplyDungeonFormulaBuff(FName Id,const TMap<FName,float>& Effects,int32 Battles);
    UFUNCTION(BlueprintCallable) bool CompleteDungeonFormulaBattle();
    static double EquipmentBonusFor(const FColdSteelProfile& State,FName Key);
    static double ResourceMaximum(const FColdSteelProfile& State,bool Mana);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Character") int32 AttributePoints = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Character") TMap<FName, int32> Attributes;
    FColdSteelStatusChanged OnChanged;
    FColdSteelStatusChanged OnStaminaChanged;
    UFUNCTION(BlueprintPure, Category="Stamina") float Stamina() const { return Current.Stamina; }
    UFUNCTION(BlueprintPure, Category="Stamina") float MaxStamina() const;
    UFUNCTION(BlueprintPure, Category="Stamina") float StaminaRecoveryRate() const;
    UFUNCTION(BlueprintPure, Category="Stamina") bool CanSprint() const;
    bool CanSpendStamina(float Amount) const;
    bool SpendStamina(float Amount);
    void DelayStaminaRecovery();
    float StaminaRecoveryWait() const { return Current.StaminaRecoveryDelay; }
    FColdSteelMeleeStaminaReadout MeleeStaminaReadout(const class AFPSGAMECharacter* Pawn) const;
    bool SprintExhausted() const { return Current.bSprintExhausted; }
    const FColdSteelStaminaTuning& StaminaSettings() const { return StaminaTuning; }
    const FColdSteelSkillDefinition& DodgeDefinition() const { return DodgeSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress DodgeProgress() const;
    FColdSteelSkillEffect DodgeEffect(int32 AtLevel=-1) const;
    float DodgeStaminaCost() const;
    bool TrainDodge(int32 Amount);
    const FColdSteelSkillDefinition& DexterousHandsDefinition() const { return DexterousHandsSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress DexterousHandsProgress() const;
    FColdSteelSkillEffect DexterousHandsEffect(int32 AtLevel=-1) const;
    UFUNCTION(BlueprintPure, Category="Skills") float ReloadSpeedMultiplier() const;
    const FColdSteelSkillDefinition& RifleDefinition() const { return RifleSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress RifleProgress() const;
    FColdSteelSkillEffect RifleEffect(int32 AtLevel=-1) const;
    float RifleWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const;
    const FColdSteelSkillDefinition& PistolDefinition() const { return PistolSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress PistolProgress() const;
    FColdSteelSkillEffect PistolEffect(int32 AtLevel=-1) const;
    float PistolWeaponDamage(const FColdSteelItem& Item,float WeaponDamage) const;
    UFUNCTION(BlueprintPure, Category="Skills") float PistolMovementMultiplier() const;
    const FColdSteelSkillDefinition& CriticalStrikeDefinition() const { return CriticalStrikeSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress CriticalStrikeProgress() const;
    FColdSteelSkillEffect CriticalStrikeEffect(int32 AtLevel=-1) const;
    const FColdSteelSkillDefinition& FireballDefinition() const { return FireballSkill; }
    FColdSteelSkillProgress FireballProgress() const;
    FFireballCast FireballStats(int32 AtLevel=-1) const;
    float FireballCooldown() const;
    bool HasInfiniteMana() const;
    bool CanSpendMana(float Amount) const;
    bool HasNoAbilityCooldown() const;
    void RefreshDevelopmentTuning();
    bool BeginFireballCast();
    void FinishFireballCast();
    void ApplyFireballExplosion(APawn* Shooter,const FVector& Center,const FFireballCast& Cast,AActor* DirectTarget=nullptr);
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
    float Mana() const;
    const TArray<FColdSteelItem>& Items() const { return Current.Items; }
    const FColdSteelItem* FindItem(const FString& Id) const;
    const FColdSteelItem* Equipped(int32 Slot=-1) const;
    UFUNCTION(BlueprintCallable, Category="Inventory") bool CycleWeapon();
    const FColdSteelItem* ResolveHotbar(int32 Index) const;
    const TArray<FColdSteelQuickBinding>& QuickBindings() const { return Current.QuickBindings; }
    FColdSteelQuickBinding QuickBinding(int32 Index) const;
    const FColdSteelItem* ResolveQuickItem(int32 Index) const;
    const FColdSteelSkillDefinition* QuickSkillDefinition(FName Id) const;
    bool CanBindQuickSkill(FName Id) const;
    bool BindQuickSkill(int32 Index,FName Id);
    bool BindQuickItem(int32 Index,const FString& Id);
    bool SwapQuickBindings(int32 From,int32 To);
    bool ClearQuickBinding(int32 Index);
    bool UseQuickBinding(int32 Index);
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
    bool StoreMatchingToWarehouse();
    bool SortWarehouse(const FString& Mode,int32 Category=-1);
    bool GrantStartingArmory();
    bool GrantEnhancementMaterials();
    bool GrantProductionTools();
    const FColdSteelItem* ActiveProductionTool() const;
    bool ToggleProductionTool(const FString& InstanceId);
    bool SelectProductionTool(const FString& Definition);
    bool StowProductionTool();
    int32 HarvestProgress(const FString& Id) const;
    bool CommitHarvestStrike(const struct FProductionResource& Target,bool& Depleted);
    bool AddWarehouseItem(const FColdSteelItem& Item,int32 Preferred=-1);
    int64 WarehouseRemainingCapacity(const FColdSteelItem& Item) const;
    int64 DepositWarehouseAmount(const FColdSteelItem& Item);
    bool RetrieveAllFromWarehouse();
    int64 CountWarehouseMaterial(TFunctionRef<bool(const FColdSteelItem&)> Predicate) const;
    int64 ConsumeWarehouseMaterial(TFunctionRef<bool(const FColdSteelItem&)> Predicate,int64 Amount);
    int64 CountMaterial(const FString& Definition) const;
    bool ConsumeMaterial(const FString& Definition,int64 Amount);
    int32 WarehouseCapacity() const { return Current.WarehousePages*ColdSteelWarehouse::CellsPerPage; }
    int32 WarehousePage = 0;
    bool bWarehouseOpen = false;
    bool SaveNow();
    bool ReloadProfile();
    void AttachPawn(class AFPSGAMECharacter* Pawn);
    void TickRuntime(float Delta,class AFPSGAMECharacter* Pawn);
    void SyncRuntime();
    FString AmmoDefinitionFor(const FColdSteelItem& Item) const;
    int32 AmmoCountFor(const FColdSteelItem& Item) const;
    int32 ReloadDualPistol(const FString& InstanceId,int32 Requested,int32 Capacity,bool Completed);
    bool EjectDualPistolCases(const FString& InstanceId,bool DiscardLive);
    int32 ConsumeAmmo(int32 Requested, bool bCompletedReload=false, bool bReloadStep=false);
    bool ClearRevolverSpentCases(bool bDiscardLiveRounds = false);
    int32 AmmoCount() const;
    FString AmmoDefinition() const;
    const FString& ResultMessage() const { return Message; }
    FColdSteelProfile Snapshot() const;
    bool CommitState(FColdSteelProfile State);
    bool IsAudit() const { return bAudit; }
    bool AuditFailNextSave = false;
    FString ProfileSlot() const { return SaveSlot; }
private:
    FColdSteelStaminaTuning StaminaTuning;
    FColdSteelSkillDefinition DodgeSkill;
    FColdSteelSkillDefinition DexterousHandsSkill;
    void LoadStaminaTuning();
    bool NormalizeStamina(FColdSteelProfile& State) const;
    void TickStamina(float Delta, class AFPSGAMECharacter* Pawn);
    FColdSteelSkillDefinition RifleSkill;
    FColdSteelSkillDefinition PistolSkill;
    FColdSteelSkillDefinition CriticalStrikeSkill;
    FColdSteelSkillDefinition FireballSkill;
    struct FFireballRewards { TMap<TWeakObjectPtr<AActor>,int64> Kills; AActor* Victim=nullptr; };
    FFireballRewards* ActiveFireballRewards=nullptr;
    TArray<FColdSteelProgressNotice> ProgressNotices;
    struct FTrainingHit { AActor* Victim=nullptr; FName SkillId; int32 ExtraExperience=0; bool bEligible=false,bCritical=false,bKillAttempted=false; };
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
    void LoadProductionDefinitions();
    void NormalizeProductionState(FColdSteelProfile& State) const;
    bool StageProductionDrops(FColdSteelProfile& State,const FProductionResource& Target,TArray<FString>& Ids);
    void StampProductionDrop(FColdSteelItem& Item) const;
    friend class AColdSteelPickup;
};
