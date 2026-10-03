#include "TransitLoadingSubsystem.h"
#include "ColdSteelUIStyle.h"
#include "GameResourcePreparation.h"
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

// Layout/art originate in game-dev scene-manager.js and panel-theme-backpack.css.
// MoviePlayer map handoff follows the architecture described by AsyncLoadingScreen (MIT).
// Independent project implementation; no plugin code or vendor assets are embedded.
struct FTransitLoadingView
{
    FText Title;
    FText Status;
    float Progress = 0;
    float Opacity = 1;
    bool CancelRequested = false;
    bool RetryRequested = false;
    bool RetryAvailable = false;
    bool ReturnToMenu = false;
    double Start = 0;
    FSlateBrush Panel = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10,ColdSteelUI::Border,1);
    FButtonStyle Button = ColdSteelUI::ButtonStyle();
    TSharedPtr<FSlateDynamicImageBrush> Background;
};

struct FStartupLoadingView
{
    int32 RequestedMode = -1;
    int32 PreviousMode = 0;
    int32 Page = 0; // 0 主界面 1 进入方式 2 联机终端 3 操作说明 4 设置
    FString Nick;
    FString StatusLine;
    bool bStatusError = false;
    TArray<FString> RecentHosts;
    TSharedPtr<SEditableTextBox> NickBox;
    TSharedPtr<SEditableTextBox> AddressBox;
    TSharedPtr<FSlateDynamicImageBrush> Background;
    FSlateBrush Panel = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10,ColdSteelUI::Border,1);
    FSlateBrush InputBg = ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6,ColdSteelUI::Border,1);
    FSlateBrush InfoCard = ColdSteelUI::RoundedBrush(FLinearColor(0.03f,0.04f,0.05f,0.55f),8,ColdSteelUI::Border,1);
    FButtonStyle Button = ColdSteelUI::ButtonStyle();
    FButtonStyle Primary = ColdSteelUI::ButtonStyle();
    FEditableTextBoxStyle InputStyle = FCoreStyle::Get().GetWidgetStyle<FEditableTextBoxStyle>(TEXT("NormalEditableTextBox"));
    FStartupLoadingView()
    {
        Primary.Normal = ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,ColdSteelUI::ButtonRadius,FLinearColor::Transparent,0);
        Primary.Hovered = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(238),ColdSteelUI::ButtonRadius,FLinearColor::Transparent,0);
        Primary.Pressed = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(196),ColdSteelUI::ButtonRadius,FLinearColor::Transparent,0);
        Primary.Disabled = ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonDisabled,ColdSteelUI::ButtonRadius,FLinearColor::Transparent,0);
        InputStyle.BackgroundImageNormal = InputBg;
        InputStyle.BackgroundImageHovered = InputBg;
        InputStyle.BackgroundImageFocused = InputBg;
        InputStyle.BackgroundImageReadOnly = InputBg;
        InputStyle.ForegroundColor = FSlateColor(ColdSteelUI::TextPrimary);
        InputStyle.SetFont(ColdSteelUI::TextFont(12));
    }
};

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

class SStartupMenuRoot : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SStartupMenuRoot) {}
        SLATE_ARGUMENT(TSharedPtr<FStartupLoadingView>, View)
        SLATE_DEFAULT_SLOT(FArguments, Content)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args) { State=Args._View;ChildSlot[Args._Content.Widget]; }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry&,const FKeyEvent& Event) override
    {
        if(Event.GetKey()==EKeys::Escape)
        {
            if(State&&State->Page!=0)State->Page=0;
            return FReply::Handled();
        }
        return FReply::Unhandled();
    }
private:
    TSharedPtr<FStartupLoadingView> State;
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
            [this](UWorld* W,UNetDriver*,ENetworkFailure::Type,const FString& Err){OnNetFailure(W,Err);});
        TravelFailureHandle=GEngine->OnTravelFailure().AddLambda(
            [this](UWorld* W,ETravelFailure::Type,const FString& Err){OnNetFailure(W,Err);});
    }
}

