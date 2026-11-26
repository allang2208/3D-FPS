#include "TransitLoadingSubsystem.h"
#include "../WorldGeneration/ForestVillageMap.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GameResourcePreparation.h"
#include "../Skills/PlayerSkillPreparation.h"
#include "Brushes/SlateDynamicImageBrush.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "RHI.h"
#include "RHIStats.h"
#include "Framework/Application/SlateApplication.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"
#include "MoviePlayer.h"
#include "ShaderPipelineCache.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Styling/CoreStyle.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "CommonActivatableWidget.h"
#include "Dom/JsonObject.h"
#include "Engine/LocalPlayer.h"
#include "Framework/Application/SlateUser.h"
#include "Input/CommonUIActionRouterBase.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"
#include "Widgets/SViewport.h"


#include "TransitLoadingViewPrivate.h"

namespace TransitLoading
{
class STransitLoadingRoot : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(STransitLoadingRoot) {}
        SLATE_ARGUMENT(TSharedPtr<FTransitLoadingView>, View)
        SLATE_DEFAULT_SLOT(FArguments, Content)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args) { State=Args._View;ChildSlot[Args._Content.Widget]; }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry&,const FKeyEvent& Event) override
    {
        if(Event.GetKey()==EKeys::Escape&&State){State->CancelRequested=true;return FReply::Handled();}
        return FReply::Unhandled();
    }
private:
    TSharedPtr<FTransitLoadingView> State;
};


TSharedRef<SWidget> MakeView(const TSharedRef<FTransitLoadingView>& State, bool Interactive)
{
    // The MoviePlayer uses a separate, immutable snapshot: no UObject access or
    // shared mutable UI attributes from its loading thread.
    auto Content = SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("TRANSIT ARCHIVE")))
            .Font(ColdSteelUI::NumberFont(9)).ColorAndOpacity(ColdSteelUI::TextTertiary).Justification(ETextJustify::Center)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,20)[SNew(STextBlock).Text_Lambda([State](){return State->Title;})
            .Font(ColdSteelUI::TextFont(20,true)).ColorAndOpacity(ColdSteelUI::TextPrimary).Justification(ETextJustify::Center)]
        +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(14)[SNew(SProgressBar)
            .FillColorAndOpacity(ColdSteelUI::Accent)
            .Percent_Lambda([State,Interactive]()->TOptional<float>{return Interactive?TOptional<float>(State->Progress):TOptional<float>();})]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,10)[SNew(STextBlock)
            .Text_Lambda([State,Interactive](){return Interactive?FText::AsPercent(State->Progress):FText::FromString(TEXT("正在切换场景…"));})
            .Font(ColdSteelUI::NumberFont(13)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([State](){return State->Status;})
            .Font(ColdSteelUI::TextFont(11)).WrapTextAt(392).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)];
    if(Interactive)
    {
        Content->AddSlot().AutoHeight().Padding(0,12,0,0)[SNew(STextBlock)
            .Text_Lambda([State](){return FText::FromString(FString::Printf(TEXT("已等待 %.0f 秒"),FPlatformTime::Seconds()-State->Start));})
            .Font(ColdSteelUI::NumberFont(9)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextTertiary)];
        Content->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0,14,0,0)[SNew(SButton).ButtonStyle(&State->Button)
            .OnClicked_Lambda([State](){State->CancelRequested=true;return FReply::Handled();})
            [SNew(STextBlock).Text_Lambda([State](){return FText::FromString(State->ReturnToMenu?TEXT("返回主界面"):TEXT("取消 / 返回主场景"));}).Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
        Content->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0,8,0,0)
            [SNew(SButton).ButtonStyle(&State->Button)
                .Visibility_Lambda([State](){return State->RetryAvailable?EVisibility::Visible:EVisibility::Collapsed;})
                .OnClicked_Lambda([State](){State->RetryRequested=true;return FReply::Handled();})
                [SNew(STextBlock).Text(FText::FromString(TEXT("重试资源准备"))).Font(ColdSteelUI::TextFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextPrimary)]];
    }
    TSharedRef<SWidget> Layout=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.008f,.008f,.008f,1))]
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(State->Background.Get())]]
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0,0,0,.55f))]
        +SOverlay::Slot().Padding(24).HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)
            [SNew(SBox).WidthOverride(440)[SNew(SBorder).BorderImage(&State->Panel).Padding(24)[Content]]]];
    if(Interactive)return SNew(STransitLoadingRoot).View(State)[Layout];
    return Layout;
}
}

void UTransitLoadingSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    if(IsRunningCommandlet()||IsRunningDedicatedServer())return;
    Collection.InitializeDependency<UColdSteelStatusModel>();
    int32 SavedMode=0;
    GConfig->GetInt(TEXT("FPSGAME.Loading"),TEXT("Mode"),SavedMode,GGameUserSettingsIni);
    bCompletePreload=SavedMode==1;
    FString Mode;
    if(FParse::Value(FCommandLine::Get(),TEXT("GameLoadingMode="),Mode))
    {bCompletePreload=Mode.Equals(TEXT("Complete"),ESearchCase::IgnoreCase);bStartupChosen=true;}
    else if(FParse::Param(FCommandLine::Get(),TEXT("SkipStartupMenu"))) {bStartupChosen=true;bCompletePreload=false;}
    // 进程级全局委托：PIE 单进程多实例（服务器+各客户端 GameInstance）全部会收到。
    // 必须按 WorldContext.OwningGameInstance 过滤——否则客户端的旅行会给服务器窗口
    // 也挂一层遮罩且 bMapLoading 被永久锁真（AfterMap 有 GI 过滤，BeforeMap 原本没有），
    // 表现就是"N 人时恒有一个窗口卡在 0% 且不吃输入"。
    PreMapHandle=FCoreUObjectDelegates::PreLoadMapWithContext.AddUObject(this,&ThisClass::BeforeMap);
    PostMapHandle=FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this,&ThisClass::AfterMap);
    if(GEngine)
    {
        // 联机失败（连不上/被踢/掉线/travel 失败）→ 重置启动态，回默认图后自动重弹主菜单。
        NetworkFailureHandle=GEngine->OnNetworkFailure().AddLambda(
            [this](UWorld* W,UNetDriver*,ENetworkFailure::Type,const FString& Err)
            {
                // A guest timing out must not put the listen host back into startup mode.
                if(W&&(W->GetNetMode()==NM_ListenServer||W->GetNetMode()==NM_DedicatedServer))return;
                OnNetFailure(W,Err);
            });
        TravelFailureHandle=GEngine->OnTravelFailure().AddLambda(
            [this](UWorld* W,ETravelFailure::Type,const FString& Err){OnNetFailure(W,Err);});
    }
}

void UTransitLoadingSubsystem::BeginTransition(const FString& Map, FSimpleDelegate OnCancel)
{
    if(IsRunningCommandlet()||!FSlateApplication::IsInitialized())return;
    if(View)CancelTransition();
    bRoomTransition=false;
    ResourcePreparation.Reset();ReleasePreparedPlayer();
    if(SkillPreparation)SkillPreparation->Cancel();
    bSkillPreparationStarted=false;
    bScenePrepared=false;bPreparationFailed=false;
    bHills=(Map.Contains(TEXT("L_TemperateHills_Initial")) || Map.Contains(ForestVillageMap::Name));
    bDungeon=Map.Contains(TEXT("L_Dungeon_Randomized"));
    bDestinationLoaded=false;
    StartedAt=FPlatformTime::Seconds();FinishedAt=0;
    CancelAction=MoveTemp(OnCancel);
    View=MakeShared<FTransitLoadingView>();View->Start=StartedAt;
    View->ReturnToMenu=false;
    View->Title=FText::FromString(bHills?TEXT("正在进入温带丘陵…"):bDungeon?TEXT("正在进入地牢…"):TEXT("正在切换场景…"));
    View->Status=FText::FromString(TEXT("正在准备场景资源…"));
    const FString File=FPaths::ProjectContentDir()/TEXT("UI/TransitLoading")/FString::Printf(TEXT("gaia-fertile-lands-%d.png"),FMath::RandRange(1,2));
    if(FPaths::FileExists(File))View->Background=MakeShared<FSlateDynamicImageBrush>(FName(*File),FVector2D(1672,941));
    AttachOverlay(true);
}

void UTransitLoadingSubsystem::BeginRoomTransition(FSimpleDelegate OnCancel)
{
    BeginTransition(TEXT("L_Dungeon_Randomized"),MoveTemp(OnCancel));
    bRoomTransition=true;
}
void UTransitLoadingSubsystem::FinishRoomTransition()
{
    if(!bRoomTransition)return;
    bScenePrepared=true;bPreparationFailed=false;
    // The authority already waited for local assembly. Do not restart whole-world preload.
    FinishPreparation();
}

void UTransitLoadingSubsystem::AttachOverlay(bool bRememberViewportIgnore)
{
    auto* VP=GetGameInstance()->GetGameViewportClient();
    if(!VP||!View||Overlay)return;
    if(bRememberViewportIgnore)bPreviousIgnoreInput=VP->IgnoreInput();
    VP->SetIgnoreInput(true);AttachedViewport=VP;
    Overlay=TransitLoading::MakeView(View.ToSharedRef(),true);
    VP->AddViewportWidgetContent(Overlay.ToSharedRef(),100000);
    CaptureLoadingInput();
}

