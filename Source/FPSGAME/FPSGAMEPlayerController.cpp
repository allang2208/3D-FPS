#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelQuickBarTypes.h"
#include "UI/TransitLoadingSubsystem.h"
#include "Dungeons/DungeonRunSubsystem.h"
#include "SceneTestPortal.h"
#include "EngineUtils.h"
#include "FPSGAMECharacter.h"
#include "Building/VoxelBuildComponent.h"
#include "Building/VoxelBuildAudit.h"
#include "Building/ColdSteelDoorInteraction.h"

#include "UI/ColdSteelHUDWidget.h"
#include "UI/LPVOScopeWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelPickup.h"
#include "Weapons/Bow/BowArrow.h"
#include "UI/ColdSteelWorldInteraction.h"
#include "UI/ColdSteelWarehouseChest.h"
#include "UI/ColdSteelSceneContainer.h"
#include "UI/ColdSteelCrateChest.h"
#include "Props/FPSPracticeTarget.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "UI/WeatherControlWidget.h"
#include "UI/DevelopmentPanelWidget.h"
#include "Development/DevelopmentSpawnComponent.h"
#include "UI/WeatherPanelValidation.h"
#include "Components/InputComponent.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/PlayerStart.h"
#include "Sound/SoundBase.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"

namespace
{
    /** Z 键范围拾取半径；默认 5 m，可现场用控制台调整。 */
    TAutoConsoleVariable<float> AreaPickupRadiusCm(TEXT("fps.Pickup.AreaRadiusCm"),500.f,
        TEXT("Z 键一键拾取的作用半径（cm）。"));
}
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "UnrealClient.h"

void RunRetiredWeaponsAudit(AFPSGAMEPlayerController* PC);
void RunWeaponWheelAudit(AFPSGAMEPlayerController* PC);
void RunWorldInteractionAudit(AFPSGAMEPlayerController* PC);
void RunConsumablePickupAudit(AFPSGAMEPlayerController* PC);
void RunEnhancementMaterialPickupAudit(AFPSGAMEPlayerController* PC);
void RunMagicScrollAudit(AFPSGAMEPlayerController* PC);
void RunLootGlowAudit(AFPSGAMEPlayerController* PC);

AFPSGAMEPlayerController::AFPSGAMEPlayerController()
{
    VoxelBuilder=CreateDefaultSubobject<UVoxelBuildComponent>(TEXT("VoxelBuilder"));
    DevelopmentSpawner=CreateDefaultSubobject<UDevelopmentSpawnComponent>(TEXT("DevelopmentSpawner"));
    bShowMouseCursor = false;
}

/** 主神空间测试宝箱（2026-10-02 用户指派）：出生点旁放一只地牢宝箱，实机验证仓库式取物面板。
 *  DungeonTreasure.HubTest＝无运行上下文也可 roll（Depth 0 档、按领取键固定种子）；
 *  DungeonChestClaim.HubTest＝稳定领取键；战利品被取空后下次开箱自动重新 roll。 */
