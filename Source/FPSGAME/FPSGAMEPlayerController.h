#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "FPSGAMEPlayerController.generated.h"

class UColdSteelHUDWidget;
class UWeatherControlWidget;
class UDevelopmentSpawnComponent;
struct FInputKeyEventArgs;

UCLASS()
class FPSGAME_API AFPSGAMEPlayerController : public APlayerController
{
    GENERATED_BODY()

public:
    AFPSGAMEPlayerController();
    void OpenGameMenu();
    void OpenWorldMap();
    const struct FColdSteelMapMarkers* GetMapMarkers() const;
    void CloseGameMenu();
    bool IsGameMenuOpen() const;
    bool CanOpenGameMenu() const;
    void SetHubMusicUserVolume(float Volume);
    void RefreshRegionMusic();
    UFUNCTION(Server,Reliable) void ServerUseApartmentControl(class AApartmentDeviceControl* Control);
    UFUNCTION(Server,Reliable) void ServerUseHeQuePump(class AHeQuePumpControl* Control);
    UFUNCTION(Server,Reliable) void ServerRepairVillageDefense(class AVillageDefenseSection* Section,APawn* RequestPawn,uint32 RequestId);
    UFUNCTION(Client,Reliable) void ClientVillageRepairResult(uint32 RequestId,bool bRepaired,const FText& Message);
    void RequestVillageRepair(class AVillageDefenseSection* Section);
    bool IsInBuildMode() const;
    class UVillageSiegeControl* GetSiegeControl() const { return SiegeControl; }
    void ToggleWeatherPanel();
    void ToggleDevelopmentPanel();
    void OpenSmartTurretDrawer(class AVillageSmartTurret* Turret);
    void CloseSmartTurretDrawer();
    bool IsSmartTurretDrawerOpen() const { return SmartTurretDrawer.IsValid(); }
    UFUNCTION(Server,Reliable) void ServerSmartTurretMount(class AVillageSmartTurret* Turret,const FString& ItemInstanceId);
    UFUNCTION(Server,Reliable) void ServerSmartTurretUnmount(class AVillageSmartTurret* Turret);
    UFUNCTION(Client,Reliable) void ClientSmartTurretResult(bool bSuccess,const FString& Message);
    UDevelopmentSpawnComponent* GetDevelopmentSpawner() const { return DevelopmentSpawner; }
    class UChapelDialogueComponent* GetChapelDialogue() const { return ChapelDialogue; }
    /** 开发面板打开期间与背包共用右侧 HUD 让位规则。 */
    UColdSteelHUDWidget* GetColdSteelHUD() const { return ColdSteelHUD; }
    /** 训练靶命中只回传给实际攻击者的 HUD，避免全服广播/客户端过滤。 */
    UFUNCTION(Client,Unreliable) void ClientPracticeHit(AActor* Target,FVector Point,float Damage,bool bBullseye,float MagicApplied);
    /** 城防设施伤害浮字（服务端按合理可视距离分发给主机与客机玩家）。 */
    UFUNCTION(Client,Unreliable) void ClientDefenseDamageNumber(AActor* Target,FVector_NetQuantize WorldPoint,float AppliedDamage,float MagicDamage,bool bCritical,bool bKilled,bool bBig);
    /** Live item thumbnails are only produced while a consuming panel is open. */
    bool IsItemIconPanelOpen() const;
    /** ALT exposes the HUD cursor without suspending the held weapon/action. */
    bool IsCursorOnlyInteraction() const;
    static bool BlocksOngoingActions(const APlayerController* Player);
    /** Browsing panels own new input, but do not revoke an action already begun. */
    bool IsActionPreservingPanelOpen() const;
    static bool BlocksActionContinuation(const APlayerController* Player);
    bool OpenGunsmith(const FString& Instance=TEXT(""));
    void CloseGunsmith();
    bool OpenWoodworking(AActor* Station,bool PracticeOnly=false);
    bool IsWoodworkingOpen() const { return WoodworkingPanel!=nullptr; }
    void CloseWoodworking();
    bool OpenAlchemy(AActor* Station);
    bool IsAlchemyOpen() const {return AlchemyPanel!=nullptr;}
    bool IsAlchemyPanelUnderLocation(FVector2D ScreenPosition) const;
    void CloseAlchemy();
    /** Manual development practice entry; never consumes materials or grants rewards. */
    bool OpenEnhancement(const FString& Instance=TEXT(""));
    bool OpenEnhancement(AActor* Station,const FString& Instance=TEXT(""));
    bool IsEnhancementOpen() const { return EnhancementPanel!=nullptr; }
    bool IsEnhancementSessionValid() const;
    AActor* GetEnhancementStation() const;
    bool IsEnhancementPanelUnderLocation(FVector2D Position) const;
    bool HandleEnhancementItemDrop(class UColdSteelItemDrag* Drag,FVector2D Position);
    void CloseEnhancement();
    UFUNCTION(BlueprintCallable, Category="Cold Steel UI") bool OpenExpedition();
    UFUNCTION(BlueprintCallable, Category="Cold Steel UI") void CloseExpedition();
    void PrepareExpeditionEquipment();
    void ResumeExpeditionAfterEquipment();
    void RunEnhancementAudit();
    void RunM4GunsmithAudit();
    void RunM4DrumAudit();
    void RunGunsmithWorkbenchAudit();
    void RunPrismHandstopAudit();
    void RunVerticalForegripAudit();
    void RunCantedForegripAudit();
    void RunGunsmithLayoutStress(TSharedPtr<FIntPoint> Counts);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void PlayerTick(float DeltaTime) override;
    virtual void UpdateRotation(float DeltaTime) override;
    virtual void UpdateHiddenComponents(const FVector& ViewLocation,TSet<FPrimitiveComponentId>& HiddenComponents) override;
    virtual void SetupInputComponent() override;
    virtual bool InputKey(const FInputKeyEventArgs& Params) override;

private:
    uint32 VillageRepairRequestId=0;
    TWeakObjectPtr<APawn> VillageRepairPawn;
    TMap<uint32,TWeakObjectPtr<AVillageDefenseSection>> PendingVillageRepairs;
    TWeakObjectPtr<AVillageDefenseSection> RecentlyRepairedSection;
    double RepairedSectionRetryTime=0.;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelGameMenuWidget> GameMenu;
    bool bGameMenuOwnsInput = false;
    bool bGameMenuOwnsPause = false;
    bool bMapReturnToCursor = false;
    UPROPERTY(VisibleAnywhere, Category="Development") TObjectPtr<UDevelopmentSpawnComponent> DevelopmentSpawner;
    UPROPERTY(VisibleAnywhere, Category="NPC") TObjectPtr<class UChapelDialogueComponent> ChapelDialogue;
    /** 当前地图 BGM（主神空间／随机地牢）；沿用 HubMusic 名称兼容现有音量设置入口。 */
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> HubMusic;
    FString RegionMusicPath;
    uint32 RegionMusicSerial=0;
    float HubMusicUserVolume=1.f;
    /** 主神空间测试宝箱（2026-10-02）：出生点旁生成一只地牢宝箱（DungeonTreasure.HubTest），仅 Hub 调用。 */
    void SpawnHubTestChest();
    /** 主神空间训练靶（2026-10-02）：出生点前方 5.5m 生成可命中木架靶（GodSpace.PracticeTarget），仅 Hub 调用。 */
    void SpawnHubPracticeTarget();
    UPROPERTY(VisibleAnywhere,Category="Building") TObjectPtr<class UVillageSiegeControl> SiegeControl;
    UPROPERTY(VisibleAnywhere,Category="Building") TObjectPtr<class UVoxelBuildComponent> VoxelBuilder;
    /** -VoxelBuildAudit 时创建的建筑系统验收运行器。 */
    UPROPERTY(Transient) TObjectPtr<class UVoxelBuildAudit> VoxelBuildAudit;
    FTimerHandle VoxelBuildAuditTimer;
    UPROPERTY(Transient) TObjectPtr<class UM4GunsmithWidget> GunsmithPanel;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelEnhancementWidget> EnhancementPanel;
    bool bEnhancementReturnToInventory=false,bEnhancementReturnToCursor=false;
    UPROPERTY(Transient) TObjectPtr<class AEnhancementWorldView> EnhancementWorld;
    TWeakObjectPtr<AActor> EnhancementStation;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelExpeditionWidget> ExpeditionPanel;
    bool bExpeditionReturnToInventory=false;
    bool bExpeditionReturnToCursor=false;
    bool bExpeditionEquipmentOpen=false;
    void ToggleInventory();
    void ToggleTimelineInteraction();
    void CaptureTimelineAudit(const FString& Filename, int32 State);
    void CaptureInventoryAudit(const FString& Filename, int32 State);

    UPROPERTY(Transient)
    TObjectPtr<UColdSteelHUDWidget> ColdSteelHUD;
    UPROPERTY(Transient)
    TObjectPtr<class ULPVOScopeWidget> ScopeOverlay;

    UPROPERTY(Transient)
    TObjectPtr<UWeatherControlWidget> WeatherPanel;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelWoodworkingWidget> WoodworkingPanel;
    bool bWoodworkingReturnToCursor=false;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelAlchemyWidget> AlchemyPanel;
    bool bAlchemyReturnToCursor=false;
    TSharedPtr<class SSmartTurretDrawer> SmartTurretDrawer;
    TWeakObjectPtr<class AVillageSmartTurret> ActiveSmartTurret;
};