void UTransitLoadingSubsystem::BeginTransition(const FString& Map, FSimpleDelegate OnCancel)
{
    if(IsRunningCommandlet()||!FSlateApplication::IsInitialized())return;
    if(View)CancelTransition();
    ResourcePreparation.Reset();ReleasePreparedPlayer();
    bScenePrepared=false;bPreparationFailed=false;
    bHills=Map.Contains(TEXT("L_TemperateHills_Initial"));
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
}

void UTransitLoadingSubsystem::ReleaseToGameplay()
{
    if(View&&FinishedAt==0&&!bPreparationFailed)FinishPreparation();
    RestoreGameplayInput();
}

void UTransitLoadingSubsystem::BeforeMap(const FWorldContext& Context,const FString& Map)
{
    // 只管本 GameInstance 名下世界的载入；其他 PIE 实例的地图切换不归本窗口遮罩管。
    if(Context.OwningGameInstance!=GetGameInstance())return;
    if(!View)BeginTransition(Map);
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
        bMapLoading=false;
        if(View)FailPreparation(FText::FromString(TEXT("场景未能载入，请返回后重试。")));
        return;
    }
    if(!World||World->GetGameInstance()!=GetGameInstance())return;
    bMapLoading=false;bDestinationLoaded=true;
    if(!View)return;
    // LoadMap invalidates viewport widgets. Keep IgnoreInput, rebuild a live overlay
    // so the player still sees cancel and does not get a "world with no input" gap.
    DetachOverlayWidget();
    AttachOverlay(false);
    if(!bHills&&!bDungeon)UpdatePreparation(FText::FromString(TEXT("正在准备场景显示…")),.9f);
}

void UTransitLoadingSubsystem::UpdatePreparation(const FText& Status, float Progress)
{
    if(!View)BeginTransition(TEXT("L_TemperateHills_Initial"));
    if(!View)return;
    View->Status=Status;View->Progress=FMath::Max(View->Progress,FMath::Clamp(bCompletePreload?Progress*.8f:Progress,0.f,.99f));
}

void UTransitLoadingSubsystem::BeginDungeonPreparation()
{
    if (!View) BeginTransition(TEXT("L_Dungeon_Randomized"));
    bDungeon=true;FinishedAt=0;
    if (View)
    {
        View->Title=FText::FromString(TEXT("正在进入地牢…"));
        View->Status=FText::FromString(TEXT("正在规划房间与通路…"));
        View->Progress=0;
    }
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
            HoldPreparedPlayer();
            ResourcePreparation=MakeShared<FGameResourcePreparation>(GetWorld());
            View->Progress=.8f;
        }
        return;
    }
    FinishPreparation();
}

void UTransitLoadingSubsystem::FinishPreparation()
{
    if(!View||FinishedAt>0)return;
    View->Progress=1;View->Status=FText::FromString(TEXT("准备完成"));
    FinishedAt=FMath::Max(FPlatformTime::Seconds(),StartedAt+1.0);
    // Return GameOnly immediately. Fade is visual only; Tick must not recapture input.
    RestoreGameplayInput();
}

void UTransitLoadingSubsystem::FailPreparation(const FText& Reason)
{
    UpdatePreparation(Reason,0);FinishedAt=0;bPreparationFailed=true;
    if(View)View->Title=FText::FromString(bDungeon?TEXT("地牢准备失败"):TEXT("场景准备失败"));
}