void AFPSGAMEPlayerController::SpawnHubTestChest()
{
    for (TActorIterator<ASkeletalMeshActor> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(TEXT("DungeonTreasure.HubTest"))) return; // 本局已生成过
    auto* Mesh = LoadObject<USkeletalMesh>(nullptr,
        TEXT("/Game/Props/GamedevTreasureChest20260922/SK_GamedevTreasureChest.SK_GamedevTreasureChest"));
    if (!Mesh) { UE_LOG(LogTemp, Warning, TEXT("HubTestChest: 宝箱网格缺失")); return; }

    // 出生点锚：与 GameMode 出生／仓库宝箱固定生成同一数据源（首个 PlayerStart），贴地后放右侧 220cm。
    FVector Base = FVector::ZeroVector; FRotator Facing = FRotator::ZeroRotator; bool bAnchor = false;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        FCollisionQueryParams Query(SCENE_QUERY_STAT(HubTestChestFloor), false, *It);
        FHitResult Floor;
        const FVector Probe = It->GetActorLocation();
        if (GetWorld()->LineTraceSingleByChannel(Floor, Probe + FVector(0, 0, 300), Probe - FVector(0, 0, 2000), ECC_Visibility, Query)
            && Floor.bBlockingHit && !Floor.bStartPenetrating)
            Base = Floor.ImpactPoint;
        else Base = Probe;
        Facing = It->GetActorRotation(); bAnchor = true;
        break;
    }
    if (!bAnchor) return;

    const FVector Side = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
    auto* Chest = GetWorld()->SpawnActor<ASkeletalMeshActor>(ASkeletalMeshActor::StaticClass(),
        Base + Side * 220.f, FRotator(0.f, Facing.Yaw + 180.f, 0.f));
    if (!Chest) return;
    Chest->Tags.Add(TEXT("DungeonTreasureChest"));
    Chest->Tags.Add(TEXT("DungeonTreasure.HubTest"));
    Chest->Tags.Add(TEXT("DungeonChestClaim.HubTest"));
    auto* Component = Chest->GetSkeletalMeshComponent();
    Component->SetSkeletalMeshAsset(Mesh);
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (auto* Closed = LoadObject<UAnimSequence>(nullptr,
        TEXT("/Game/Props/GamedevTreasureChest20260922/A_TreasureChest_ClosedPose.A_TreasureChest_ClosedPose")))
    {
        Component->PlayAnimation(Closed, false); Component->SetPosition(Closed->GetPlayLength(), false); Component->SetPlayRate(0.f);
        Component->TickAnimation(0.f, false); Component->RefreshBoneTransforms(); Component->SetComponentTickEnabled(false);
        Component->ComponentTags.Add(TEXT("DungeonClosedPoseFrozen"));
    }
    // 与地牢生成器同口径：骨骼网格不参与射线（NoCollision），交互命中靠 BlockAll 盒体（尺寸取 treasure_chest_assets.json）。
    auto* Box = NewObject<UBoxComponent>(Chest);
    Chest->AddInstanceComponent(Box);
    Box->SetupAttachment(Component);
    Box->SetBoxExtent(FVector(59.5f, 74.3f, 55.1f));
    Box->SetRelativeLocation(FVector(6.2f, 5.2f, 55.1f));
    Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->RegisterComponent();
}

/** 主神空间训练靶（2026-10-02 用户指派）：出生点前方下靶位生成圆环木架靶，承接全武器命中，
 *  浮出伤害数字并在头顶牌滚动 DPS。与 SpawnHubTestChest 同一出生点锚、同贴地方式。 */
void AFPSGAMEPlayerController::SpawnHubPracticeTarget()
{
    for (TActorIterator<AFPSPracticeTarget> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(TEXT("GodSpace.PracticeTarget"))) return; // 本局已生成过

    FVector Base = FVector::ZeroVector; FRotator Facing = FRotator::ZeroRotator; bool bAnchor = false;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        Base = It->GetActorLocation();
        Facing = It->GetActorRotation(); bAnchor = true;
        break;
    }
    if (!bAnchor) return;

    const FVector Forward = FRotationMatrix(Facing).GetUnitAxis(EAxis::X);
    const FVector Spot = Base + Forward * 550.f;
    FHitResult Floor;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HubPracticeTargetFloor), false);
    FVector Position = Spot;
    if (GetWorld()->LineTraceSingleByChannel(Floor, Spot + FVector(0, 0, 200), Spot - FVector(0, 0, 1500), ECC_Visibility, Query)
        && Floor.bBlockingHit && !Floor.bStartPenetrating)
        Position = Floor.ImpactPoint;

    auto* Target = GetWorld()->SpawnActor<AFPSPracticeTarget>(Position, FRotator(0.f, Facing.Yaw + 180.f, 0.f));
    if (Target) Target->Tags.Add(TEXT("GodSpace.PracticeTarget"));
}

