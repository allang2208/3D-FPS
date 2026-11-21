// Source/FPSGAME/UI/ColdSteelProgressNotification.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 19-19 | file scope
#include "Widgets/Layout/SScaleBox.h"

// Lines 57-57 | TSharedRef<SWidget> UColdSteelProgressNotification::BuildSurface()
    InteractionBrush.ImageSize=FVector2D(20/Scale);

// Lines 70-90 | TSharedRef<SWidget> UColdSteelProgressNotification::BuildSurface()
    const auto InteractionNotice=SAssignNew(InteractionRow,SBox)
        [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
                [SNew(SBox).WidthOverride(20/Scale).HeightOverride(24/Scale).VAlign(VAlign_Top)
                    .Visibility_Lambda([this]{return InteractionIcon?EVisibility::HitTestInvisible:EVisibility::Collapsed;})
                    [SNew(SImage).Image(&InteractionBrush)]]
            +SVerticalBox::Slot().AutoHeight()
                [SNew(SScaleBox).Stretch(EStretch::ScaleToFitX).StretchDirection(EStretchDirection::DownOnly).HAlign(HAlign_Center)
                    [SAssignNew(InteractionTitle,STextBlock).AutoWrapText(false).Justification(ETextJustify::Center)
                        .Font(TitleFont(1,FLinearColor(0,0,0,.8f),false)).ColorAndOpacity(ColdSteelUI::NoticeGold)
                        .ShadowOffset(FVector2D(0,2/Scale)).ShadowColorAndOpacity(FLinearColor(0,0,0,.9f))]]
            +SVerticalBox::Slot().AutoHeight()
                [SNew(SScaleBox).Stretch(EStretch::ScaleToFitX).StretchDirection(EStretchDirection::DownOnly).HAlign(HAlign_Center)
                    [SAssignNew(InteractionDetail,STextBlock).AutoWrapText(false).Justification(ETextJustify::Center)
                        .Margin(FMargin(0,6/Scale,0,0)).Font(DetailFont()).ColorAndOpacity(FLinearColor::White)
                        .ShadowOffset(FVector2D(0,2/Scale)).ShadowColorAndOpacity(FLinearColor(0,0,0,.9f))]]];
    InteractionTitle->SetText(FText::FromString(Interaction.Title));
    InteractionDetail->SetText(FText::FromString(Interaction.Detail));
    InteractionDetail->SetVisibility(Interaction.Detail.IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible);
    InteractionRow->SetVisibility(InteractionRemaining>0.f?EVisibility::HitTestInvisible:EVisibility::Collapsed);
    auto Surface=SNew(SOverlay)

// Lines 94-97 | TSharedRef<SWidget> UColdSteelProgressNotification::BuildSurface()
        [SNew(SBox).WidthOverride_Lambda([this]{return FOptionalSize(FMath::Max(1.f,FMath::Min(820/Scale,float(GetCachedGeometry().GetLocalSize().X)-40/Scale)));})
            [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()
            [SAssignNew(Card,SBox)[SNew(SVerticalBox)

// Lines 99-99 | TSharedRef<SWidget> UColdSteelProgressNotification::BuildSurface()
                    [SNew(SBox).WidthOverride(48/Scale).HeightOverride(48/Scale)

// Lines 109-111 | TSharedRef<SWidget> UColdSteelProgressNotification::BuildSurface()
                        .Justification(ETextJustify::Center).AutoWrapText(true)]]]
            +SVerticalBox::Slot().AutoHeight()[InteractionNotice]]];
    Card->SetVisibility(bActive?EVisibility::HitTestInvisible:EVisibility::Collapsed);