void UTransitLoadingSubsystem::DetachOverlayWidget()
{
    if(auto* VP=AttachedViewport.Get())
    {
        if(Overlay)VP->RemoveViewportWidgetContent(Overlay.ToSharedRef());
    }
    Overlay.Reset();
}

void UTransitLoadingSubsystem::CaptureLoadingInput()
{
    if(auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0))
    {
        // Team entry can start while this local player is browsing the M map.
        // Release its input locks and restore its HUD before loading takes focus.
        if (auto* GamePC=Cast<AFPSGAMEPlayerController>(PC)) GamePC->CloseGameMenu();
        if(CursorController.Get()!=PC)
        {
            CursorController=PC;
            bPreviousCursor=PC->bShowMouseCursor;
        }
        PC->bShowMouseCursor=true;
        FInputModeUIOnly Mode;
        if(Overlay)Mode.SetWidgetToFocus(Overlay);
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        PC->SetInputMode(Mode);
    }
    if(Overlay&&FSlateApplication::IsInitialized())
        FSlateApplication::Get().SetAllUserFocus(Overlay,EFocusCause::SetDirectly);
}

void UTransitLoadingSubsystem::RestoreGameplayInput()
{
    if(auto* VP=GetGameInstance()?GetGameInstance()->GetGameViewportClient():nullptr)
        VP->SetIgnoreInput(false);
    auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0);
    if(!PC)PC=CursorController.Get();
    if(PC)
    {
        PC->ResetIgnoreInputFlags();
        PC->bShowMouseCursor=false;
        PC->SetInputMode(FInputModeGameOnly());
        if(APawn* Pawn=PC->GetPawn())
        {
            Pawn->EnableInput(PC);
            if(auto* Character=Cast<ACharacter>(Pawn))
                if(auto* Movement=Character->GetCharacterMovement())Movement->SetComponentTickEnabled(true);
        }
        UE_LOG(LogTemp,Display,TEXT("TransitLoading: restore gameplay input map=%s pawn=%s"),
            *UGameplayStatics::GetCurrentLevelName(PC,true),*GetNameSafe(PC->GetPawn()));
    }
    CursorController.Reset();
    if(FSlateApplication::IsInitialized())FSlateApplication::Get().SetAllUserFocusToGameViewport();
#if !UE_BUILD_SHIPPING
    UE_LOG(LogTemp,Display,TEXT("TransitInputState phase=restore %s"),*GetInputRoutingState());
#endif
}

