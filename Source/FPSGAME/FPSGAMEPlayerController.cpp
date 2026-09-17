#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelQuickBarTypes.h"
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
#include "UI/ColdSteelWorldInteraction.h"
#include "UI/ColdSteelWarehouseChest.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "UI/WeatherControlWidget.h"
#include "UI/DevelopmentPanelWidget.h"
#include "Development/DevelopmentSpawnComponent.h"
#include "UI/WeatherPanelValidation.h"
#include "Components/InputComponent.h"
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

void AFPSGAMEPlayerController::BeginPlay()
{
    Super::BeginPlay();
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
            bool Exists=false;for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It){Exists=true;break;}
            if(!Exists){
                FCollisionQueryParams Query;Query.AddIgnoredActor(GetPawn());
                const FRotator Facing=GetPawn()->GetActorRotation();
                for(float Angle:{60.f,-60.f,120.f,-120.f,0.f,180.f}){
                    FVector P=GetPawn()->GetActorLocation()+Facing.Vector().RotateAngleAxis(Angle,FVector::UpVector)*190;
                    FHitResult Ground;
                    if(!GetWorld()->LineTraceSingleByChannel(Ground,P+FVector(0,0,100),P-FVector(0,0,500),ECC_Visibility,Query)||Ground.ImpactNormal.Z<.8f)continue;
                    P=Ground.ImpactPoint+FVector(0,0,2);
                    if(GetWorld()->OverlapBlockingTestByChannel(P+FVector(0,0,68),Facing.Quaternion(),ECC_Pawn,FCollisionShape::MakeBox(FVector(58,76,65)),Query))continue;
                    if(GetWorld()->SpawnActor<AColdSteelWarehouseChest>(P,Facing))break;
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
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelItemTooltipAudit")))
        {
            FTimerHandle TooltipTimer;
            GetWorldTimerManager().SetTimer(TooltipTimer,[this](){ColdSteelHUD->RunItemTooltipAudit();},12.f,false);
        }
    }
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
        if(Params.Key==EKeys::Six){Profile->SelectProductionTool(TEXT("tool_axe"));return true;}
        if(Params.Key==EKeys::Seven){Profile->SelectProductionTool(TEXT("tool_pickaxe"));return true;}
        if(Params.Key==EKeys::Eight){Profile->SelectProductionTool(TEXT("tool_shovel"));return true;}
        if(Params.Key==EKeys::F7){Profile->StowProductionTool();return true;}
        if(Params.Key==EKeys::G || Params.Key==EKeys::MouseScrollUp || Params.Key==EKeys::MouseScrollDown)
        {if (const auto* C=Cast<AFPSGAMECharacter>(GetPawn()); !C || !C->IsTraversing()) Profile->CycleWeapon();return true;}
        if(Params.Key==EKeys::E&&GetPawn())
        {
            auto* Target=ColdSteelWorldInteraction::TraceTarget(this);
            if(auto* Chest=Cast<AColdSteelWarehouseChest>(Target);Chest&&ColdSteelHUD){ColdSteelHUD->OpenWarehouse(Chest);return true;}
            if(auto* Pickup=Cast<AColdSteelPickup>(Target)){Profile->Pickup(Pickup->ItemId);return true;}
            // Door System 的门：准星命中后按门自己的交互入口开门／关门（隐藏玩家代理在子系统里维护）。
            if(Target&&UColdSteelDoorInteraction::IsDoor(Target))
            {
                if(auto* Doors=GetWorld()?GetWorld()->GetSubsystem<UColdSteelDoorInteraction>():nullptr)
                {
                    FString Entry;
                    // 开关门保持安静：不占提示栏、也不触发提示栏的音效；入口名仍然写日志便于排查。
                    Doors->TryInteract(Target,GetPawn(),Entry);
                    return true;
                }
            }
            // Nearby portals receive E through their existing input component before a bound skill.
            for(TActorIterator<ASceneTestPortal> It(GetWorld());It;++It)if(It->IsWithinInteractionRange(GetPawn()))return Super::InputKey(Params);
        }
        // Z: one key picks up every drop around the player (blocks, equipment, materials). Ctrl+Z is
        // the build undo and is consumed by the building component before it reaches this branch.
        if(Params.Key==EKeys::Z&&GetPawn()&&!IsInputKeyDown(EKeys::LeftControl)&&!IsInputKeyDown(EKeys::RightControl))
        {Profile->PickupNearby(AreaPickupRadiusCm.GetValueOnGameThread());return true;}
        const int32 QuickIndex=ColdSteelQuickBar::KeyIndex(Params.Key);
        if(QuickIndex>=0)
        {
            if(Profile->BeginSpellAimPreview(QuickIndex))return true;
            Profile->UseQuickBinding(QuickIndex);return true;
        }
    }
    return Super::InputKey(Params);
}

void AFPSGAMEPlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
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

void AFPSGAMEPlayerController::ToggleTimelineInteraction()
{
    if (GunsmithPanel || EnhancementPanel) return;
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
    InputMode.SetWidgetToFocus(ColdSteelHUD->TakeWidget());
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
