#include "TransitLoadingSubsystem.h"
#include "ColdSteelUIStyle.h"
#include "GameResourcePreparation.h"
#include "Brushes/SlateDynamicImageBrush.h"
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
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

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
    FSlateBrush Panel = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10,ColdSteelUI::Border,1);
    FButtonStyle Button = ColdSteelUI::ButtonStyle();
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

TSharedRef<SWidget> MakeView(const TSharedRef<FTransitLoadingView>& State, bool Interactive)
{
    // The MoviePlayer uses a separate, immutable snapshot: no UObject access or
    // shared mutable UI attributes from its loading thread.
    auto Content = SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("TRANSIT ARCHIVE")))
            .Font(ColdSteelUI::NumberFont(9)).ColorAndOpacity(ColdSteelUI::TextTertiary).Justification(ETextJustify::Center)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,20)[SNew(STextBlock).Text(State->Title)
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
    PreMapHandle=FCoreUObjectDelegates::PreLoadMap.AddUObject(this,&ThisClass::BeforeMap);
    PostMapHandle=FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this,&ThisClass::AfterMap);
}

void UTransitLoadingSubsystem::BeginTransition(const FString& Map, FSimpleDelegate OnCancel)
{
    if(IsRunningCommandlet()||!FSlateApplication::IsInitialized())return;
    if(View)CancelTransition();
    ResourcePreparation.Reset();ReleasePreparedPlayer();
    bScenePrepared=false;bPreparationFailed=false;
    bHills=Map.Contains(TEXT("L_TemperateHills_Initial"));
    bDungeon=Map.Contains(TEXT("L_Dungeon_Generated"))||Map.Contains(TEXT("L_Dungeon_Randomized"));
    bDestinationLoaded=false;
    StartedAt=FPlatformTime::Seconds();FinishedAt=0;
    CancelAction=MoveTemp(OnCancel);
    View=MakeShared<FTransitLoadingView>();View->Start=StartedAt;
    View->ReturnToMenu=false;
    View->Title=FText::FromString(bHills?TEXT("正在进入温带丘陵…"):bDungeon?TEXT("正在进入地牢…"):TEXT("正在切换场景…"));
    View->Status=FText::FromString(TEXT("正在准备场景资源…"));
    const FString File=FPaths::ProjectContentDir()/TEXT("UI/TransitLoading")/FString::Printf(TEXT("gaia-fertile-lands-%d.png"),FMath::RandRange(1,2));
    if(FPaths::FileExists(File))View->Background=MakeShared<FSlateDynamicImageBrush>(FName(*File),FVector2D(1672,941));
    AttachOverlay();
}

void UTransitLoadingSubsystem::AttachOverlay()
{
    auto* VP=GetGameInstance()->GetGameViewportClient();
    if(!VP||!View||Overlay)return;
    bPreviousIgnoreInput=VP->IgnoreInput();VP->SetIgnoreInput(true);AttachedViewport=VP;
    Overlay=TransitLoading::MakeView(View.ToSharedRef(),true);
    VP->AddViewportWidgetContent(Overlay.ToSharedRef(),100000);
    FSlateApplication::Get().SetAllUserFocus(Overlay,EFocusCause::SetDirectly);
}

void UTransitLoadingSubsystem::BeforeMap(const FString& Map)
{
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
    AttachOverlay();
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
}

void UTransitLoadingSubsystem::FailPreparation(const FText& Reason)
{
    UpdatePreparation(Reason,0);FinishedAt=0;bPreparationFailed=true;
}