FString UTransitLoadingSubsystem::GetInputRoutingState() const
{
    // Boundary/on-demand observation only: never run a widget-tree scan or
    // force an unlock to make the diagnostic state appear healthy.
    const auto State=MakeShared<FJsonObject>();
    UWorld* World=GetWorld();
    auto* PC=World?UGameplayStatics::GetPlayerController(World,0):nullptr;
    auto* VP=GetGameInstance()?GetGameInstance()->GetGameViewportClient():nullptr;
    auto* LocalPlayer=PC?PC->GetLocalPlayer():nullptr;
    State->SetStringField(TEXT("world"),GetPathNameSafe(World));
    State->SetBoolField(TEXT("paused"),World&&World->IsPaused());
    State->SetBoolField(TEXT("loading_owns_input"),IsHoldingGameplayInput());
    State->SetBoolField(TEXT("startup_overlay"),StartupOverlay.IsValid());
    State->SetBoolField(TEXT("loading_overlay"),Overlay.IsValid());
    State->SetBoolField(TEXT("scene_prepared"),bScenePrepared);
    State->SetBoolField(TEXT("preparation_failed"),bPreparationFailed);
    State->SetStringField(TEXT("controller"),GetPathNameSafe(PC));
    State->SetStringField(TEXT("viewport"),GetPathNameSafe(VP));
    if(PC)
    {
        State->SetBoolField(TEXT("controller_input_enabled"),PC->InputEnabled());
        State->SetBoolField(TEXT("player_input_present"),PC->PlayerInput!=nullptr);
        State->SetBoolField(TEXT("move_ignored"),PC->IsMoveInputIgnored());
        State->SetBoolField(TEXT("look_ignored"),PC->IsLookInputIgnored());
        State->SetBoolField(TEXT("cursor_visible"),PC->bShowMouseCursor);
        State->SetStringField(TEXT("pawn"),GetPathNameSafe(PC->GetPawn()));
        if(APawn* Pawn=PC->GetPawn())State->SetBoolField(TEXT("pawn_input_enabled"),Pawn->InputEnabled());
    }
    if(VP)
    {
        State->SetBoolField(TEXT("viewport_ignore_input"),VP->IgnoreInput());
        State->SetNumberField(TEXT("viewport_capture_mode"),static_cast<int32>(VP->GetMouseCaptureMode()));
        if(VP->Viewport)
        {
            State->SetBoolField(TEXT("viewport_has_focus"),VP->Viewport->HasFocus());
            State->SetBoolField(TEXT("viewport_has_capture"),VP->Viewport->HasMouseCapture());
        }
    }
    if(auto* Router=LocalPlayer?LocalPlayer->GetSubsystem<UCommonUIActionRouterBase>():nullptr)
    {
        const ECommonInputMode Mode=Router->GetActiveInputMode();
        State->SetStringField(TEXT("common_ui_mode"),Mode==ECommonInputMode::Menu?TEXT("Menu"):
            Mode==ECommonInputMode::Game?TEXT("Game"):TEXT("All"));
        State->SetStringField(TEXT("common_ui_leaf"),GetPathNameSafe(Router->GetLeafmostActivatableWidget()));
        State->SetBoolField(TEXT("common_ui_tree_pending"),Router->IsPendingTreeChange());
        if(FSlateApplication::IsInitialized())
            State->SetBoolField(TEXT("common_ui_allows_game_input"),Router->CanProcessNormalGameInput());
    }
    if(FSlateApplication::IsInitialized())
    {
        const auto Describe=[](const TSharedPtr<SWidget>& Widget)
        {return Widget?Widget->ToString():FString(TEXT("None"));};
        auto& Slate=FSlateApplication::Get();
        State->SetBoolField(TEXT("application_active"),Slate.IsActive());
        State->SetStringField(TEXT("keyboard_focus"),Describe(Slate.GetKeyboardFocusedWidget()));
        if(auto User=LocalPlayer?LocalPlayer->GetSlateUser():nullptr)
        {
            State->SetNumberField(TEXT("slate_user"),User->GetUserIndex());
            State->SetStringField(TEXT("user_focus"),Describe(User->GetFocusedWidget()));
            State->SetStringField(TEXT("cursor_captor"),Describe(User->GetCursorCaptor()));
            if(VP)
            {
                State->SetBoolField(TEXT("game_viewport_in_focus_path"),User->IsWidgetInFocusPath(VP->GetGameViewportWidget()));
                State->SetBoolField(TEXT("game_viewport_has_cursor_capture"),User->DoesWidgetHaveCursorCapture(VP->GetGameViewportWidget()));
            }
            TArray<TSharedPtr<FJsonValue>> FocusPath;
            auto Widget=User->GetFocusedWidget();
            for(int32 Depth=0;Widget&&Depth<32;++Depth,Widget=Widget->GetParentWidget())
                FocusPath.Add(MakeShared<FJsonValueString>(Describe(Widget)));
            State->SetArrayField(TEXT("focus_path_leaf_to_root"),FocusPath);
        }
    }
    FString Json;
    FJsonSerializer::Serialize(State,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
    return Json;
}

void UTransitLoadingSubsystem::ReleaseToGameplay()
{
    if(StartupOverlay||(bCompletePreload&&ResourcePreparation&&!ResourcePreparation->IsReady()))return;
    if(View&&FinishedAt==0&&!bPreparationFailed)FinishPreparation();
    if(View&&FinishedAt==0)return;
    RestoreGameplayInput();
}

void UTransitLoadingSubsystem::BeforeMap(const FWorldContext& Context,const FString& Map)
{
    // 只管本 GameInstance 名下世界的载入；其他 PIE 实例的地图切换不归本窗口遮罩管。
    // LoadMap broadcasts its matching PostLoadMap with null on failure. That
    // event has no world to filter; remember the latest global load's owner.
    bOwnsCurrentMapLoad=Context.OwningGameInstance==GetGameInstance();
    if(!bOwnsCurrentMapLoad)return;
    if(!View||FinishedAt>0)BeginTransition(Map);
    if(!View)return;
    bMapLoading=true;CancelAction.Unbind();
    if(IsMoviePlayerEnabled())
    {
        auto Snapshot=MakeShared<FTransitLoadingView>(*View);
        Snapshot->Status=FText::FromString(TEXT("正在载入场景，请稍候…"));
        FLoadingScreenAttributes Screen;
        Screen.MinimumLoadingScreenDisplayTime=0;
        Screen.bAutoCompleteWhenLoadingCompletes=true;
        Screen.bMoviesAreSkippable=false;
        Screen.WidgetLoadingScreen=TransitLoading::MakeView(Snapshot,false);
        GetMoviePlayer()->SetupLoadingScreen(Screen);
        // Do not depend on relative ordering with MoviePlayer's own PreLoadMap binding.
        GetMoviePlayer()->PlayMovie();
    }
}

void UTransitLoadingSubsystem::AfterMap(UWorld* World)
{
    if(!World)
    {
        if(!bOwnsCurrentMapLoad)return;
        bOwnsCurrentMapLoad=false;bMapLoading=false;
        if(View)FailPreparation(FText::FromString(TEXT("场景未能载入，请返回后重试。")));
        return;
    }
    if(World->GetGameInstance()!=GetGameInstance())return;
    bOwnsCurrentMapLoad=false;
    bMapLoading=false;bDestinationLoaded=true;
    // A client travel URL may identify the host instead of the destination map.
    if(!bRoomTransition)
    {
        const FString Map=World->GetMapName();
        const bool LoadedHills=(Map.Contains(TEXT("L_TemperateHills_Initial")) || Map.Contains(ForestVillageMap::Name));
        if(bHills||LoadedHills)
        {
            bHills=LoadedHills;
            bDungeon=!bHills&&Map.Contains(TEXT("L_Dungeon_Randomized"));
        }
    }
    if(!View)return;
    // LoadMap invalidates viewport widgets. Keep IgnoreInput, rebuild a live overlay
    // so the player still sees cancel and does not get a "world with no input" gap.
    DetachOverlayWidget();
    AttachOverlay(false);
    if(!bHills&&!bDungeon)UpdatePreparation(FText::FromString(TEXT("正在准备场景显示…")),.9f);
}

void UTransitLoadingSubsystem::UpdatePreparation(const FText& Status, float Progress)
{
    if(!View||FinishedAt>0||bPreparationFailed)return;
    View->Status=Status;View->Progress=FMath::Max(View->Progress,FMath::Clamp(bCompletePreload?Progress*.8f:Progress,0.f,.99f));
}

void UTransitLoadingSubsystem::BeginHillsPreparation()
{
    if(!View||FinishedAt>0)BeginTransition(TEXT("L_TemperateHills_Initial"));
    if(!View)return;
    // A travel can reuse an overlay that was already preparing the old world.
    // Only this hills actor may mark its new destination prepared.
    ResourcePreparation.Reset();ReleasePreparedPlayer();
    bHills=true;bDungeon=false;bScenePrepared=false;bPreparationFailed=false;
    View->ReturnToMenu=false;View->RetryAvailable=false;View->Progress=0;
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client)
    {
        // BeginPlay is also a destination signal when PIE omitted PostLoadMap.
        bStartupChosen=true;bDestinationLoaded=true;bMapLoading=false;
    }
    View->Title=FText::FromString(TEXT("正在进入温带丘陵…"));
    UpdatePreparation(FText::FromString(TEXT("正在准备温带丘陵…")),0);
}

