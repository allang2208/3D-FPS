#include "ColdSteelProgressNotification.h"
#include "ColdSteelStatusModel.h"
#include "Async/Async.h"
#include "ImageCore.h"
#include "ColdSteelUIStyle.h"
#include "Audio.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundWaveProcedural.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Colors/SColorBlock.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Notifications/SProgressBar.h"

void UColdSteelProgressNotification::LoadAssets()
{
    Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model)return;
    const FString Base=FPaths::ProjectContentDir()/TEXT("ColdSteelData");
    TArray<uint8> Bytes;
    if(PCM.IsEmpty() && FFileHelper::LoadFileToArray(Bytes,*(Base/Model->RifleDefinition().UpgradeSound)))
    {
        FWaveModInfo Wave;
        if(Wave.ReadWaveInfo(Bytes.GetData(),Bytes.Num()) && *Wave.pBitsPerSample==16 && *Wave.pFormatTag==1)
        {
            SampleRate=*Wave.pSamplesPerSec;Channels=*Wave.pChannels;
            if(SampleRate>0 && (Channels==1||Channels==2))
            {PCM.Append(Wave.SampleDataStart,Wave.SampleDataSize);AudioDuration=float(PCM.Num())/(SampleRate*Channels*2);}
        }
    }
}
TSharedRef<SWidget> UColdSteelProgressNotification::RebuildWidget()
{
    LoadAssets(); SAssignNew(Root,SBox); Root->SetContent(BuildSurface()); return Root.ToSharedRef();
}
TSharedRef<SWidget> UColdSteelProgressNotification::BuildSurface()
{
    // 2026-11-15: game-dev level-up-text format. No plate: optional 48px icon, gold 28px title with a
    // soft gold glow and a 2px dark drop shadow, green 18px detail; centred 10% below the top edge.
    // The project ships Noto Sans SC Regular/Medium only, so the title's weight comes from Medium plus
    // a thin dark outline; the glow is a wider low-alpha gold outline on a duplicate layer behind it.
    Scale=ColdSteelUI::PixelScale(this);
    IconBrush.ImageSize=FVector2D(48/Scale);
    SetVisibility(ESlateVisibility::HitTestInvisible);
    InteractionBrush.ImageSize=FVector2D(20/Scale);
    auto TitleFont=[this](float Outline,const FLinearColor& Color,bool bUpgrade){auto F=ColdSteelUI::TextFont((bUpgrade?28:20)*.75f/Scale,true);F.OutlineSettings.OutlineSize=FMath::Max(1,FMath::RoundToInt(Outline/Scale));F.OutlineSettings.OutlineColor=Color;return F;};
    auto DetailFont=[this]{auto F=ColdSteelUI::TextFont(18*.75f/Scale,true);F.OutlineSettings.OutlineSize=FMath::Max(1,FMath::RoundToInt(1/Scale));F.OutlineSettings.OutlineColor=FLinearColor(0,0,0,.85f);return F;};
    const FLinearColor Glow(ColdSteelUI::NoticeGold.R,ColdSteelUI::NoticeGold.G,ColdSteelUI::NoticeGold.B,.22f);
    auto Title=[this,TitleFont](float Outline,const FLinearColor& OutlineColor,bool bShadow,bool bGlowLayer)
    {
        return SNew(STextBlock).Text_Lambda([this]{return FText::FromString(Active.Title);})
            .Font_Lambda([this,TitleFont,Outline,OutlineColor]{return TitleFont(Outline,OutlineColor,Active.bUpgrade);})
            .ColorAndOpacity_Lambda([this,bGlowLayer]{return FSlateColor(Active.bUpgrade?ColdSteelUI::NoticeGold:bGlowLayer?FLinearColor::Transparent:ColdSteelUI::TextPrimary);})
            .Visibility_Lambda([this,bGlowLayer]{return bGlowLayer&&!Active.bUpgrade?EVisibility::Collapsed:EVisibility::HitTestInvisible;})
            .ShadowOffset(bShadow?FVector2D(0,2/Scale):FVector2D::ZeroVector).ShadowColorAndOpacity(FLinearColor(0,0,0,bShadow?.9f:0.f))
            .Justification(ETextJustify::Center).AutoWrapText(true);
    };
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
        +SOverlay::Slot()[SNew(SColorBlock).Color_Lambda([this]{return FLinearColor(1.f,.86f,.39f,bActive&&Active.bUpgrade?.05f*FMath::Clamp(1-Elapsed/.5f,0.f,1.f):0.f);})]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top)
            .Padding(TAttribute<FMargin>::CreateLambda([this]{return FMargin(20/Scale,GetCachedGeometry().GetLocalSize().Y*.10f,20/Scale,0);}))
        [SNew(SBox).WidthOverride_Lambda([this]{return FOptionalSize(FMath::Max(1.f,FMath::Min(820/Scale,float(GetCachedGeometry().GetLocalSize().X)-40/Scale)));})
            [SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()
            [SAssignNew(Card,SBox)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0,0,0,8/Scale)
                    [SNew(SBox).WidthOverride(48/Scale).HeightOverride(48/Scale)
                        .Visibility_Lambda([this]{return Active.Icon.IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})[SNew(SImage).Image(&IconBrush)]]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
                    [SNew(SOverlay)
                        +SOverlay::Slot()[Title(6,Glow,false,true)]
                        +SOverlay::Slot()[Title(1,FLinearColor(0,0,0,.8f),true,false)]]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0,6/Scale,0,0)
                    [SNew(STextBlock).Text_Lambda([this]{return FText::FromString(Active.Detail);})
                        .Visibility_Lambda([this]{return Active.Detail.IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})
                        .Font(DetailFont()).ColorAndOpacity(ColdSteelUI::NoticeDetail).ShadowOffset(FVector2D(0,2/Scale)).ShadowColorAndOpacity(FLinearColor(0,0,0,.9f))
                        .Justification(ETextJustify::Center).AutoWrapText(true)]]]
            +SVerticalBox::Slot().AutoHeight()[InteractionNotice]]];
    Card->SetVisibility(bActive?EVisibility::HitTestInvisible:EVisibility::Collapsed);
    return Surface;
}
void UColdSteelProgressNotification::PlayCue()
{
    if(Audio){Audio->Stop();Audio=nullptr;}
    if(PCM.IsEmpty())return;
    Sound=NewObject<USoundWaveProcedural>(this);
    Sound->SetSampleRate(SampleRate);Sound->NumChannels=Channels;Sound->Duration=AudioDuration;
    Sound->SoundGroup=SOUNDGROUP_UI;Sound->QueueAudio(PCM.GetData(),PCM.Num());
    Audio=UGameplayStatics::SpawnSound2D(this,Sound,.6f,1.f,0.f,nullptr,false,true);
}
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