void AFPSGAMEPlayerController::BeginPlay()
{
    Super::BeginPlay();
    // 主神空间驻留 BGM：原项目 audio-config 的 bgm.main（main 场景＝主神空间，罗马庭院），
    // 沿用其 music 声道 0.6 音量。SoundWave 已设循环；组件随控制器存活、换图销毁，
    // 因此只在 Hub（DayNight_Lighting）内自动循环，去 hills/地牢自动停止。
    if (UGameplayStatics::GetCurrentLevelName(this, true) == TEXT("DayNight_Lighting"))
    {
        if (auto* Sound = LoadObject<USoundBase>(nullptr, TEXT("/Game/Audio/GodSpaceBGM20261002/S_RomanCourtyard.S_RomanCourtyard")))
        {
            HubMusic = NewObject<UAudioComponent>(this);
            HubMusic->SetSound(Sound);
            HubMusic->SetVolumeMultiplier(.6f);
            HubMusic->bAutoDestroy = false;
            HubMusic->Play();
        }
        SpawnHubTestChest();
        SpawnHubPracticeTarget();
    }
    // 建筑系统验收：-VoxelBuildAudit（材质表 / 过载曲线 / 体素块目录 / 放置-撤销-拆除闭环 / 存档落盘）
    if(UVoxelBuildAudit::Requested())
    {
        VoxelBuildAudit=NewObject<UVoxelBuildAudit>(this);
        VoxelBuildAudit->Start(this);
        GetWorldTimerManager().SetTimer(VoxelBuildAuditTimer,
            FTimerDelegate::CreateWeakLambda(this,[this]()
            {
                if(VoxelBuildAudit&&VoxelBuildAudit->Tick())GetWorldTimerManager().ClearTimer(VoxelBuildAuditTimer);
            }),1.5f,true,8.f);
    }
    if(FParse::Param(FCommandLine::Get(),TEXT("LootGlowAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunLootGlowAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("MagicScrollAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunMagicScrollAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("DropHitchAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){if(ColdSteelHUD)ColdSteelHUD->RunDropHitchAudit();}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("EnhancementMaterialPickupAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunEnhancementMaterialPickupAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("ConsumablePickupAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunConsumablePickupAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("WorldInteractionAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunWorldInteractionAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("WeaponWheelAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunWeaponWheelAudit(this);}),5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelEnhancementAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunEnhancementAudit,12.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("GunsmithWorkbenchAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunGunsmithWorkbenchAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("CantedForegripAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunCantedForegripAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("VerticalForegripAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunVerticalForegripAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("PrismHandstopAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunPrismHandstopAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("M4DrumAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunM4DrumAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("M4GunsmithAudit")))
    {
        FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunM4GunsmithAudit,5.f,false);
    }
    if(FParse::Param(FCommandLine::Get(),TEXT("RetiredWeaponsAudit")))
        GetWorldTimerManager().SetTimerForNextTick([this](){RunRetiredWeaponsAudit(this);});

    if (!IsLocalController())
    {
        return;
    }

#if !UE_BUILD_SHIPPING
    WeatherPanel = CreateWidget<UDevelopmentPanelWidget>(this, UDevelopmentPanelWidget::StaticClass());
    // The unified panel owns the F6 input context. Its drawer now shares the backpack's
    // size, slide and HUD-yield rules, so it must sit above the HUD (20) to dim it the
    // same way; gunsmith/enhancement panels (60) and drag visuals (1000) stay on top.
    if (WeatherPanel) WeatherPanel->AddToPlayerScreen(30);
    StartWeatherPanelValidation(this, WeatherPanel);
#endif
    ColdSteelHUD = CreateWidget<UColdSteelHUDWidget>(this, UColdSteelHUDWidget::StaticClass());
    ScopeOverlay=CreateWidget<ULPVOScopeWidget>(this,ULPVOScopeWidget::StaticClass());
    if(ScopeOverlay){ScopeOverlay->SetVisibility(ESlateVisibility::HitTestInvisible);ScopeOverlay->AddToPlayerScreen(10);}
    if (ColdSteelHUD)
    {
        ColdSteelHUD->AddToPlayerScreen(20);
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelTopVitalsAudit"))){FTimerHandle VitalsAudit;GetWorldTimerManager().SetTimer(VitalsAudit,[this](){ColdSteelHUD->RunTopVitalsAudit();},10.f,false);}
        FTimerHandle WarehouseInit;
        GetWorldTimerManager().SetTimer(WarehouseInit,[this]()
        {
            // The gunplay audit requires its original clear movement corridor.
            if(FParse::Param(FCommandLine::Get(),TEXT("GunplayAudit"))){UE_LOG(LogTemp,Display,TEXT("Gunplay audit: omit automatic chest from movement fixture"));return;}
            const bool Audit=FParse::Param(FCommandLine::Get(),TEXT("ColdSteelWarehouseAudit"));
            if(!GetPawn()||(!Audit&&UGameplayStatics::GetCurrentLevelName(this,true)!=TEXT("DayNight_Lighting")))return;
            bool Exists=false;for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It)if(!Cast<AColdSteelCrateChest>(*It)){Exists=true;break;}
            if(!Exists){
                // 固定生成：锚点取地图 PlayerStart（与 GameMode 出生同一数据源），位置由关卡与
                // Content/ColdSteelData/warehouse_assets.json 的 spawn 段决定。不再读取玩家当前
                // 站位与视角，所以每次进入游戏的落点一致；只有关卡没有 PlayerStart 时才退回旧口径。
                FVector Where;FRotator Facing;FString Source;
                if(AColdSteelWarehouseChest::ResolveFixedSpawn(GetWorld(),GetPawn(),Where,Facing,Source))
                {
                    GetWorld()->SpawnActor<AColdSteelWarehouseChest>(Where,Facing);
                    UE_LOG(LogTemp,Display,TEXT("WarehouseChest: fixed spawn %s facing %s (anchor=%s)"),*Where.ToString(),*Facing.ToString(),*Source);
                }
                else UE_LOG(LogTemp,Warning,TEXT("WarehouseChest: fixed spawn unresolved; chest not placed"));
            }
            // 五档储物箱：宝箱右侧成排固定生成（同朝向，间距 170cm），复用仓库面板与开合动画；
            // 仓库审计流程保持原有场景，不自动加箱子。
            if(!Audit){bool HasCrates=false;for(TActorIterator<AColdSteelCrateChest> It(GetWorld());It;++It){HasCrates=true;break;}
                if(!HasCrates)for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It)
                    if(auto* Anchor=*It;Anchor&&!Cast<AColdSteelCrateChest>(Anchor))
                    {
                        int32 Placed=0;
                        for(int32 Slot=0;Slot<5;++Slot)if(AColdSteelCrateChest::SpawnBeside(GetWorld(),Anchor,static_cast<EColdSteelCrateTier>(Slot),0.f,190.f+170.f*Slot))++Placed;
                        UE_LOG(LogTemp,Display,TEXT("CrateChest: storage row beside %s placed %d/5"),*Anchor->GetName(),Placed);
                        break;
                    }
            }
            if(Audit)ColdSteelHUD->RunWarehouseAudit();
        },3.f,false);
        // The persistent HUD is display-only until the inventory is opened.
        // Activating a focusable CommonUI root here steals keyboard and mouse
        // input from the possessed character at PIE startup.
        SetInputMode(FInputModeGameOnly());
        bShowMouseCursor = false;

        // Deterministic visual acceptance route. It is inert in normal play and
        // exercises the same PlayerController InputKey path as a physical Tab press.
        if (FParse::Param(FCommandLine::Get(), TEXT("ColdSteelUIAudit")))
        {
            GetWorldTimerManager().SetTimerForNextTick([this]()
            {
                InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::Tab, IE_Pressed, 1.0f));
                FTimerHandle CaptureTimer;
                GetWorldTimerManager().SetTimer(CaptureTimer, []()
                {
                    const FString Directory = FPaths::ProjectSavedDir() / TEXT("UIAudit/2026-09-09");
                    IFileManager::Get().MakeDirectory(*Directory, true);
                    FScreenshotRequest::RequestScreenshot(Directory / TEXT("ue-backpack-runtime.png"), true, false);
                }, 0.75f, false);
            });
        }

        if (FParse::Param(FCommandLine::Get(), TEXT("EventTimelineUIAudit")))
        {
            ColdSteelHUD->SetEventTimelineAuditState(0);
            FTimerHandle CompactTimer;
            GetWorldTimerManager().SetTimer(CompactTimer, [this]()
            {
                CaptureTimelineAudit(TEXT("ue-event-timeline-compact.png"), 0);
            }, 0.8f, false);
            FTimerHandle ExpandedTimer;
            GetWorldTimerManager().SetTimer(ExpandedTimer, [this]()
            {
                CaptureTimelineAudit(TEXT("ue-event-timeline-expanded.png"), 1);
            }, 1.6f, false);
            FTimerHandle DetailsTimer;
            GetWorldTimerManager().SetTimer(DetailsTimer, [this]()
            {
                CaptureTimelineAudit(TEXT("ue-event-timeline-forecast.png"), 2);
            }, 2.4f, false);
        }

        if (FParse::Param(FCommandLine::Get(), TEXT("AttributeEquipmentUIAudit")))
        {
            FTimerHandle StatusTimer;
            GetWorldTimerManager().SetTimer(StatusTimer, [this]()
            {
                CaptureInventoryAudit(TEXT("ue-attribute-panel-1280.png"), 0);
            }, 0.9f, false);
            FTimerHandle EquipmentTimer;
            GetWorldTimerManager().SetTimer(EquipmentTimer, [this]()
            {
                CaptureInventoryAudit(TEXT("ue-equipment-card-1280.png"), 1);
            }, 1.8f, false);
        }
        if (FParse::Param(FCommandLine::Get(), TEXT("ColdSteelUpgradeAudit")))
        {
            FTimerHandle UpgradeTimer;
            GetWorldTimerManager().SetTimer(UpgradeTimer, [this]() { ColdSteelHUD->RunUpgradeAudit(); }, 12.0f, false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelInventoryAudit")))
        {
            FTimerHandle InventoryTimer;
            GetWorldTimerManager().SetTimer(InventoryTimer,[this](){ColdSteelHUD->RunInventoryAudit();},12.f,false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("SmeltingVisualAudit")))
        {
            FTimerHandle SmeltingTimer;
            GetWorldTimerManager().SetTimer(SmeltingTimer,[this](){ColdSteelHUD->RunSmeltingVisualAudit();},12.f,false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelItemTooltipAudit")))
        {
            FTimerHandle TooltipTimer;
            GetWorldTimerManager().SetTimer(TooltipTimer,[this](){ColdSteelHUD->RunItemTooltipAudit();},12.f,false);
        }
    }
    // Automation escape hatch: -ClearwaterNoMenu skips the startup mode menu, which otherwise
    // covers the viewport until a human clicks it. A headless capture run has nobody to click,
    // so every screenshot came back showing the menu+loading overlay rather than the scene --
    // which made a rendering investigation look like a scene that refused to draw.
    if (FParse::Param(FCommandLine::Get(), TEXT("ClearwaterNoMenu")))
    {
        if (auto* Loading = GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        {
            Loading->ReleaseToGameplay();
        }
        return;
    }
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())Loading->ShowStartupMenu(this);
}

void AFPSGAMEPlayerController::SetupInputComponent()
{
    // Bind at the controller layer so CommonUI and Enhanced Input cannot hide the drawer shortcut.
    Super::SetupInputComponent();
    if (InputComponent)
    {
        InputComponent->BindKey(EKeys::LeftAlt, IE_Pressed, this, &AFPSGAMEPlayerController::ToggleTimelineInteraction);
    }
}

bool AFPSGAMEPlayerController::InputKey(const FInputKeyEventArgs& Params)
{
    // Action handlers own inspection interruption. Raw keys and look/move axes
    // also describe ordinary locomotion, empty shortcuts and UI-only input.
    if(ColdSteelHUD&&ColdSteelHUD->HandleGunAssemblyInput(Params))return true;
    if(ColdSteelHUD&&ColdSteelHUD->HandleWorldForgeInput(Params))return true;
    if (ExpeditionPanel)
    {
        if (Params.Event == IE_Pressed && Params.Key == EKeys::Escape) CloseExpedition();
        return true;
    }
    if(auto* AmmoPawn=Cast<AFPSGAMECharacter>(GetPawn());AmmoPawn&&AmmoPawn->IsAmmoWheelOpen())
    {
        if(Params.Key==EKeys::Escape){if(Params.Event==IE_Pressed)AmmoPawn->CancelAmmoSelection();return true;}
        if(Params.Key==EKeys::MouseScrollUp||Params.Key==EKeys::MouseScrollDown)AmmoPawn->CancelAmmoSelection();
        // 手别由鼠标所在圆盘决定（双持弹两个盘），点击只吞掉，避免选弹时开火。
        if(Params.Key==EKeys::LeftMouseButton||Params.Key==EKeys::RightMouseButton)return true;
    }
    if(ColdSteelHUD&&ColdSteelHUD->IsQuickDragging())
    {
        if(Params.Event==IE_Pressed&&Params.Key==EKeys::Escape)ColdSteelHUD->CancelQuickDrag();
        return Params.Event==IE_Released?Super::InputKey(Params):true;
    }
    // UI has already received this event; do not forward unhandled cursor clicks to gameplay.
    if (bShowMouseCursor && Params.Key.IsMouseButton() && Params.Event != IE_Released) return true;
    if (Params.Event == IE_Pressed && Params.Key == EKeys::F6) { ToggleDevelopmentPanel(); return true; }
    if (WeatherPanel && WeatherPanel->IsPanelOpen())
    {
        if (Params.Event == IE_Pressed && Params.Key == EKeys::Escape) WeatherPanel->SetPanelOpen(false);
        return Params.Event == IE_Released ? Super::InputKey(Params) : true;
    }
    const bool BuildMenuOpen=GunsmithPanel||(WeatherPanel&&WeatherPanel->IsPanelOpen())||(ColdSteelHUD&&ColdSteelHUD->IsInventoryOpen());
    if(BuildMenuOpen&&Params.Event==IE_Pressed)
        UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL BuildMenuOpen 来源 gunsmith=%d devpanel=%d inventory=%d key=%s"),
            GunsmithPanel?1:0,(WeatherPanel&&WeatherPanel->IsPanelOpen())?1:0,
            (ColdSteelHUD&&ColdSteelHUD->IsInventoryOpen())?1:0,*Params.Key.ToString());
    if(VoxelBuilder&&VoxelBuilder->HandleInput(Params,BuildMenuOpen))return true;
    if(EnhancementPanel){if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::K||Params.Key==EKeys::Tab))CloseEnhancement();return true;}
    if(Params.Event==IE_Pressed&&Params.Key==EKeys::K){OpenEnhancement();return true;}
    if(GunsmithPanel)
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::J||Params.Key==EKeys::Tab))CloseGunsmith();
        return true;
    }
    if(Params.Event==IE_Pressed&&Params.Key==EKeys::J){OpenGunsmith();return true;}
    if ((Params.Event == IE_Pressed || Params.Event == IE_Repeat) && ColdSteelHUD &&
        ColdSteelHUD->HandlePanelShortcut(Params.Key, Params.Event == IE_Repeat))
    {
        return true;
    }
    // Magic hold-to-preview consumes its own release: pressing a bound slot while its
    // projectile hovers shows the red trajectory instead of firing, and letting go fires it.
    if(Params.Event==IE_Released&&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        const int32 QuickIndex=ColdSteelQuickBar::KeyIndex(Params.Key);
        if(QuickIndex>=0)
        {
            auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            if(Profile&&Profile->EndSpellAimPreview(QuickIndex))return true;
        }
    }
    if(Params.Event==IE_Pressed&&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        if(Params.Key==EKeys::MouseScrollUp||Params.Key==EKeys::MouseScrollDown)
            if(auto* C=Cast<AFPSGAMECharacter>(GetPawn());C&&C->AdjustOpticMagnification(Params.Key==EKeys::MouseScrollUp?.5f:-.5f))return true;
        auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto InterruptInspection=[this]()
        {
            if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->InterruptWeaponInspection();
        };
        if(Params.Key==EKeys::Eight){Profile->SelectProductionTool(TEXT("tool_shovel"));return true;}
        if(Params.Key==EKeys::F7){Profile->StowProductionTool();return true;}
        // G 已让位给符文长剑·环绕飞剑（角色 BindAction "RuneBlades"），武器轮换只留滚轮。
        if(Params.Key==EKeys::MouseScrollUp || Params.Key==EKeys::MouseScrollDown)
        {Profile->CycleWeapon();return true;}
        if(Params.Key==EKeys::E&&GetPawn())
        {
            auto* Target=ColdSteelWorldInteraction::TraceTarget(this);
            if(ColdSteelWorldInteraction::IsExpeditionAltar(Target)){OpenExpedition();return true;}
            if(ColdSteelWorldInteraction::IsBlessingFountain(Target)){InterruptInspection();ColdSteelWorldInteraction::DrinkFromFountain(this,Target);return true;}
            if(auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&Run->IsShrine(Target)){InterruptInspection();Run->ClaimShrine(this,Target);return true;}
            if(ColdSteelWorldInteraction::IsTreasureChest(Target)){InterruptInspection();ColdSteelWorldInteraction::OpenTreasureChest(this,Target);return true;}
            if(auto* Container=ColdSteelWorldInteraction::FocusedSceneContainer(this)){InterruptInspection();Container->TrySearch(this);return true;}
            if(auto* Chest=Cast<AColdSteelWarehouseChest>(Target);Chest&&ColdSteelHUD){ColdSteelHUD->OpenWarehouse(Chest);return true;}
            if(auto* Pickup=Cast<AColdSteelPickup>(Target)){InterruptInspection();Profile->Pickup(Pickup->ItemId);return true;}
            if(auto* Arrow=Cast<ABowArrow>(Target)){InterruptInspection();Arrow->TryRecover(GetPawn());return true;}
            // 冶炼高炉：E 同时打开背包与独立冶炼面板（面板贴抽屉左侧，可被 Esc／× 单独关闭；炉内按真实时间继续冶炼）。
            // 放在门判定之前：高炉不是门，但两者都靠"命中 Actor 是什么"分派，先特异后泛化。
            if(ColdSteelWorldInteraction::IsForgingStation(Target)&&ColdSteelHUD)
            {ColdSteelHUD->OpenForging(Target);return true;}
            if(ColdSteelWorldInteraction::IsSmeltingFurnace(Target)&&ColdSteelHUD)
            {ColdSteelHUD->OpenSmelting(Target);return true;}
            // 工作台：E 同时打开背包与制作面板（格式复刻冶炼面板，制作内容后续设计；
            // Docs/UI/workbench-panel-plan-20260924.md）。与高炉判定并列、互斥同贴位。
            if(ColdSteelWorldInteraction::IsWorkbench(Target)&&ColdSteelHUD)
            {ColdSteelHUD->OpenWorkbench(Target);return true;}
            // Door System 的门：准星命中后按门自己的交互入口开门／关门（隐藏玩家代理在子系统里维护）。
            if(Target&&UColdSteelDoorInteraction::IsDoor(Target))
            {
                if(auto* Doors=GetWorld()?GetWorld()->GetSubsystem<UColdSteelDoorInteraction>():nullptr)
                {
                    FString Entry;
                    InterruptInspection();
                    // 开关门保持安静：不占提示栏、也不触发提示栏的音效；入口名仍然写日志便于排查。
                    Doors->TryInteract(Target,GetPawn(),Entry);
                    return true;
                }
            }
            // Nearby portals receive E through their existing input component before a bound skill.
            for(TActorIterator<ASceneTestPortal> It(GetWorld());It;++It)if(It->IsWithinInteractionRange(GetPawn())){InterruptInspection();return Super::InputKey(Params);}
        }
        // Z: one key picks up every drop around the player (blocks, equipment, materials). Ctrl+Z is
        // the build undo and is consumed by the building component before it reaches this branch.
        if(Params.Key==EKeys::Z&&GetPawn()&&!IsInputKeyDown(EKeys::LeftControl)&&!IsInputKeyDown(EKeys::RightControl))
        {Profile->PickupNearby(AreaPickupRadiusCm.GetValueOnGameThread());return true;}
        const int32 QuickIndex=ColdSteelQuickBar::KeyIndex(Params.Key);
        if(QuickIndex>=0)
        {
            const auto Binding=Profile->QuickBinding(QuickIndex);
            // Dodge shares the locomotion policy even when triggered by a skill slot.
            if(!Binding.IsEmpty()&&Binding.Skill!=TEXT("dodge"))InterruptInspection();
            if(Profile->BeginSpellAimPreview(QuickIndex))return true;
            Profile->UseQuickBinding(QuickIndex);return true;
        }
    }
    return Super::InputKey(Params);
}

void AFPSGAMEPlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if(IsLocalController()&&!ExpeditionPanel&&!GunsmithPanel&&!EnhancementPanel
        &&(!ColdSteelHUD||(!ColdSteelHUD->IsWorldForging()&&!ColdSteelHUD->IsGunAssembly()))
        &&(!WeatherPanel||!WeatherPanel->IsPanelOpen())
        &&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        auto* VP=GetWorld()?GetWorld()->GetGameViewport():nullptr;
        const bool bInputHeld=(VP&&VP->IgnoreInput())||IsMoveInputIgnored()||IsLookInputIgnored()
            ||(bShowMouseCursor&&!IsCursorOnlyInteraction());
        if(bInputHeld&&UGameplayStatics::GetCurrentLevelName(this,true)==TEXT("L_Dungeon_Randomized"))
        {
            bool bDungeonReady=false;
            for(TActorIterator<AActor> It(GetWorld());It;++It)
                if(It->ActorHasTag(TEXT("DungeonAssembly.Ready"))){bDungeonReady=true;break;}
            if(auto* Loading=GetGameInstance()?GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
                bDungeonReady&&Loading&&!Loading->IsHoldingGameplayInput())
                Loading->ReleaseToGameplay();
        }
    }
    const auto* ScopeCharacter=Cast<AFPSGAMECharacter>(GetPawn());
    const bool Hide=IsLocalController()&&!bShowMouseCursor&&ScopeCharacter&&ScopeCharacter->GetScopePresentationAlpha()>.5f;
    if(Hide==bScopePanelsHidden)return;
    bScopePanelsHidden=Hide;
    if(Hide){
        TArray<UUserWidget*> Panels;
        UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this,Panels,UUserWidget::StaticClass(),true);
        for(auto* Panel:Panels)if(Panel!=ScopeOverlay&&Panel->GetOwningPlayer()==this){
            ScopePanelVisibility.Add(Panel,static_cast<uint8>(Panel->GetVisibility()));
            Panel->SetVisibility(ESlateVisibility::Hidden);
        }
    }else{
        for(const auto& Entry:ScopePanelVisibility)if(Entry.Key.IsValid())Entry.Key->SetVisibility(static_cast<ESlateVisibility>(Entry.Value));
        ScopePanelVisibility.Reset();
    }
}