void UTransitLoadingSubsystem::BeginDungeonPreparation()
{
    if (!View) BeginTransition(TEXT("L_Dungeon_Randomized"));
    ResourcePreparation.Reset();
    bDungeon=true;bHills=false;bScenePrepared=false;FinishedAt=0;
    if(SkillPreparation)SkillPreparation->Cancel();
    bSkillPreparationStarted=false;
    if (View)
    {
        View->Title=FText::FromString(TEXT("正在进入地牢…"));
        View->Status=FText::FromString(TEXT("正在规划房间与通路…"));
        View->Progress=0;
    }
}

void UTransitLoadingSubsystem::QueueDungeonResourceWarmup(AActor* Actor)
{
    if(!bCompletePreload||!bDungeon||bScenePrepared||bPreparationFailed||!View||
        !GetWorld()||GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(!ResourcePreparation)
    {
        ApplyLoadingBudget();
        ResourcePreparation=MakeShared<FGameResourcePreparation>(GetWorld(),true);
    }
    ResourcePreparation->QueueAssembledActor(Actor);
}

void UTransitLoadingSubsystem::CompletePreparation()
{
    if(!View||FinishedAt>0||bPreparationFailed)return;
    bScenePrepared=true;
    View->ReturnToMenu=bCompletePreload;
    if(StartupOverlay)return;
    if(bCompletePreload)
    {
        if(!ResourcePreparation)
        {
            ApplyLoadingBudget();
            ResourcePreparation=MakeShared<FGameResourcePreparation>(GetWorld());
        }
        HoldPreparedPlayer();
        ResourcePreparation->FinishSceneAssembly();
        View->Progress=FMath::Max(View->Progress,.8f);
        return;
    }
    FinishPreparation();
}

void UTransitLoadingSubsystem::FinishPreparation()
{
    if(!View||FinishedAt>0||bPreparationFailed||StartupOverlay||!bScenePrepared)return;
    // Only scene preparation gates entry. Learned assets start after the overlay
    // is gone and can never retain input, movement or the loading percentage.
    View->Progress=1;View->Status=FText::FromString(TEXT("准备完成"));
    FinishedAt=FMath::Max(FPlatformTime::Seconds(),StartedAt+1.0);
    // Return GameOnly immediately. Fade is visual only; Tick must not recapture input.
    RestoreGameplayInput();
}

void UTransitLoadingSubsystem::FailPreparation(const FText& Reason)
{
    if(View)View->Status=Reason;
    FinishedAt=0;bPreparationFailed=true;
    if(View)View->Title=FText::FromString(bDungeon?TEXT("地牢准备失败"):TEXT("场景准备失败"));
}

void UTransitLoadingSubsystem::Tick(float DeltaTime)
{
    // Other destinations rely on server assembly. Hills clients cook their own
    // terrain and call CompletePreparation when the local pawn can actually move.
    if(View&&!bRoomTransition&&!bHills&&FinishedAt==0&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client
        &&UGameplayStatics::GetPlayerPawn(GetWorld(),0)&&!bScenePrepared)
    {
        UE_LOG(LogTemp,Warning,TEXT("TransitLoading: net-client bypass map=%s pawn=%s"),
            *UGameplayStatics::GetCurrentLevelName(GetWorld(),true),
            *GetNameSafe(UGameplayStatics::GetPlayerPawn(GetWorld(),0)));
        // The client does not wait for the server's dungeon callback.
        bStartupChosen=true;bDestinationLoaded=true;bScenePrepared=true;
        bMapLoading=false;bPreparationFailed=false;
        ResourcePreparation.Reset();CancelAction.Unbind();
        FinishPreparation();
    }
    if(StartupView)
    {
        if(StartupView->RequestedMode>=0)ChooseLoadingMode(StartupView->RequestedMode==1);
        else return;
    }
    // 联机失败回单机图后把主菜单带回（PC 未就绪时 ShowStartupMenu 内部早退，逐帧重试无副作用）。
    if(!bStartupChosen&&!StartupOverlay&&GetWorld()&&GetWorld()->GetNetMode()==NM_Standalone)
        ShowStartupMenu(UGameplayStatics::GetPlayerController(GetWorld(),0));
    if(!View && bDungeon && !bMapLoading && ResourcePreparation && ResourcePreparation->HasResidencyWork())
        ResourcePreparation->TickResidency();
    if(!View&&!bMapLoading&&bStartupChosen&&!StartupOverlay&&GetWorld()&&GetWorld()->IsGameWorld()&&!GetWorld()->IsPaused())
    {
        auto* Pawn=UGameplayStatics::GetPlayerPawn(GetWorld(),0);
          auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(Pawn&&Pawn->HasActorBegunPlay()&&Model)
        {
            if(!bSkillPreparationStarted)
            {
                if(!SkillPreparation)SkillPreparation=MakeShared<FPlayerSkillPreparation>();
                SkillPreparation->Begin(*Model);bSkillPreparationStarted=true;
            }
            SkillPreparation->Tick();
        }
    }
    if(!View||bMapLoading)return;
    // Existing sessions may still be inside the superseded entry queue when
    // this function is hot-patched. Discard that queue and its skill-only error.
    if(bSkillPreparationStarted&&FinishedAt==0)
    {
        const bool SkillFailed=SkillPreparation&&SkillPreparation->HasFailed();
        if(SkillPreparation)SkillPreparation->Cancel();
        bSkillPreparationStarted=false;
        if(SkillFailed){bPreparationFailed=false;View->RetryAvailable=false;}
    }
    if(FinishedAt==0)
    {
        AttachOverlay(false);
        if(auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0))
        {
            if(CursorController.Get()!=PC)CaptureLoadingInput();
            // 遮罩还挂着时，若有后来者（例如新 Pawn 的 BeginPlay）把光标关掉，下一帧夺回。
            else if(!PC->bShowMouseCursor)PC->bShowMouseCursor=true;
        }
    }
    if(View->CancelRequested)
    {
        if(!UWildlifeSubsystem::FlushPendingLoot(GetWorld()))
        {
            View->CancelRequested=false;
            FailPreparation(FText::FromString(TEXT("掉落保存失败，请稍后重试返回。")));
            return;
        }
        if(View->ReturnToMenu&&bScenePrepared&&GetWorld()->GetNetMode()==NM_Standalone)
        {
            View->CancelRequested=false;bStartupChosen=false;
            ShowStartupMenu(UGameplayStatics::GetPlayerController(GetWorld(),0));return;
        }
        FSimpleDelegate Action=CancelAction;
        const bool WasRoomTransition=bRoomTransition;
        CancelTransition();
        if(Action.IsBound())Action.Execute();
        else if(!WasRoomTransition)UGameplayStatics::OpenLevel(GetWorld(),TEXT("/Game/GameMaps/DayNight_Lighting"));
        return;
    }
    if(View->RetryRequested){View->RetryRequested=false;RetryResources();}
    if(bDestinationLoaded&&!bHills&&!bDungeon&&!bPreparationFailed&&UGameplayStatics::GetPlayerPawn(GetWorld(),0)
        &&GetWorld()->GetNetMode()!=NM_Client
        &&(bCompletePreload||FShaderPipelineCache::NumPrecompilesRemaining()==0))CompletePreparation();
    if(ResourcePreparation&&FinishedAt==0&&!bPreparationFailed)
    {
        ResourcePreparation->Tick();
        if(bScenePrepared)
        {View->Status=ResourcePreparation->Status;View->Progress=FMath::Max(View->Progress,.8f+.19f*ResourcePreparation->Progress);}
        if(ResourcePreparation->HasFailed())
        {FailPreparation(ResourcePreparation->Status);View->RetryAvailable=true;}
        else if(bScenePrepared&&ResourcePreparation->IsReady())FinishPreparation();
    }
    if(bScenePrepared&&!bCompletePreload&&!StartupOverlay&&FinishedAt==0&&!bPreparationFailed)
        FinishPreparation();
    if(FinishedAt>0)
    {
        View->Opacity=1.f-FMath::Clamp(float((FPlatformTime::Seconds()-FinishedAt)/.3),0.f,1.f);
        if(Overlay)Overlay->SetRenderOpacity(View->Opacity);
        if(View->Opacity<=0)
        {
            // Keep visible entry textures protected; after fade-out, the bounded
            // residency pass hands abandoned room/equipment textures back to streaming.
            RemoveOverlay();ReleasePreparedPlayer();View.Reset();CancelAction.Unbind();FinishedAt=0;bRoomTransition=false;
        }
    }
}

