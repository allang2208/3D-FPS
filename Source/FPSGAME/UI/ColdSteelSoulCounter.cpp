#include "ColdSteelSoulCounter.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelCurrency.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/Border.h"
#include "Components/Image.h"
#include "Async/Async.h"
#include "Engine/Texture2D.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

void UColdSteelSoulCounter::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);SetVisibility(ESlateVisibility::HitTestInvisible);
    Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    Background=WidgetTree->ConstructWidget<UBorder>();Background->SetPadding(FMargin(0));
    Background->SetVisibility(ESlateVisibility::HitTestInvisible);Root->AddChildToCanvas(Background)->SetZOrder(0);
    SoulIcon=WidgetTree->ConstructWidget<UImage>();SoulIcon->SetVisibility(ESlateVisibility::Hidden);
    Root->AddChildToCanvas(SoulIcon)->SetZOrder(1);
    auto MakeText=[this]()
    {
        auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetAutoWrapText(false);
        Label->SetVisibility(ESlateVisibility::HitTestInvisible);Root->AddChildToCanvas(Label)->SetZOrder(1);return Label;
    };
    Caption=MakeText();Caption->SetText(FText::FromString(TEXT("灵魂")));Caption->SetColorAndOpacity(ColdSteelUI::HUDGoldLight);
    Number=MakeText();Number->SetJustification(ETextJustify::Right);Number->SetRenderTransformPivot(FVector2D(1,.5));
    Number->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    for(int32 I=0;I<3;++I){auto* Label=MakeText();Label->SetJustification(ETextJustify::Right);Label->SetVisibility(ESlateVisibility::Collapsed);DeltaLabels.Add(Label);}
    SetDisplayScale(ColdSteelUI::PixelScale(this));RefreshNumber();LoadSoulIcon();
}

void UColdSteelSoulCounter::SetDisplayScale(float Value)
{
    Scale=FMath::Max(.01f,Value);
    if(!Caption)return;
    Surface=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,8/Scale,ColdSteelUI::Border,1/Scale);
    Background->SetBrush(Surface);
    auto* BackgroundSlot=CastChecked<UCanvasPanelSlot>(Background->Slot);BackgroundSlot->SetAnchors(FAnchors(0,0,1,0));
    BackgroundSlot->SetOffsets(FMargin(0,40/Scale,0,40/Scale));
    auto* IconSlot=CastChecked<UCanvasPanelSlot>(SoulIcon->Slot);
    IconSlot->SetPosition(FVector2D(8,44)/Scale);IconSlot->SetSize(FVector2D(32,32)/Scale);
    Caption->SetFont(ColdSteelUI::TextFont(14*.75f/Scale));
    Number->SetFont(ColdSteelUI::NumberFont(20*.75f/Scale,true));
    auto* NameSlot=CastChecked<UCanvasPanelSlot>(Caption->Slot);
    NameSlot->SetPosition(FVector2D(42,51)/Scale);NameSlot->SetSize(FVector2D(40,24)/Scale);
    auto* NumberSlot=CastChecked<UCanvasPanelSlot>(Number->Slot);NumberSlot->SetAnchors(FAnchors(0,0,1,0));
    NumberSlot->SetOffsets(FMargin(86/Scale,47/Scale,12/Scale,28/Scale));
    for(const auto& Label:DeltaLabels)
    {
        Label->SetFont(ColdSteelUI::NumberFont(14*.75f/Scale));
        auto* DeltaSlot=CastChecked<UCanvasPanelSlot>(Label->Slot);DeltaSlot->SetAnchors(FAnchors(0,0,1,0));
        DeltaSlot->SetOffsets(FMargin(6/Scale,0,12/Scale,18/Scale));
    }
    RefreshDeltas();
}

void UColdSteelSoulCounter::SetBalance(int64 Value,bool Animate)
{
    Value=FMath::Clamp<int64>(Value,0,ColdSteelCurrency::MaxSouls);
    if(!Initialized || !Animate)
    {
        if(Initialized&&Value==Target&&Elapsed>=.55f&&Deltas.IsEmpty())return;
        Initialized=true;Target=Value;Display=From=double(Value);Elapsed=.55f;
        if(!Deltas.IsEmpty()){Deltas.Reset();RefreshDeltas();}
        if(Number){Number->SetRenderScale(FVector2D(1));Number->SetColorAndOpacity(ColdSteelUI::TextPrimary);}RefreshNumber();return;
    }
    if(Value==Target)return;
    const int64 Difference=Value-Target;
    From=Display;Target=Value;Elapsed=0;
    if(!Deltas.IsEmpty()&&Deltas[0].Age<.18f&&((Deltas[0].Amount>0)==(Difference>0)))
    {Deltas[0].Amount+=Difference;Deltas[0].Age=0;}
    else {Deltas.Insert({Difference,0},0);if(Deltas.Num()>3)Deltas.SetNum(3);}
    RefreshDeltas();
}