// Lines 123-182 | void UColdSteelProgressNotification::PrepareNoticeIcon(bool bInteraction)
void UColdSteelProgressNotification::PrepareNoticeIcon(bool bInteraction)
{
    const FString& Icon=bInteraction?Interaction.Icon:Active.Icon;
    const uint64 Request=bInteraction?++InteractionIconRequest:++IconRequest;
    FSlateBrush& Brush=bInteraction?InteractionBrush:IconBrush;
    (bInteraction?InteractionIcon:IconTexture)=nullptr;
    Brush.SetResourceObject(nullptr);Brush.DrawAs=ESlateBrushDrawType::NoDrawType;
    if(!bInteraction){bNoticeLoading=true;bNoticeReady=Icon.IsEmpty();}
    if(Icon.IsEmpty() || (bInteraction && FPaths::GetExtension(Icon).IsEmpty()))return;
    const FString Filename=FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Icon;
    const TWeakObjectPtr<UColdSteelProgressNotification> Weak(this);
    // Each surface ignores callbacks for icons it has already replaced.
    Async(EAsyncExecution::ThreadPool,[Weak,Request,Filename,bInteraction]()
    {
        auto Image=MakeShared<FImage,ESPMode::ThreadSafe>();
        const bool Loaded=FImageUtils::LoadImage(*Filename,*Image);
        AsyncTask(ENamedThreads::GameThread,[Weak,Request,Image,Loaded,bInteraction]()
        {
            auto* Self=Weak.Get();
            if(!Self || Request!=(bInteraction?Self->InteractionIconRequest:Self->IconRequest))return;
            auto& Texture=bInteraction?Self->InteractionIcon:Self->IconTexture;
            auto& TargetBrush=bInteraction?Self->InteractionBrush:Self->IconBrush;
            if(Loaded)Texture=FImageUtils::CreateTexture2DFromImage(*Image);
            TargetBrush.SetResourceObject(Texture);
            TargetBrush.DrawAs=Texture?ESlateBrushDrawType::Image:ESlateBrushDrawType::NoDrawType;
            if(!bInteraction)Self->bNoticeReady=true;
        });
    });
}

void UColdSteelProgressNotification::UpdateInteraction()
{
    FColdSteelProgressNotice Next;
    const bool bWasVisible=InteractionRemaining>0.f;
    if(Model && Model->TakeInteractionNotice(Next))
    {
        // Some callers supply a short glyph in place of a texture.
        if(!Next.Icon.IsEmpty() && FPaths::GetExtension(Next.Icon).IsEmpty())
        {
            Next.Title=Next.Icon+TEXT(" ")+Next.Title;
            Next.Icon.Reset();
        }
        const bool bIconChanged=Interaction.Icon!=Next.Icon;
        if(!bWasVisible || Interaction.Title!=Next.Title)InteractionTitle->SetText(FText::FromString(Next.Title));
        if(!bWasVisible || Interaction.Detail!=Next.Detail)
        {
            InteractionDetail->SetText(FText::FromString(Next.Detail));
            InteractionDetail->SetVisibility(Next.Detail.IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible);
        }
        Interaction=MoveTemp(Next);
        InteractionVisibleUntil=FPlatformTime::Seconds()+Interaction.Duration;
        if(bIconChanged)PrepareNoticeIcon(true);
    }
    InteractionRemaining=FMath::Max(0.f,static_cast<float>(InteractionVisibleUntil-FPlatformTime::Seconds()));
    const bool bVisible=InteractionRemaining>0.f;
    if(bVisible!=bWasVisible)
        InteractionRow->SetVisibility(bVisible?EVisibility::HitTestInvisible:EVisibility::Collapsed);
    if(bVisible)InteractionRow->SetRenderOpacity(FMath::Min(1.f,InteractionRemaining/.18f));
}


// Lines 191-191 | void UColdSteelProgressNotification::NativeTick(const FGeometry& Geometry,float Delta)
        if(InteractionRow)UpdateInteraction();

// Lines 219-233 | void UColdSteelProgressNotification::NativeDestruct()
{
    ++IconRequest;
    ++InteractionIconRequest;
    bNoticeLoading=bNoticeReady=bActive=false;
    InteractionRemaining=0.f;
    InteractionVisibleUntil=0.;
    Interaction={};
    InteractionIcon=nullptr;
    InteractionBrush.SetResourceObject(nullptr);
    if(InteractionRow)InteractionRow->SetVisibility(EVisibility::Collapsed);
    if(Card)Card->SetVisibility(EVisibility::Collapsed);
    if(Audio){Audio->Stop();Audio=nullptr;}
    Sound=nullptr;
    Super::NativeDestruct();
}

// Lines 235-242 | void UColdSteelProgressNotification::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    InteractionTitle.Reset();
    InteractionDetail.Reset();
    InteractionRow.Reset();
    Card.Reset();
    Root.Reset();
}