void AFPSGAMEPlayerController::ToggleInventory()
{
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) WeatherPanel->SetPanelOpen(false);
    if (ColdSteelHUD)
    {
        ColdSteelHUD->ToggleInventory();
        UE_LOG(LogTemp, Display, TEXT("ColdSteelUI: inventory toggled, open=%s"),
            ColdSteelHUD->IsInventoryOpen() ? TEXT("true") : TEXT("false"));
    }
}

bool AFPSGAMEPlayerController::IsCursorOnlyInteraction() const
{
    return bShowMouseCursor && !IsMoveInputIgnored() && !IsLookInputIgnored() &&
        !GunsmithPanel && !EnhancementPanel && !ExpeditionPanel && (!WeatherPanel || !WeatherPanel->IsPanelOpen()) &&
        ColdSteelHUD && !ColdSteelHUD->IsInventoryOpen() && (!VoxelBuilder || !VoxelBuilder->IsPanelOpen());
}

bool AFPSGAMEPlayerController::BlocksOngoingActions(const APlayerController* Player)
{
    if(!Player || Player->IsMoveInputIgnored() || Player->IsLookInputIgnored())return true;
    const auto* FPSPlayer=Cast<AFPSGAMEPlayerController>(Player);
    return Player->bShowMouseCursor && (!FPSPlayer || !FPSPlayer->IsCursorOnlyInteraction());
}