void UTransitLoadingSubsystem::Tick(float DeltaTime)
{
    if(StartupView)
    {
        if(StartupView->RequestedMode>=0)ChooseLoadingMode(StartupView->RequestedMode==1);
        else return;
    }
    if(!View||bMapLoading)return;
    AttachOverlay();
    if(auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0))
    {
        if(CursorController.Get()!=PC)
        {
            CursorController=PC;bPreviousCursor=PC->bShowMouseCursor;
            PC->bShowMouseCursor=true;
            if(Overlay)FSlateApplication::Get().SetAllUserFocus(Overlay,EFocusCause::SetDirectly);
        }
        // 遮罩还挂着时，若有后来者（例如新 Pawn 的 BeginPlay）把光标关掉，下一帧夺回。
        else if(!PC->bShowMouseCursor)PC->bShowMouseCursor=true;
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
    if(auto* PC=CursorController.Get())PC->bShowMouseCursor=bPreviousCursor;
    CursorController.Reset();
    if(auto* VP=AttachedViewport.Get())
    {
        if(Overlay)VP->RemoveViewportWidgetContent(Overlay.ToSharedRef());
        VP->SetIgnoreInput(bPreviousIgnoreInput);
    }
    if(FSlateApplication::IsInitialized())FSlateApplication::Get().SetAllUserFocusToGameViewport();
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
    auto Options=SNew(SVerticalBox);
    TSharedPtr<SButton> FocusButton;
    for(int32 Mode=0;Mode<2;++Mode)
    {
        const FString Title=Mode==0?TEXT("快速测试"):TEXT("完整预加载");
        const FString Description=Mode==0?TEXT("优先进入游戏，高清纹理在游玩时逐步加载。适合快速调试。"):
            TEXT("场景、装备与高清纹理准备完成后再进入。等待更久，占用更多显存。若有资源未就绪，会显示原因并保留在加载界面。");
        TSharedPtr<SButton> OptionButton;
        Options->AddSlot().AutoHeight().Padding(0,0,0,12)
        [SAssignNew(OptionButton,SButton).ButtonStyle(&State->Button).ContentPadding(20).HAlign(HAlign_Fill)
            .OnClicked_Lambda([State,Mode](){State->RequestedMode=Mode;return FReply::Handled();})
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Title+(State->PreviousMode==Mode?TEXT("  ·  上次选择"):TEXT(""))))
                    .Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock).Text(FText::FromString(Description))
                    .Font(ColdSteelUI::TextFont(10.5f)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextSecondary)]]];
        if(Mode==State->PreviousMode)FocusButton=OptionButton;
    }
    TWeakObjectPtr<UGameViewportClient> WeakVP=VP;
    StartupOverlay=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(ColdSteelUI::GlassFallback)]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(24)
        [SNew(SBox)
            .WidthOverride_Lambda([WeakVP](){FVector2D Size(728,700);if(WeakVP.IsValid())WeakVP->GetViewportSize(Size);return FOptionalSize(FMath::Max(200.f,FMath::Min(680.f,float(Size.X)-48)));})
            .MaxDesiredHeight_Lambda([WeakVP](){FVector2D Size(728,700);if(WeakVP.IsValid())WeakVP->GetViewportSize(Size);return FOptionalSize(FMath::Max(120.f,float(Size.Y)-48));})
            [SNew(SBorder).BorderImage(&State->Panel).Padding(24)
                [SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("无尽轮回")))
                        .Font(ColdSteelUI::TextFont(18,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,24)[SNew(STextBlock).Text(FText::FromString(TEXT("选择进入方式")))
                        .Font(ColdSteelUI::TextFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextSecondary)]
                    +SVerticalBox::Slot().FillHeight(1)[SNew(SScrollBox)+SScrollBox::Slot()[Options]]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)[SNew(STextBlock)
                        .Text(FText::FromString(TEXT("本次选择会用于随后进入的场景；两档均保留地面与碰撞的必要准备。")))
                        .Font(ColdSteelUI::TextFont(9)).AutoWrapText(true).ColorAndOpacity(ColdSteelUI::TextTertiary)]]]];
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
    CompletePreparation();
}

bool UTransitLoadingSubsystem::IsTickable() const { return !IsTemplate()&&(View.IsValid()||StartupView.IsValid()); }
TStatId UTransitLoadingSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UTransitLoadingSubsystem,STATGROUP_Tickables); }
void UTransitLoadingSubsystem::Deinitialize()
{
    FCoreUObjectDelegates::PreLoadMap.Remove(PreMapHandle);FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostMapHandle);
    RemoveStartupMenu();CancelTransition();RestoreLoadingBudget();BiomeHandles.Reset();Super::Deinitialize();
}