void UTransitLoadingSubsystem::RemoveOverlay()
{
    RestoreGameplayInput();
    if(auto* VP=AttachedViewport.Get())
    {
        if(Overlay)VP->RemoveViewportWidgetContent(Overlay.ToSharedRef());
        VP->SetIgnoreInput(false);
    }
    Overlay.Reset();AttachedViewport.Reset();
#if !UE_BUILD_SHIPPING
    UE_LOG(LogTemp,Display,TEXT("TransitInputState phase=overlay_removed %s"),*GetInputRoutingState());
#endif
}

void UTransitLoadingSubsystem::CancelTransition()
{
    bRoomTransition=false;
    if(SkillPreparation)SkillPreparation->Cancel();
    bSkillPreparationStarted=false;
    ResourcePreparation.Reset();ReleasePreparedPlayer();
    RemoveOverlay();View.Reset();CancelAction.Unbind();FinishedAt=0;bMapLoading=false;bDestinationLoaded=false;
    bScenePrepared=false;bPreparationFailed=false;
}

void UTransitLoadingSubsystem::QueueSkillAssets(AActor* Owner,FName Skill,FSimpleDelegate Ready,const TArray<FSoftObjectPath>& ExtraPaths)
{
    if(!SkillPreparation)SkillPreparation=MakeShared<FPlayerSkillPreparation>();
    SkillPreparation->RegisterConsumer(Owner,Skill,Ready,ExtraPaths);
}