void UColdSteelProgressNotification::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    if(Root && !FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this)))Root->SetContent(BuildSurface());
    const bool Paused=UGameplayStatics::IsGamePaused(this);
    if(Audio)Audio->SetPaused(Paused);
    if(!Paused)
    {
        if(InteractionRow)UpdateInteraction();
        if(!bActive && !bNoticeLoading && Model && Model->PopProgressNotice(Active))
            PrepareNoticeIcon();
        if(bNoticeLoading && bNoticeReady)
        {
            bNoticeLoading=bNoticeReady=false;
            bActive=true;Elapsed=0;PlayCue();
        }
        if(bActive)
        {
            Elapsed+=Delta;
            if(Audio && Elapsed>=AudioDuration){Audio->Stop();Audio=nullptr;Sound=nullptr;}
            if(Elapsed>=Active.Duration){bActive=false;Elapsed=0;}
        }
    }
    if(Card)
    {
        // game-dev sceneLabelFade: 0-20% fade in from -10px, hold, 80-100% fade out to -10px.
        const float Edge=FMath::Max(.05f,Active.Duration*.2f);
        const float Alpha=bActive?FMath::Min(FMath::Clamp(Elapsed/Edge,0.f,1.f),FMath::Clamp((Active.Duration-Elapsed)/Edge,0.f,1.f)):0.f;
        // Slate draws a rounded brush's outline with its own vertex channel that ignores RenderOpacity,
        // so an opacity-0 card would still leave its 1px Border stroke on screen. Collapse it when idle.
        Card->SetVisibility(Alpha>0.f?EVisibility::Visible:EVisibility::Collapsed);
        Card->SetRenderOpacity(Alpha);
        Card->SetRenderTransform(FSlateRenderTransform(FVector2D(0,-10*(1-Alpha)/Scale)));
    }
}
void UColdSteelProgressNotification::NativeDestruct()
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
void UColdSteelProgressNotification::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    InteractionTitle.Reset();
    InteractionDetail.Reset();
    InteractionRow.Reset();
    Card.Reset();
    Root.Reset();
}
