#include "ColdSteelProgressNotification.h"
#include "ColdSteelStatusModel.h"
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
    if(!IconTexture && FFileHelper::LoadFileToArray(Bytes,*(Base/Model->RifleDefinition().Icon)))
        IconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
    if(IconTexture){IconBrush.SetResourceObject(IconTexture);IconBrush.DrawAs=ESlateBrushDrawType::Image;}
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
    Scale=ColdSteelUI::PixelScale(this);
    GlassBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale);
    FallbackBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius/Scale);
    IconBrush.ImageSize=FVector2D(48/Scale);
    SetVisibility(ESlateVisibility::HitTestInvisible);
    auto Surface=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SColorBlock).Color_Lambda([this]{return FLinearColor(1,1,1,bActive?.035f*FMath::Clamp(1-Elapsed/.5f,0.f,1.f):0.f);})]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top)
            .Padding(TAttribute<FMargin>::CreateLambda([this]{return FMargin(12/Scale,GetCachedGeometry().GetLocalSize().Y*.10f,12/Scale,0);}))
        [SAssignNew(Card,SBox).WidthOverride_Lambda([this]{return FOptionalSize(FMath::Max(1.f,FMath::Min(640/Scale,float(GetCachedGeometry().GetLocalSize().X)-24/Scale)));})
            [SNew(SBackgroundBlur).BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius)
                .CornerRadius(FVector4(10/Scale)).LowQualityFallbackBrush(&FallbackBrush)
                [SNew(SBorder).BorderImage(&GlassBrush).Padding(FMargin(16/Scale,12/Scale))
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12/Scale,0)
                                [SNew(SBox).WidthOverride(48/Scale).HeightOverride(48/Scale)
                                    .Visibility_Lambda([this]{return Active.Icon.IsEmpty()?EVisibility::Collapsed:EVisibility::Visible;})[SNew(SImage).Image(&IconBrush)]]
                            +SHorizontalBox::Slot().FillWidth(1)[SNew(SVerticalBox)
                                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this]{return FText::FromString(Active.Title);})
                                    .Font_Lambda([this]{return ColdSteelUI::TextFont(20*.75f/Scale,true);}).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(true)]
                                +SVerticalBox::Slot().AutoHeight().Padding(0,6/Scale,0,0)[SNew(STextBlock).Text_Lambda([this]{return FText::FromString(Active.Detail);})
                                    .Font_Lambda([this]{return ColdSteelUI::TextFont(14*.75f/Scale);}).ColorAndOpacity(ColdSteelUI::Success).AutoWrapText(true)]]]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,10/Scale,0,0)[SNew(SBox).HeightOverride(2/Scale)
                            [SNew(SProgressBar).Percent_Lambda([this]()->TOptional<float>{return bActive?FMath::Clamp(Elapsed/Active.Duration,0.f,1.f):0.f;})
                                .FillColorAndOpacity(ColdSteelUI::Accent)]]]]]];
    Card->SetRenderOpacity(0);
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
void UColdSteelProgressNotification::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    if(Root && !FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this)))Root->SetContent(BuildSurface());
    const bool Paused=UGameplayStatics::IsGamePaused(this);
    if(Audio)Audio->SetPaused(Paused);
    if(!Paused)
    {
        if(!bActive && Model && Model->PopProgressNotice(Active)){bActive=true;Elapsed=0;PlayCue();}
        if(bActive)
        {
            Elapsed+=Delta;
            if(Audio && Elapsed>=AudioDuration){Audio->Stop();Audio=nullptr;Sound=nullptr;}
            if(Elapsed>=Active.Duration){bActive=false;Elapsed=0;}
        }
    }
    if(Card)
    {
        const float Alpha=bActive?FMath::Min(FMath::Clamp(Elapsed/.18f,0.f,1.f),FMath::Clamp((Active.Duration-Elapsed)/.35f,0.f,1.f)):0.f;
        Card->SetRenderOpacity(Alpha);
        Card->SetRenderTransform(FSlateRenderTransform(FVector2D(0,-8*(1-Alpha)/Scale)));
    }
}
void UColdSteelProgressNotification::NativeDestruct()
{if(Audio){Audio->Stop();Audio=nullptr;}Sound=nullptr;Super::NativeDestruct();}
void UColdSteelProgressNotification::ReleaseSlateResources(bool bReleaseChildren)
{Super::ReleaseSlateResources(bReleaseChildren);Card.Reset();Root.Reset();}