void UTransitLoadingSubsystem::RetainBiomeResources(const TArray<TSharedPtr<FStreamableHandle>>& Handles,bool bAllBatchesLoaded)
{
    // Keep the previous visit's dressing until the new visit replaces those
    // batches. Returning early still preserves the just-loaded spawn assets.
    if(bAllBatchesLoaded||Handles.Num()>=BiomeHandles.Num())BiomeHandles=Handles;
    else for(int32 I=0;I<Handles.Num();++I)BiomeHandles[I]=Handles[I];
}

void UTransitLoadingSubsystem::OnNetFailure(UWorld* World,const FString& ErrorString)
{
    // 只认本 GameInstance 的世界（PIE 多实例下全局广播会串到别的实例）。
    if(!World||World->GetGameInstance()!=GetGameInstance())return;
    if(World->GetNetMode()==NM_ListenServer||World->GetNetMode()==NM_DedicatedServer)
    {
        // Server travel failure leaves room ownership with the host; the
        // PlayerState travel coordinator releases the team preparation.
        CancelTransition();
        if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Model->PostNotice(TEXT("地图切换失败"),ErrorString);
        return;
    }
    // Release the old world's input/preparation before waiting for the return map.
    RemoveStartupMenu();
    CancelTransition();
    PendingMenuStatus=ErrorString.IsEmpty()?TEXT("连接失败：无法进入对方房间")
        :FString::Printf(TEXT("连接失败：%s"),*ErrorString);
    bPendingMenuError=true;
    // 引擎会把我们拉回默认图；本地 PC 就绪后 Tick 里的兜底会重弹主菜单。
    bStartupChosen=false;
}

