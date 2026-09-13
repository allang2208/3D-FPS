#include "TransitLoadingSubsystem.h"
#include "ColdSteelUIStyle.h"
#include "Brushes/SlateDynamicImageBrush.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
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
    double Start = 0;
    FSlateBrush Panel = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10,ColdSteelUI::Border,1);
    FButtonStyle Button = ColdSteelUI::ButtonStyle();
    TSharedPtr<FSlateDynamicImageBrush> Background;
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
        if(Event.GetKey()==EKeys::Escape&&State)State->CancelRequested=true;
        return FReply::Handled();
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
            [SNew(STextBlock).Text(FText::FromString(TEXT("取消 / 返回主场景"))).Font(ColdSteelUI::TextFont(10)).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
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
    PreMapHandle=FCoreUObjectDelegates::PreLoadMap.AddUObject(this,&ThisClass::BeforeMap);
    PostMapHandle=FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this,&ThisClass::AfterMap);
}

void UTransitLoadingSubsystem::BeginTransition(const FString& Map, FSimpleDelegate OnCancel)
{
    if(IsRunningCommandlet()||!FSlateApplication::IsInitialized())return;
    if(View)CancelTransition();
    bHills=Map.Contains(TEXT("L_TemperateHills_Initial"));
    bDestinationLoaded=false;
    StartedAt=FPlatformTime::Seconds();FinishedAt=0;
    CancelAction=MoveTemp(OnCancel);
    View=MakeShared<FTransitLoadingView>();View->Start=StartedAt;
    View->Title=FText::FromString(bHills?TEXT("正在进入温带丘陵…"):TEXT("正在切换场景…"));
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
    if(!bHills)UpdatePreparation(FText::FromString(TEXT("正在准备场景显示…")),.9f);
}

void UTransitLoadingSubsystem::UpdatePreparation(const FText& Status, float Progress)
{
    if(!View)BeginTransition(TEXT("L_TemperateHills_Initial"));
    if(!View)return;
    View->Status=Status;View->Progress=FMath::Max(View->Progress,FMath::Clamp(Progress,0.f,.99f));
}

void UTransitLoadingSubsystem::CompletePreparation()
{
    if(!View||FinishedAt>0)return;
    View->Progress=1;View->Status=FText::FromString(TEXT("准备完成"));
    FinishedAt=FMath::Max(FPlatformTime::Seconds(),StartedAt+1.0);
}

void UTransitLoadingSubsystem::FailPreparation(const FText& Reason)
{
    UpdatePreparation(Reason,0);FinishedAt=0;
}

void UTransitLoadingSubsystem::Tick(float DeltaTime)
{
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
    }
    if(View->CancelRequested)
    {
        FSimpleDelegate Action=CancelAction;
        CancelTransition();
        if(Action.IsBound())Action.Execute();
        else UGameplayStatics::OpenLevel(GetWorld(),TEXT("/Game/GameMaps/DayNight_Lighting"));
        return;
    }
    if(bDestinationLoaded&&!bHills&&UGameplayStatics::GetPlayerPawn(GetWorld(),0)&&FShaderPipelineCache::NumPrecompilesRemaining()==0)CompletePreparation();
    if(FinishedAt>0)
    {
        View->Opacity=1.f-FMath::Clamp(float((FPlatformTime::Seconds()-FinishedAt)/.3),0.f,1.f);
        if(Overlay)Overlay->SetRenderOpacity(View->Opacity);
        if(View->Opacity<=0)CancelTransition();
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
    RemoveOverlay();View.Reset();CancelAction.Unbind();FinishedAt=0;bMapLoading=false;bDestinationLoaded=false;
}

void UTransitLoadingSubsystem::RetainBiomeResources(const TArray<TSharedPtr<FStreamableHandle>>& Handles)
{
    // A single curated biome remains resident across return portals; no terrain instances are retained.
    BiomeHandles=Handles;
}

bool UTransitLoadingSubsystem::IsTickable() const { return !IsTemplate()&&View.IsValid(); }
TStatId UTransitLoadingSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UTransitLoadingSubsystem,STATGROUP_Tickables); }
void UTransitLoadingSubsystem::Deinitialize()
{
    FCoreUObjectDelegates::PreLoadMap.Remove(PreMapHandle);FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(PostMapHandle);
    CancelTransition();BiomeHandles.Reset();Super::Deinitialize();
}