void UTransitLoadingSubsystem::Tick(float DeltaTime)
{
    // M4 联机：联网客户端不跑单机式过场遮罩/启动菜单——世界就绪由服务器把关；
    // pawn 一落地就拆遮罩放行输入（修复 PIE/联机客户端视口进度条永久冻结）。
    if(View&&FinishedAt==0&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client
        &&UGameplayStatics::GetPlayerPawn(GetWorld(),0))
    {
        UE_LOG(LogTemp,Warning,TEXT("TransitLoading: net-client bypass map=%s pawn=%s"),
            *UGameplayStatics::GetCurrentLevelName(GetWorld(),true),
            *GetNameSafe(UGameplayStatics::GetPlayerPawn(GetWorld(),0)));
        // 直接放行输入并当场撕掉遮罩：常规淡出路径依赖 bMapLoading 清除，
        // 而 AfterMap 的 GameInstance 守卫在 PIE 多实例/网络旅行下会提前返回不清旗标，
        // 导致 View 永远挂着（进度条冻结在"准备完成"）。
        bStartupChosen=true;bDestinationLoaded=true;bCompletePreload=true;
        bMapLoading=false;bPreparationFailed=false;
        RestoreGameplayInput();
        if(View.IsValid()){RemoveOverlay();View.Reset();FinishedAt=0;}
        return;
    }
    if(StartupView)
    {
        if(StartupView->RequestedMode>=0)ChooseLoadingMode(StartupView->RequestedMode==1);
        else return;
    }
    // 联机失败回单机图后把主菜单带回（PC 未就绪时 ShowStartupMenu 内部早退，逐帧重试无副作用）。
    if(!bStartupChosen&&!StartupOverlay&&GetWorld()&&GetWorld()->GetNetMode()==NM_Standalone)
        ShowStartupMenu(UGameplayStatics::GetPlayerController(GetWorld(),0));
    if(!View||bMapLoading)return;
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
        if(View->ReturnToMenu&&bScenePrepared)
        {
            View->CancelRequested=false;bStartupChosen=false;
            ShowStartupMenu(UGameplayStatics::GetPlayerController(GetWorld(),0));return;
        }
        FSimpleDelegate Action=CancelAction;
        CancelTransition();
        if(Action.IsBound())Action.Execute();
        else UGameplayStatics::OpenLevel(GetWorld(),TEXT("/Game/GameMaps/DayNight_Lighting"));
        return;
    }
    if(View->RetryRequested){View->RetryRequested=false;RetryResources();}
    if(bDestinationLoaded&&!bHills&&!bDungeon&&!bPreparationFailed&&UGameplayStatics::GetPlayerPawn(GetWorld(),0)
        &&(bCompletePreload||FShaderPipelineCache::NumPrecompilesRemaining()==0))CompletePreparation();
    if(ResourcePreparation&&FinishedAt==0&&!bPreparationFailed)
    {
        ResourcePreparation->Tick();
        View->Status=ResourcePreparation->Status;View->Progress=.8f+.19f*ResourcePreparation->Progress;
        if(ResourcePreparation->HasFailed())
        {FailPreparation(ResourcePreparation->Status);View->RetryAvailable=true;}
        else if(ResourcePreparation->IsReady())FinishPreparation();
    }
    if(FinishedAt>0)
    {
        View->Opacity=1.f-FMath::Clamp(float((FPlatformTime::Seconds()-FinishedAt)/.3),0.f,1.f);
        if(Overlay)Overlay->SetRenderOpacity(View->Opacity);
        if(View->Opacity<=0)
        {
            // Keep the prepared world's mip protection until the next map/entry.
            RemoveOverlay();ReleasePreparedPlayer();View.Reset();CancelAction.Unbind();FinishedAt=0;
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
}

void UTransitLoadingSubsystem::CancelTransition()
{
    ResourcePreparation.Reset();ReleasePreparedPlayer();
    RemoveOverlay();View.Reset();CancelAction.Unbind();FinishedAt=0;bMapLoading=false;bDestinationLoaded=false;
    bScenePrepared=false;bPreparationFailed=false;
}

void UTransitLoadingSubsystem::RetainBiomeResources(const TArray<TSharedPtr<FStreamableHandle>>& Handles)
{
    // A single curated biome remains resident across return portals; no terrain instances are retained.
    BiomeHandles=Handles;
}

void UTransitLoadingSubsystem::ShowStartupMenu(APlayerController* Controller)
{
    if(!Controller||!Controller->IsLocalController()||!FSlateApplication::IsInitialized()||StartupOverlay)return;
    if(GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(bStartupChosen)
    {
        ApplyLoadingBudget();
        if(bCompletePreload&&!View){BeginTransition(UGameplayStatics::GetCurrentLevelName(this,true));bDestinationLoaded=true;}
        return;
    }
    auto* VP=GetGameInstance()->GetGameViewportClient();
    if(!VP)return;
    if(!View){BeginTransition(UGameplayStatics::GetCurrentLevelName(this,true));bDestinationLoaded=true;}
    StartupController=Controller;StartupViewport=VP;
    bStartupPreviousIgnore=VP->IgnoreInput();bStartupPreviousCursor=Controller->bShowMouseCursor;
    bStartupPausedWorld=!UGameplayStatics::IsGamePaused(this)&&Controller->SetPause(true);
    VP->SetIgnoreInput(true);Controller->bShowMouseCursor=true;
    StartupView=MakeShared<FStartupLoadingView>();StartupView->PreviousMode=bCompletePreload?1:0;
    const auto State=StartupView;
    TWeakObjectPtr<UGameViewportClient> WeakVP=VP;
    GConfig->GetString(TEXT("FPSGAME.Menu"),TEXT("Nick"),State->Nick,GGameUserSettingsIni);
    {
        FString Joined;
        if(GConfig->GetString(TEXT("FPSGAME.Menu"),TEXT("RecentHosts"),Joined,GGameUserSettingsIni))
            Joined.ParseIntoArray(State->RecentHosts,TEXT(","),true);
    }
    {
        const FString BgFile=FPaths::ProjectContentDir()/TEXT("UI/MainMenu/start-screen-background.png");
        if(FPaths::FileExists(BgFile))State->Background=MakeShared<FSlateDynamicImageBrush>(FName(*BgFile),FVector2D(2048,1536));
    }
    if(!PendingMenuStatus.IsEmpty())
    {State->StatusLine=PendingMenuStatus;State->bStatusError=bPendingMenuError;PendingMenuStatus.Empty();bPendingMenuError=false;}
    // 子页统一套玻璃面板；主页按原版菜单样式直接压在背景图上（无面板窄列）。
    auto PanelPage=[State,WeakVP](TSharedRef<SWidget> Content) -> TSharedRef<SWidget>
    {
        return SNew(SBox)
            .WidthOverride_Lambda([WeakVP](){FVector2D Size(728,700);if(WeakVP.IsValid())WeakVP->GetViewportSize(Size);return FOptionalSize(FMath::Max(200.f,FMath::Min(560.f,float(Size.X)-48)));})
            .MaxDesiredHeight_Lambda([WeakVP](){FVector2D Size(728,700);if(WeakVP.IsValid())WeakVP->GetViewportSize(Size);return FOptionalSize(FMath::Max(120.f,float(Size.Y)-48));})
            [SNew(SBorder).BorderImage(&State->Panel).Padding(24)
                [SNew(SScrollBox)+SScrollBox::Slot()[Content]]];
    };
    auto Eyebrow=[](const TCHAR* Text) -> TSharedRef<SWidget>
    {
        return SNew(STextBlock).Text(FText::FromString(Text)).Font(ColdSteelUI::NumberFont(9))
            .Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextTertiary);
    };
    auto MenuBtn=[State](const TCHAR* Label,TFunction<void()> Fn,bool bPrimary=false,bool bDanger=false) -> TSharedRef<SWidget>
    {
        return SNew(SButton).ButtonStyle(bPrimary?&State->Primary:&State->Button)
            .ContentPadding(FMargin(0,13)).HAlign(HAlign_Center)
            .OnClicked_Lambda([Fn](){Fn();return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(Label))
                .Font(ColdSteelUI::TextFont(bPrimary?13.f:11.f,bPrimary))
                .ColorAndOpacity(bPrimary?FSlateColor(ColdSteelUI::Gray(18)):
                    (bDanger?FSlateColor(ColdSteelUI::Danger):FSlateColor(ColdSteelUI::TextPrimary)))];
    };
    auto StatusLine=[State]() -> TSharedRef<SWidget>
    {
        return SNew(STextBlock).Text_Lambda([State](){return FText::FromString(State->StatusLine);})
            .Font(ColdSteelUI::NumberFont(9)).Justification(ETextJustify::Center)
            .ColorAndOpacity_Lambda([State](){return FSlateColor(State->bStatusError?ColdSteelUI::Danger:ColdSteelUI::TextSecondary);});
    };
    TSharedPtr<SButton> FocusButton;
    // ----- 主页 -----
    auto MainPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 接入终端"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("无 尽 轮 回")))
            .Font(ColdSteelUI::TextFont(26,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("第一人称动作 RPG")))
            .Font(ColdSteelUI::TextFont(10.5f)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("V 0.1.0")))
            .Font(ColdSteelUI::NumberFont(8)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,24,0,0)
        [SAssignNew(FocusButton,SButton).ButtonStyle(&State->Primary).ContentPadding(FMargin(0,14)).HAlign(HAlign_Center)
            .OnClicked_Lambda([State](){State->Page=1;return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(TEXT("开 始 游 戏"))).Font(ColdSteelUI::TextFont(13,true)).ColorAndOpacity(ColdSteelUI::Gray(18))]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[MenuBtn(TEXT("多 人 游 戏"),[State](){State->Page=2;})]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[MenuBtn(TEXT("设    置"),[State](){State->Page=4;})]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[MenuBtn(TEXT("操作说明"),[State](){State->Page=3;})]
            +SHorizontalBox::Slot().FillWidth(1).Padding(10,0,0,0)[MenuBtn(TEXT("退出游戏"),[this](){MenuQuitGame();},false,true)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,16,0,0)[StatusLine()]
        +SVerticalBox::Slot().AutoHeight().Padding(0,14,0,0)
        [SNew(SBorder).BorderImage(&State->InfoCard).Padding(FMargin(14,11))
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("快 捷 操 作")))
                    .Font(ColdSteelUI::NumberFont(8)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock)
                    .Text(FText::FromString(TEXT("基础操作会在实际游玩中逐步提示。完整键位可随时从「操作说明」查看。")))
                    .Font(ColdSteelUI::TextFont(10)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]]];
    // ----- 进入方式 -----
    auto ModeOption=[State](const TCHAR* Title,const TCHAR* Desc,int32 Mode) -> TSharedRef<SWidget>
    {
        return SNew(SButton).ButtonStyle(&State->Button).ContentPadding(16).HAlign(HAlign_Fill)
            .OnClicked_Lambda([State,Mode](){State->RequestedMode=Mode;return FReply::Handled();})
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(FString(Title)+(State->PreviousMode==Mode?TEXT("  ·  上次选择"):TEXT(""))))
                    .Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Text(FText::FromString(Desc))
                    .Font(ColdSteelUI::TextFont(10)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
    };
    auto StartPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 接入终端"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("选 择 进 入 方 式")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[ModeOption(TEXT("快速测试"),TEXT("优先进入游戏，高清纹理在游玩时逐步加载。适合快速调试。"),0)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[ModeOption(TEXT("完整预加载"),TEXT("场景、装备与高清纹理准备完成后再进入。等待更久，占用更多显存；资源未就绪会显示原因并保留在加载界面。"),1)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    // ----- 联机终端 -----
    FString LocalIps;
    if(auto* Sub=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM))
    {
        TArray<TSharedPtr<FInternetAddr>> Addrs;
        if(Sub->GetLocalAdapterAddresses(Addrs))
            for(const auto& A:Addrs)
            {
                if(!A.IsValid())continue;
                const FString S=A->ToString(false);
                if(!S.IsEmpty()&&S!=TEXT("127.0.0.1")&&!S.StartsWith(TEXT("169.254."))&&!S.Contains(TEXT(":")))
                    LocalIps+=LocalIps.IsEmpty()?S:TEXT(" / ")+S;
            }
    }
    auto MpPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 联机协议"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("联 机 终 端")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("建立房间等待好友接入，或按地址加入他人房间。")))
            .Font(ColdSteelUI::TextFont(10)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(STextBlock).Text(FText::FromString(TEXT("昵称")))
            .Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,14)
        [SAssignNew(State->NickBox,SEditableTextBox).Style(&State->InputStyle).Padding(FMargin(10,9))
            .Text(FText::FromString(State->Nick)).HintText(FText::FromString(TEXT("显示给其他玩家的名字")))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[MenuBtn(TEXT("创 建 房 间（主机）"),[this](){MenuHostRoom();},true)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,4)[SNew(STextBlock).Text(FText::FromString(TEXT("以当前场景开启监听房间，好友通过你的 IP 加入。")))
            .Font(ColdSteelUI::TextFont(9)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[SNew(STextBlock).Text(FText::FromString(
            LocalIps.IsEmpty()?TEXT("本机地址：未检测到局域网 IP"):FString::Printf(TEXT("本机地址：%s:7777"),*LocalIps)))
            .Font(ColdSteelUI::NumberFont(9)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,14)[SNew(SSeparator).Orientation(Orient_Horizontal)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(STextBlock).Text(FText::FromString(TEXT("加入房间")))
            .Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(State->AddressBox,SEditableTextBox).Style(&State->InputStyle).Padding(FMargin(10,8))
                .HintText(FText::FromString(TEXT("IP[:端口]，例如 192.168.1.10:7777")))]
            +SHorizontalBox::Slot().AutoWidth().Padding(8,0,0,0).VAlign(VAlign_Center)
            [SNew(SButton).ButtonStyle(&State->Button).ContentPadding(FMargin(18,8))
                .OnClicked_Lambda([this](){MenuJoinByAddress(TEXT(""));return FReply::Handled();})
                [SNew(STextBlock).Text(FText::FromString(TEXT("连 接"))).Font(ColdSteelUI::TextFont(11,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]]];
    if(State->RecentHosts.Num()>0)
    {
        MpPage->AddSlot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Text(FText::FromString(TEXT("最 近 连 接")))
            .Font(ColdSteelUI::NumberFont(8)).ColorAndOpacity(ColdSteelUI::TextTertiary)];
        for(const FString& Host:State->RecentHosts)
        {
            const FString HostCopy=Host;
            MpPage->AddSlot().AutoHeight().Padding(0,6,0,0)
            [SNew(SButton).ButtonStyle(&State->Button).ContentPadding(FMargin(12,7)).HAlign(HAlign_Left)
                .OnClicked_Lambda([this,HostCopy](){MenuJoinByAddress(HostCopy);return FReply::Handled();})
                [SNew(STextBlock).Text(FText::FromString(HostCopy)).Font(ColdSteelUI::NumberFont(10)).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
        }
    }
    MpPage->AddSlot().AutoHeight().Padding(0,14,0,0)[StatusLine()];
    MpPage->AddSlot().AutoHeight().Padding(0,10,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    // ----- 操作说明 -----
    auto HelpPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 键位"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("操 作 说 明")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
        [SNew(SBorder).BorderImage(&State->InfoCard).Padding(FMargin(14,12))
            [SNew(STextBlock)
                .Text(FText::FromString(TEXT("W A S D　移动\n空格　跳跃\nShift　冲刺\nCtrl / C　滑铲\n鼠标左键　攻击 / 开火\n鼠标右键　瞄准\nR　换弹\nF　快速近战\nG　符文刃\nL　检视武器\nTab / B　背包\nEsc　系统菜单")))
                .Font(ColdSteelUI::TextFont(10.5f)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    // ----- 设置 -----
    auto SettingsPage=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,2)[Eyebrow(TEXT("轮回档案 // 终端设置"))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,18)[SNew(STextBlock).Text(FText::FromString(TEXT("设    置")))
            .Font(ColdSteelUI::TextFont(15,true)).Justification(ETextJustify::Center).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
        [SNew(SBorder).BorderImage(&State->InfoCard).Padding(FMargin(14,12))
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([State](){
                    return FText::FromString(FString::Printf(TEXT("进入方式：%s"),State->PreviousMode==1?TEXT("完整预加载"):TEXT("快速测试")));})
                    .Font(ColdSteelUI::TextFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextSecondary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock)
                    .Text(FText::FromString(TEXT("载入档位可在「开始游戏」里切换。画面、音频与键位设置将在后续版本开放。")))
                    .Font(ColdSteelUI::TextFont(9.5f)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextTertiary)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[MenuBtn(TEXT("返回主界面"),[State](){State->Page=0;})];
    StartupOverlay=SNew(TransitLoading::SStartupMenuRoot).View(State)
        [SNew(SOverlay)
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.031f,0.051f,0.070f,1))]
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill).HAlign(HAlign_Center).VAlign(VAlign_Bottom)
            [SNew(SImage).Image(State->Background.Get())]]
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.016f,0.031f,0.070f,0.30f))]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(24)
        [SNew(SWidgetSwitcher).WidgetIndex_Lambda([State](){return State->Page;})
            +SWidgetSwitcher::Slot()[SNew(SBox).WidthOverride(300)[MainPage]]
            +SWidgetSwitcher::Slot()[PanelPage(StartPage)]
            +SWidgetSwitcher::Slot()[PanelPage(MpPage)]
            +SWidgetSwitcher::Slot()[PanelPage(HelpPage)]
            +SWidgetSwitcher::Slot()[PanelPage(SettingsPage)]]];
    VP->AddViewportWidgetContent(StartupOverlay.ToSharedRef(),100010);
    Controller->SetInputMode(FInputModeUIOnly().SetWidgetToFocus(FocusButton).SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock));
    FSlateApplication::Get().SetAllUserFocus(FocusButton,EFocusCause::SetDirectly);
}

void UTransitLoadingSubsystem::RemoveStartupMenu()
{
    if(auto* PC=StartupController.Get())
    {
        if(bStartupPausedWorld)PC->SetPause(false);
        PC->bShowMouseCursor=bStartupPreviousCursor;PC->SetInputMode(FInputModeGameOnly());
    }
    if(auto* VP=StartupViewport.Get())
    {
        if(StartupOverlay)VP->RemoveViewportWidgetContent(StartupOverlay.ToSharedRef());
        VP->SetIgnoreInput(bStartupPreviousIgnore);
    }
    StartupOverlay.Reset();StartupView.Reset();StartupViewport.Reset();StartupController.Reset();bStartupPausedWorld=false;
    if(Overlay&&FSlateApplication::IsInitialized())FSlateApplication::Get().SetAllUserFocus(Overlay,EFocusCause::SetDirectly);
}

void UTransitLoadingSubsystem::ChooseLoadingMode(bool Complete)
{
    bStartupChosen=true;bCompletePreload=Complete;
    GConfig->SetInt(TEXT("FPSGAME.Loading"),TEXT("Mode"),Complete?1:0,GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
    ResourcePreparation.Reset();ReleasePreparedPlayer();bPreparationFailed=false;
    ApplyLoadingBudget();RemoveStartupMenu();
    if(View){View->ReturnToMenu=Complete&&bScenePrepared;View->RetryAvailable=false;View->Opacity=1;View->Progress=0;StartedAt=FPlatformTime::Seconds();View->Start=StartedAt;}
    if(bScenePrepared)CompletePreparation();
}

void UTransitLoadingSubsystem::MenuApplyNick()
{
    if(!StartupView)return;
    FString Nick=StartupView->NickBox.IsValid()?StartupView->NickBox->GetText().ToString():StartupView->Nick;
    Nick=Nick.TrimStartAndEnd();
    Nick.ReplaceInline(TEXT("?"),TEXT(""));Nick.ReplaceInline(TEXT("&"),TEXT(""));
    Nick.ReplaceInline(TEXT("/"),TEXT(""));Nick.ReplaceInline(TEXT("="),TEXT(""));
    Nick.ReplaceInline(TEXT(" "),TEXT(""));Nick.ReplaceInline(TEXT("\t"),TEXT(""));
    if(Nick.Len()>20)Nick=Nick.Left(20);
    StartupView->Nick=Nick;
    GConfig->SetString(TEXT("FPSGAME.Menu"),TEXT("Nick"),*Nick,GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
}

void UTransitLoadingSubsystem::MenuHostRoom()
{
    MenuApplyNick();
    if(!StartupView||!GetWorld())return;
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    const FString Nick=StartupView->Nick;
    const int32 Mode=StartupView->PreviousMode;
    FString Options=TEXT("listen");
    if(!Nick.IsEmpty())Options+=FString::Printf(TEXT("?Name=%s"),*Nick);
    ChooseLoadingMode(Mode==1);
    UGameplayStatics::OpenLevel(this,FName(*Map),true,Options);
}

void UTransitLoadingSubsystem::MenuJoinByAddress(FString Address)
{
    MenuApplyNick();
    if(!StartupView)return;
    Address=Address.TrimStartAndEnd();
    if(Address.IsEmpty()&&StartupView->AddressBox.IsValid())
        Address=StartupView->AddressBox->GetText().ToString().TrimStartAndEnd();
    if(Address.IsEmpty()||Address.Contains(TEXT("?"))||Address.Contains(TEXT("&"))||Address.Contains(TEXT(" ")))
    {
        StartupView->StatusLine=TEXT("地址无效：请输入 IP 或 IP:端口，例如 192.168.1.10:7777");
        StartupView->bStatusError=true;
        return;
    }
    StartupView->StatusLine=FString::Printf(TEXT("正在连接 %s …"),*Address);
    StartupView->bStatusError=false;
    StartupView->RecentHosts.Remove(Address);
    StartupView->RecentHosts.Insert(Address,0);
    if(StartupView->RecentHosts.Num()>4)StartupView->RecentHosts.SetNum(4);
    GConfig->SetString(TEXT("FPSGAME.Menu"),TEXT("RecentHosts"),*FString::Join(StartupView->RecentHosts,TEXT(",")),GGameUserSettingsIni);
    GConfig->Flush(false,GGameUserSettingsIni);
    const FString Nick=StartupView->Nick;
    const int32 Mode=StartupView->PreviousMode;
    ChooseLoadingMode(Mode==1);
    UGameplayStatics::OpenLevel(this,FName(*Address),true,
        Nick.IsEmpty()?FString():FString::Printf(TEXT("Name=%s"),*Nick));
}

void UTransitLoadingSubsystem::MenuQuitGame()
{
    UKismetSystemLibrary::QuitGame(this,StartupController.Get(),EQuitPreference::Quit,false);
}

void UTransitLoadingSubsystem::OnNetFailure(UWorld* World,const FString& ErrorString)
{
    // 只认本 GameInstance 的世界（PIE 多实例下全局广播会串到别的实例）。
    if(!World||World->GetGameInstance()!=GetGameInstance())return;
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
        FTextureMemoryStats Stats;RHIGetTextureMemoryStats(Stats);
        if(Stats.TotalGraphicsMemory>0)
            Target=FMath::Max(256,int32((Stats.TotalGraphicsMemory/(1024*1024))*.45));
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
    if(!bScenePrepared||!bCompletePreload)return;
    ResourcePreparation.Reset();bPreparationFailed=false;
    if(View){View->RetryAvailable=false;StartedAt=FPlatformTime::Seconds();View->Start=StartedAt;}
    if(View)View->Title=FText::FromString(TEXT("正在准备场景资源…"));
    CompletePreparation();
}

bool UTransitLoadingSubsystem::IsTickable() const { return !IsTemplate()&&(View.IsValid()||StartupView.IsValid()); }
TStatId UTransitLoadingSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UTransitLoadingSubsystem,STATGROUP_Tickables); }
void UTransitLoadingSubsystem::Deinitialize()
{
    FCoreUObjectDelegates::PreLoadMapWithContext.Remove(PreMapHandle);FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostMapHandle);
    RemoveStartupMenu();CancelTransition();RestoreLoadingBudget();BiomeHandles.Reset();
    if(GEngine)
    {
        if(NetworkFailureHandle.IsValid())GEngine->OnNetworkFailure().Remove(NetworkFailureHandle);
        if(TravelFailureHandle.IsValid())GEngine->OnTravelFailure().Remove(TravelFailureHandle);
    }
    Super::Deinitialize();
}