void UTransitLoadingSubsystem::ApplyLoadingBudget()
{
    auto* Pool=IConsoleManager::Get().FindConsoleVariable(TEXT("r.Streaming.PoolSize"));
    if(!Pool)return;
    if(!bBudgetApplied){OriginalPoolSize=Pool->GetInt();bBudgetApplied=true;}
    int32 Target=OriginalPoolSize;
    if(bCompletePreload)
    {
        // Both loading-mode policies live beside each other in TextureStreaming.
        // A missing override retains the project's normal RHI-calculated pool.
        float CompletePercent=0.f;
        if(GConfig&&GConfig->GetFloat(TEXT("TextureStreaming"),TEXT("CompletePreloadPoolSizeVRAMPercentage"),CompletePercent,GEngineIni)
            && CompletePercent>0.f)
        {
            FTextureMemoryStats Stats;RHIGetTextureMemoryStats(Stats);
            if(Stats.TotalGraphicsMemory>0)
                Target=FMath::Max(256,int32((Stats.TotalGraphicsMemory/(1024*1024))
                    * (double(FMath::Clamp(CompletePercent,1.f,100.f))/100.)));
        }
    }
    // Replace at the current priority, so ending PIE does not leave a SetByCode override.
    Pool->SetWithCurrentPriority(Target);AppliedPoolSize=Target;
    UE_LOG(LogTemp,Display,TEXT("GameEntry mode=%s texture_pool_mb=%d"),bCompletePreload?TEXT("Complete"):TEXT("Quick"),Target);
}

void UTransitLoadingSubsystem::RestoreLoadingBudget()
{
    if(!bBudgetApplied)return;
    if(auto* Pool=IConsoleManager::Get().FindConsoleVariable(TEXT("r.Streaming.PoolSize"));Pool&&Pool->GetInt()==AppliedPoolSize)
        Pool->SetWithCurrentPriority(OriginalPoolSize);
    bBudgetApplied=false;
}

void UTransitLoadingSubsystem::HoldPreparedPlayer()
{
    auto* Player=Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(GetWorld(),0));
    if(!Player||PreparedPlayer==Player)return;
    ReleasePreparedPlayer();PreparedPlayer=Player;bPlayerPreviouslyDamageable=Player->CanBeDamaged();
    Player->SetCanBeDamaged(false);
    if(auto* Movement=Player->GetCharacterMovement())
    {bPlayerMovementTicked=Movement->IsComponentTickEnabled();Movement->StopMovementImmediately();Movement->SetComponentTickEnabled(false);}
}

void UTransitLoadingSubsystem::ReleasePreparedPlayer()
{
    if(auto* Player=PreparedPlayer.Get())
    {
        Player->SetCanBeDamaged(bPlayerPreviouslyDamageable);
        if(auto* Movement=Player->GetCharacterMovement())Movement->SetComponentTickEnabled(bPlayerMovementTicked);
    }
    PreparedPlayer.Reset();
}

void UTransitLoadingSubsystem::RetryResources()
{
    if(!bScenePrepared)return;
    ResourcePreparation.Reset();bPreparationFailed=false;
    if(SkillPreparation)SkillPreparation->Cancel();
    bSkillPreparationStarted=false;
    if(View){View->RetryAvailable=false;StartedAt=FPlatformTime::Seconds();View->Start=StartedAt;}
    if(View)View->Title=FText::FromString(TEXT("正在准备场景资源…"));
    if(!bHills&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client)FinishPreparation();
    else CompletePreparation();
}

bool UTransitLoadingSubsystem::IsTickable() const
{
    return !IsTemplate() && (bPendingMenuError || View.IsValid() || StartupView.IsValid() ||
        (bStartupChosen&&!bMapLoading&&GetWorld()&&GetWorld()->IsGameWorld()&&GetWorld()->GetNetMode()!=NM_DedicatedServer&&
            (!bSkillPreparationStarted||(SkillPreparation&&!SkillPreparation->IsReady()))) ||
        (bDungeon && ResourcePreparation && ResourcePreparation->HasResidencyWork()));
}
TStatId UTransitLoadingSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UTransitLoadingSubsystem,STATGROUP_Tickables); }
void UTransitLoadingSubsystem::Deinitialize()
{
    FCoreUObjectDelegates::PreLoadMapWithContext.Remove(PreMapHandle);FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostMapHandle);
    RemoveStartupMenu();CancelTransition();RestoreLoadingBudget();BiomeHandles.Reset();
    SkillPreparation.Reset();
    if(GEngine)
    {
        if(NetworkFailureHandle.IsValid())GEngine->OnNetworkFailure().Remove(NetworkFailureHandle);
        if(TravelFailureHandle.IsValid())GEngine->OnTravelFailure().Remove(TravelFailureHandle);
    }
    Super::Deinitialize();
}