void UColdSteelSoulCounter::RefreshNumber()
{
    if(!Number)return;
    const int64 Value=Elapsed>=.55f?Target:FMath::RoundToInt64(Display);
    if(Value!=LastDrawn){LastDrawn=Value;Number->SetText(FText::AsNumber(Value));}
}

void UColdSteelSoulCounter::RefreshDeltas()
{
    for(int32 I=0;I<DeltaLabels.Num();++I)
    {
        auto* Label=DeltaLabels[I].Get();
        if(!Deltas.IsValidIndex(I)){Label->SetVisibility(ESlateVisibility::Collapsed);continue;}
        const auto& Delta=Deltas[I];const bool Gain=Delta.Amount>0;
        const FText Text=FText::FromString(FString::Printf(TEXT("%s %s 灵魂"),Gain?TEXT("+"):TEXT("−"),*FText::AsNumber(FMath::Abs(Delta.Amount)).ToString()));
        if(!Label->GetText().EqualTo(Text))Label->SetText(Text);
        Label->SetColorAndOpacity(Gain?ColdSteelUI::HUDGoldLight:ColdSteelUI::Danger);
        Label->SetRenderOpacity(Delta.Age<.55f?1.f:FMath::Clamp((1.25f-Delta.Age)/.7f,0.f,1.f));
        Label->SetRenderTranslation(FVector2D(0,(28-I*12-4*FMath::Clamp(Delta.Age/1.25f,0.f,1.f))/Scale));
        Label->SetVisibility(ESlateVisibility::HitTestInvisible);
    }
}

void UColdSteelSoulCounter::NativeTick(const FGeometry& G,float Dt)
{
    Super::NativeTick(G,Dt);
    if(Elapsed<.55f)
    {
        Elapsed=FMath::Min(.55f,Elapsed+Dt);const double T=Elapsed/.55;
        Display=FMath::Lerp(From,double(Target),1-FMath::Pow(1-T,3));
        const float Pulse=1.f+.07f*FMath::Sin(float(T)*PI);
        Number->SetRenderScale(FVector2D(Pulse));
        Number->SetColorAndOpacity(FMath::Lerp(Target>=From?ColdSteelUI::HUDGoldLight:ColdSteelUI::Danger,ColdSteelUI::TextPrimary,float(T)));
        RefreshNumber();
    }
    if(!Deltas.IsEmpty())
    {
        for(auto& Delta:Deltas)Delta.Age+=Dt;
        Deltas.RemoveAll([](const FDelta& Delta){return Delta.Age>=1.25f;});RefreshDeltas();
    }
}

void UColdSteelSoulCounter::LoadSoulIcon()
{
    const FString Filename=FPaths::ProjectContentDir()/TEXT("ColdSteelData/Currency/soul-gold-flame.png");
    const TWeakObjectPtr<UColdSteelSoulCounter> Weak(this);
    Async(EAsyncExecution::ThreadPool,[Weak,Filename]()
    {
        FImage Source;
        if(!FImageUtils::LoadImage(*Filename,Source))return;
        auto Thumbnail=MakeShared<FImage,ESPMode::ThreadSafe>();
        const float Factor=FMath::Min(1.f,128.f/FMath::Max(Source.SizeX,Source.SizeY));
        FImageCore::ResizeImageAllocDest(Source,*Thumbnail,
            FMath::Max(1,FMath::RoundToInt(Source.SizeX*Factor)),FMath::Max(1,FMath::RoundToInt(Source.SizeY*Factor)),
            ERawImageFormat::BGRA8,EGammaSpace::sRGB);
        AsyncTask(ENamedThreads::GameThread,[Weak,Thumbnail]()
        {
            auto* Self=Weak.Get();if(!Self||!Self->SoulIcon)return;
            if(auto* Texture=FImageUtils::CreateTexture2DFromImage(*Thumbnail))
            {
                Self->SoulIcon->SetBrushFromTexture(Texture);
                Self->SoulIcon->SetVisibility(ESlateVisibility::HitTestInvisible);
            }
        });
    });
}
