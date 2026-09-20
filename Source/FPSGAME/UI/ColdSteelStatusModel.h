#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelWarehouseRules.h"
#include "../Movement/FPSStaminaTuning.h"
#include "ColdSteelStatusModel.generated.h"

class APawn;
struct FMeleeModifiers;

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
    /** 巧手通用修炼入口（近战命中/击杀走命中事务，翻越与消耗品等一次性动作用本入口）。 */
    bool TrainDexterousHands(int32 Amount);
    const FColdSteelSkillDefinition& DexterousHandsDefinition() const { return DexterousHandsSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress DexterousHandsProgress() const;
    FColdSteelSkillEffect DexterousHandsEffect(int32 AtLevel=-1) const;
    UFUNCTION(BlueprintPure, Category="Skills") float ReloadSpeedMultiplier() const;
    /** 「快速进战」：定义、进度、按等级与当前力量取值的施放结算与 F 键入口。 */
    const FColdSteelSkillDefinition& QuickCombatDefinition() const { return QuickCombatSkill; }
    UFUNCTION(BlueprintPure, Category="Skills") FColdSteelSkillProgress QuickCombatProgress() const;
    // Preview overrides isolate a workbench item's parts from the equipped weapon.
    FQuickCombatCast QuickCombatStats(int32 AtLevel=-1,const FMeleeModifiers* PreviewModifiers=nullptr) const;
    float QuickCombatCooldown() const;
    float QuickCombatCooldownDuration() const { return Current.QuickCombatCooldownDuration; }
    /** 按 F/快捷栏触发：不限定武器类型，按当前武器选动作（剑/手枪/步枪）；冷却中拒绝。 */
    bool TriggerQuickCombat();
    bool TrainQuickCombat(int32 Amount);
    /** 动作实际开始时预留冷却；挥击结束（FinishQuickCombatCast）后才起跳走表。 */
    bool CommitQuickCombatCast();
    void FinishQuickCombatCast();
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
    const FColdSteelSkillDefinition& IceSpikeDefinition() const { return IceSpikeSkill; }
    FColdSteelSkillProgress IceSpikeProgress() const;
    FIceSpikeCast IceSpikeStats(int32 AtLevel=-1) const;
    float IceSpikeCooldown() const { return HasNoAbilityCooldown()?0.f:Current.IceSpikeCooldown; }
    float IceSpikeCooldownDuration() const { return Current.IceSpikeCooldownDuration; }
    bool BeginIceSpikeCast(const FIceSpikeCast& Cast);
    void ApplyIceSpikeHit(APawn* Shooter,const FHitResult& Hit,const FIceSpikeCast& Cast,FIceSpikeRewards& Rewards);
    void FinishIceSpikeCast(const FIceSpikeRewards& Rewards);
    FColdSteelSkillProgress FireballProgress() const;
    FFireballCast FireballStats(int32 AtLevel=-1) const;
    /**
     * Wand hook: the spell multiplier carried by the equipped wand's item data
     * (`wandSpellMultiplier`, 1 = unchanged). No wand exists yet, so every spell
     * multiplies by 1 and today's damage numbers do not move.
     */
    double MagicImplementMultiplier() const;
    float FireballCooldown() const;
    float FireballCooldownDuration() const { return Current.FireballCooldownDuration; }
    bool HasInfiniteMana() const;
    bool CanSpendMana(float Amount) const;
    bool HasNoAbilityCooldown() const;
    void RefreshDevelopmentTuning();
    bool BeginFireballCast();
    void FinishFireballCast();
    void ApplyFireballExplosion(APawn* Shooter,const FVector& Center,const FFireballCast& Cast,const FHitResult* DirectHit=nullptr);
    float ApplySkillWeaponHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot,FWeaponDamageResult* Result=nullptr);
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
    /** 开发面板：直接提升角色等级，按正常升级发放属性点，经验夹到当前等级门槛以下。 */
    UFUNCTION(BlueprintCallable, Category="Development") bool GrantLevel(int32 Count=1);
    /** 开发面板：存档中的技能目录（规范顺序，与 ColdSteelSkills::Migrate 的键一致）。 */
    const TArray<FName>& SkillCatalog() const;
    /** 开发面板：技能的真实定义（名称／满级／图标）；MasteryDefinition 只覆盖武器精通，其余会回退到步枪。 */
    const FColdSteelSkillDefinition& DevelopmentSkillDefinition(FName Id) const;
    /** 开发面板：把指定技能提升 Count 级，不超过满级；满级清零修炼值。 */
    UFUNCTION(BlueprintCallable, Category="Development") bool RaiseSkillLevel(FName Id,int32 Count=1);
    /** 开发面板：把指定技能直接提升到满级。 */
    UFUNCTION(BlueprintCallable, Category="Development") bool MaxSkillLevel(FName Id);
    /** 开发面板：当前加载的物品目录（定义 id、名称与归纳类别），供分类下拉使用。 */
    const TArray<FColdSteelCatalogEntry>& ItemCatalog() const;
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
    /**
     * Magic hold-to-preview: a press while the bound projectile hovers starts the red
     * trajectory preview instead of firing, and the matching release fires it. A quick tap
     * behaves like a normal press; drops the request when the preview already died with its
     * projectile (timeout, death, loadout change).
     */
    bool BeginSpellAimPreview(int32 Index);
    bool EndSpellAimPreview(int32 Index);
    /** Clears any held preview, e.g. when a menu opens and the key release will not arrive. */
    void CancelSpellAimPreview();
    FColdSteelItem CreateItem(const FString& Definition, int64 Count=1) const;
    FColdSteelProposal ProposeMove(const FString& Id,int32 Place,int32 Cell,int32 Orientation=-1) const;
    bool MoveItem(const FString& Id,int32 Place,int32 Cell,int32 Orientation=-1);
    bool CommitProposal(const FColdSteelProposal& Proposal);
    UFUNCTION(BlueprintCallable, Category="Inventory") bool AddItem(const FString& Definition,int64 Count=1);
    /** 全有或全无地扣除物品（背包优先、仓库兜底），一次事务；不足时不扣任何东西并写入原因。 */
    bool ConsumeItem(const FString& Definition,int64 Count,FString& OutReason);
    bool Split(const FString& Id,int64 Count);
    bool Sort();
    bool BindHotbar(int32 Index,const FString& Id);
    bool SwapHotbar(int32 A,int32 B);
    bool UseItem(const FString& Id);
    bool UseHotbar(int32 Index);
    bool Drop(const FString& Id);
    bool Pickup(const FString& Id);
    /** Z 键范围拾取：把半径内的地面掉落一次事务收进背包；放不下的留在地面并在提示栏播报。 */
    int32 PickupNearby(float RadiusCm);
    /** 残骸转体素块：把一组方块物品放到世界坐标，一次事务。 */
    bool GrantWorldBlocks(const TMap<FString,int64>& Blocks,const FVector& Position);
    /** 提示栏：屏幕上方的进度提示队列（升级提示用的同一位置），供各系统播报信息。 */
    void PostNotice(const FString& Title,const FString& Detail=FString(),const FString& Icon=FString(),float Duration=2.8f);
    bool DefaultAction(const FString& Id);
    FColdSteelProposal ProposeWarehouse(const FString& Id,int32 Place,int32 Cell=-1,int32 Orientation=-1) const;
    bool TransferWarehouse(const FString& Id,int32 Place,int32 Cell=-1,int32 Orientation=-1);
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
    /** Clears one harvest counter so an excavated topsoil cell can be dug again. */
    bool ResetHarvestProgress(const FString& Id);
    bool HasTreeGrowth(const FString& Id) const;
    float TreeGrowthScale(const FString& Id) const;
    float TreeStumpScale(const FString& Id) const;
    bool IsTreeMature(const FString& Id) const;
    void TickTreeGrowthClock(float Delta);
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
    /** Quick slot whose ice spike preview is currently held, INDEX_NONE when none. */
    int32 AimPreviewIndex = INDEX_NONE;
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
    FColdSteelSkillDefinition IceSpikeSkill;
    FColdSteelSkillDefinition QuickCombatSkill;
    struct FFireballRewards { TMap<TWeakObjectPtr<AActor>,int64> Kills; AActor* Victim=nullptr; };
    FFireballRewards* ActiveFireballRewards=nullptr;
    TArray<FColdSteelProgressNotice> ProgressNotices;
    struct FTrainingHit { AActor* Victim=nullptr; FName SkillId; int32 ExtraExperience=0; bool bEligible=false,bCritical=false,bKillAttempted=false,bMelee=false; };
    FTrainingHit* ActiveTrainingHit=nullptr;
    void QueueProgressNotices(const FColdSteelProfile& Before,const FColdSteelProfile& After);
    FColdSteelProfile Current;
    TMap<FString,FString> Definitions;
    // 开发面板目录：首次读取时按 items.json 的类别归纳并排序，之后只读复用。
    mutable TArray<FColdSteelCatalogEntry> ItemCatalogCache;
    mutable bool bItemCatalogBuilt = false;
    TSet<TWeakObjectPtr<AActor>> RewardedVictims;
    TWeakObjectPtr<class AFPSGAMECharacter> CurrentPawn;
    FString SaveSlot;
    FString Message;
    bool bPersistenceBlocked=false;
    bool bAudit=false;
    float SaveAccumulator=0;
    TWeakObjectPtr<class AFPSWeatherManager> TreeGrowthWeather;
    float TreeGrowthWeatherSearch=0;
    void Publish(const FColdSteelProfile& State);
    // Runtime capture only persists; gameplay transactions also apply their changes.
    bool PersistState(FColdSteelProfile State, bool bApplyPawn);
    // Hit-driven training arrives once per accepted bullet. The live profile is
    // updated immediately, while the checked A/B save is coalesced instead of
    // running inside every hit.
    bool StageTraining(FColdSteelProfile&& State);
    bool bTrainingDirty = false;
    float TrainingFlushAccumulator = 0.f;
    double LastTrainingPublish = -10.;
    void ApplyToPawn();
    void RefreshDrops();
    void LoadProductionDefinitions();
    void NormalizeProductionState(FColdSteelProfile& State) const;
    bool StageProductionDrops(FColdSteelProfile& State,const FProductionResource& Target,TArray<FString>& Ids);
    void StampProductionDrop(FColdSteelItem& Item) const;
    friend class AColdSteelPickup;
};
