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
    void ToggleWeatherPanel();
    void ToggleDevelopmentPanel();
    UDevelopmentSpawnComponent* GetDevelopmentSpawner() const { return DevelopmentSpawner; }
    /** 开发面板打开期间与背包共用右侧 HUD 让位规则。 */
    UColdSteelHUDWidget* GetColdSteelHUD() const { return ColdSteelHUD; }
    /** ALT exposes the HUD cursor without suspending the held weapon/action. */
    bool IsCursorOnlyInteraction() const;
    static bool BlocksOngoingActions(const APlayerController* Player);
    bool OpenGunsmith(const FString& Instance=TEXT(""));
    void CloseGunsmith();
    bool OpenEnhancement(const FString& Instance=TEXT(""));
    void CloseEnhancement();
    UFUNCTION(BlueprintCallable, Category="Cold Steel UI") bool OpenExpedition();
    UFUNCTION(BlueprintCallable, Category="Cold Steel UI") void CloseExpedition();
    void PrepareExpeditionEquipment();
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
    virtual void PlayerTick(float DeltaTime) override;
    virtual void SetupInputComponent() override;
    virtual bool InputKey(const FInputKeyEventArgs& Params) override;

private:
    UPROPERTY(VisibleAnywhere, Category="Development") TObjectPtr<UDevelopmentSpawnComponent> DevelopmentSpawner;
    /** 主神空间（Hub 地图）驻留 BGM 组件：随控制器存活、换图自动销毁。 */
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> HubMusic;
    /** 主神空间测试宝箱（2026-10-02）：出生点旁生成一只地牢宝箱（DungeonTreasure.HubTest），仅 Hub 调用。 */
    void SpawnHubTestChest();
    /** 主神空间训练靶（2026-10-02）：出生点前方 5.5m 生成可命中木架靶（GodSpace.PracticeTarget），仅 Hub 调用。 */
    void SpawnHubPracticeTarget();
    UPROPERTY(VisibleAnywhere,Category="Building") TObjectPtr<class UVoxelBuildComponent> VoxelBuilder;
    /** -VoxelBuildAudit 时创建的建筑系统验收运行器。 */
    UPROPERTY(Transient) TObjectPtr<class UVoxelBuildAudit> VoxelBuildAudit;
    FTimerHandle VoxelBuildAuditTimer;
    bool bScopePanelsHidden=false;
    TMap<TWeakObjectPtr<class UUserWidget>,uint8> ScopePanelVisibility;
    UPROPERTY(Transient) TObjectPtr<class UM4GunsmithWidget> GunsmithPanel;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelEnhancementWidget> EnhancementPanel;
    bool bEnhancementReturnToInventory=false;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelExpeditionWidget> ExpeditionPanel;
    bool bExpeditionReturnToInventory=false;
    bool bExpeditionReturnToCursor=false;
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
};
