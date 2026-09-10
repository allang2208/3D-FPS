#include "FPSGAMEPlayerController.h"
#include "FPSGAMECharacter.h"

#include "UI/ColdSteelHUDWidget.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelPickup.h"
#include "UI/ColdSteelWorldInteraction.h"
#include "UI/ColdSteelWarehouseChest.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "UI/WeatherControlWidget.h"
#include "UI/WeatherPanelValidation.h"
#include "Components/InputComponent.h"
#include "HAL/FileManager.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "UnrealClient.h"

void RunRetiredWeaponsAudit(AFPSGAMEPlayerController* PC);
void RunWorldInteractionAudit(AFPSGAMEPlayerController* PC);

AFPSGAMEPlayerController::AFPSGAMEPlayerController()
{
    bShowMouseCursor = false;
}

void AFPSGAMEPlayerController::BeginPlay()
{
    Super::BeginPlay();
    if(FParse::Param(FCommandLine::Get(),TEXT("WorldInteractionAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunWorldInteractionAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("GunsmithWorkbenchAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunGunsmithWorkbenchAudit,5.f,false);}
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

    WeatherPanel = CreateWidget<UWeatherControlWidget>(this, UWeatherControlWidget::StaticClass());
    if (WeatherPanel) WeatherPanel->AddToPlayerScreen(40);
    StartWeatherPanelValidation(this, WeatherPanel);
    ColdSteelHUD = CreateWidget<UColdSteelHUDWidget>(this, UColdSteelHUDWidget::StaticClass());
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
        InputComponent->BindKey(EKeys::LeftAlt, IE_Pressed, this, &AFPSGAMEPlayerController::BeginTimelineInteraction);
        InputComponent->BindKey(EKeys::LeftAlt, IE_Released, this, &AFPSGAMEPlayerController::EndTimelineInteraction);
    }
}

bool AFPSGAMEPlayerController::InputKey(const FInputKeyEventArgs& Params)
{
    if(GunsmithPanel)
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::J||Params.Key==EKeys::Tab))CloseGunsmith();
        return true;
    }
    if(Params.Event==IE_Pressed&&Params.Key==EKeys::J){OpenGunsmith();return true;}
    if (Params.Event == IE_Pressed && Params.Key == EKeys::F6)
    {
        ToggleWeatherPanel();
        return true;
    }
    if (WeatherPanel && WeatherPanel->IsPanelOpen())
        return Params.Event == IE_Released ? Super::InputKey(Params) : true;
    if ((Params.Event == IE_Pressed || Params.Event == IE_Repeat) && ColdSteelHUD &&
        ColdSteelHUD->HandlePanelShortcut(Params.Key, Params.Event == IE_Repeat))
    {
        return true;
    }
    if(Params.Event==IE_Pressed&&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(Params.Key==EKeys::G){Profile->CycleWeapon();return true;}
        const FKey Keys[]={EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four};
        for(int32 Index=0;Index<4;++Index)if(Params.Key==Keys[Index]){Profile->UseHotbar(Index);return true;}
        if(Params.Key==EKeys::E&&GetPawn())
        {
            auto* Target=ColdSteelWorldInteraction::TraceTarget(this);
            if(auto* Chest=Cast<AColdSteelWarehouseChest>(Target);Chest&&ColdSteelHUD){ColdSteelHUD->OpenWarehouse(Chest);return true;}
            if(auto* Pickup=Cast<AColdSteelPickup>(Target)){Profile->Pickup(Pickup->ItemId);return true;}
        }
    }
    return Super::InputKey(Params);
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

void AFPSGAMEPlayerController::BeginTimelineInteraction()
{
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) return;
    if (!ColdSteelHUD || ColdSteelHUD->IsInventoryOpen()) return;
    bShowMouseCursor = true;
    FInputModeGameAndUI InputMode;
    InputMode.SetWidgetToFocus(ColdSteelHUD->TakeWidget());
    InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    InputMode.SetHideCursorDuringCapture(false);
    SetInputMode(InputMode);
}

void AFPSGAMEPlayerController::EndTimelineInteraction()
{
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) return;
    if (!ColdSteelHUD || ColdSteelHUD->IsInventoryOpen()) return;
    bShowMouseCursor = false;
    SetInputMode(FInputModeGameOnly());
}

void AFPSGAMEPlayerController::ToggleWeatherPanel()
{
    if (!WeatherPanel) return;
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