void AFPSGAMEPlayerController::ToggleTimelineInteraction()
{
    if(ColdSteelHUD&&(ColdSteelHUD->IsWorldForging()||ColdSteelHUD->IsGunAssembly()))return;
    if (GunsmithPanel || EnhancementPanel || ExpeditionPanel) return;
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) return;
    if (!ColdSteelHUD || ColdSteelHUD->IsInventoryOpen()) return;
    if (bShowMouseCursor)
    {
        bShowMouseCursor = false;
        SetInputMode(FInputModeGameOnly());
        return;
    }
    bShowMouseCursor = true;
    FInputModeGameAndUI InputMode;
    // Keep keyboard focus in the viewport. Cursor clicks still reach the HUD,
    // without a focus transfer synthesizing releases of held combat inputs.
    InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    InputMode.SetHideCursorDuringCapture(false);
    SetInputMode(InputMode);
}

void AFPSGAMEPlayerController::ToggleWeatherPanel()
{
    ToggleDevelopmentPanel();
}

void AFPSGAMEPlayerController::ToggleDevelopmentPanel()
{
    if (!WeatherPanel) return;
    CloseExpedition();
    if (GunsmithPanel) CloseGunsmith();
    if (EnhancementPanel) CloseEnhancement();
    if (ColdSteelHUD && ColdSteelHUD->IsInventoryOpen()) ColdSteelHUD->ToggleInventory();
    WeatherPanel->SetPanelOpen(!WeatherPanel->IsPanelOpen());
}

void AFPSGAMEPlayerController::CaptureTimelineAudit(const FString& Filename, int32 State)
{
    if (!ColdSteelHUD) return;
    ColdSteelHUD->SetEventTimelineAuditState(State);
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("UIAudit/2026-09-09");
    IFileManager::Get().MakeDirectory(*Directory, true);
    FScreenshotRequest::RequestScreenshot(Directory / Filename, true, false);
}

void AFPSGAMEPlayerController::CaptureInventoryAudit(const FString& Filename, int32 State)
{
    if (!ColdSteelHUD) return;
    ColdSteelHUD->SetInventoryAuditState(State);
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("UIAudit/2026-09-09");
    IFileManager::Get().MakeDirectory(*Directory, true);
    FScreenshotRequest::RequestScreenshot(Directory / Filename, true, false);
}
