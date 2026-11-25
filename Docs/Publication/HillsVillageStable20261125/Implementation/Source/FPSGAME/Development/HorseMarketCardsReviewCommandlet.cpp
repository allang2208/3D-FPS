#include "HorseMarketCardsReviewCommandlet.h"
#if WITH_EDITOR
#include "../UI/SColdSteelHorseMarket.h"
#include "../UI/ColdSteelMountGearPanel.h"
#include "../Movement/StableHorseGear.h"
#include "Editor.h"
#include "../Movement/StableHorseAppearance.h"
#include "../UI/ColdSteelUIStyle.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Framework/Application/SlateApplication.h"
#include "Interfaces/ISlateRHIRendererModule.h"
#include "Slate/WidgetRenderer.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Brushes/SlateNoResource.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "RenderingThread.h"
#endif

int32 UHorseMarketCardsReviewCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Output;
    if(!FParse::Value(*Params,TEXT("Output="),Output) || Output.IsEmpty())return 1;
    if(!FSlateApplication::IsInitialized())
    {
        auto& Module=FModuleManager::LoadModuleChecked<ISlateRHIRendererModule>(TEXT("SlateRHIRenderer"));
        FSlateApplication::InitializeAsStandaloneApplication(Module.CreateSlateRHIRenderer());
    }
    IFileManager::Get().MakeDirectory(*Output,true);
    FGuid Bought;
    int32 Requests=0;
    auto Panel=SNew(SColdSteelHorseMarket).OnDetails(SColdSteelHorseMarket::FOpenHorse::CreateLambda(
        [&](FGuid Id){Bought=Id;++Requests;}));
    if(!Panel->Atlas.IsValid() || !Panel->SoftAtlas.IsValid())return 2;
    FWidgetRenderer Renderer(true,true);
    const FSlateBrush Back=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,8);
    auto Surface=SNew(SBorder).BorderImage(&Back).Padding(8)[Panel];
    auto Capture=[&](int32 Width,int32 Height,const TCHAR* Filename)
    {
        FVector2D Size(Width,Height);
        // Slate already applies display gamma. A linear target avoids encoding a second time.
        TStrongObjectPtr<UTextureRenderTarget2D> Target(FWidgetRenderer::CreateTargetFor(Size,TF_Bilinear,false));
        if(!Target.IsValid())return false;
        for(int32 I=0;I<9;++I)Renderer.DrawWidget(Target.Get(),Surface,Size,.1f);
        FlushRenderingCommands();
        TArray<FColor> Pixels;
        FReadSurfaceDataFlags Read(RCM_UNorm);
        Read.SetLinearToGamma(false);
        if(!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels,Read))return false;
        TArray64<uint8> PNG;
        FImageUtils::PNGCompressImageArray(Width,Height,Pixels,PNG);
        return FFileHelper::SaveArrayToFile(PNG,*(Output/Filename));
    };
    auto Click=[](const TSharedPtr<SButton>& Button)
    {
        const FKeyEvent Enter(EKeys::Enter,FModifierKeysState(),0,false,0,0);
        Button->OnKeyDown(Button->GetCachedGeometry(),Enter);
        Button->OnKeyUp(Button->GetCachedGeometry(),Enter);
    };
    const FGuid Profile(0x4a69,0x12c7,0x33d0,0x5086);
    FStableMountRoster Roster;
    int32 Day=0;
    TArray<FStableHorseOffer> Stock;
    for(;Day<365;++Day)
    {
        Stock=StableHorseMarket::Stock(Profile,Day);
        TSet<int32> Coats;
        bool Patterned=false;
        for(const auto& Offer:Stock)
        {
            const auto Look=FStableHorseAppearance::FromId(Offer.Horse.HorseId);
            Coats.Add(Look.Coat);
            Patterned|=Look.Pattern!=0;
        }
        if(Coats.Num()==4 && Patterned)break;
    }
    if(Day==365)return 14;
    Panel->SetStock(Stock,Roster,Day,5000,false);
    if(Panel->Cards.Num()!=4 || !Capture(906,910,TEXT("market-wide.png")))return 3;
    auto LayoutOK=[&](int32 ExpectedColumns)
    {
        const FGeometry& One=Panel->Cards[0]->Button->GetCachedGeometry();
        const FGeometry& Two=Panel->Cards[1]->Button->GetCachedGeometry();
        const FVector2D Span=Two.GetAbsolutePosition()-One.GetAbsolutePosition();
        UE_LOG(LogTemp,Display,TEXT("MARKET_REVIEW columns=%d card=%.0fx%.0f next=(%.0f,%.0f)"),
            Panel->Columns,One.GetLocalSize().X,One.GetLocalSize().Y,Span.X,Span.Y);
        return Panel->Columns==ExpectedColumns && One.GetLocalSize().X>240 && One.GetLocalSize().Y>140 &&
            (ExpectedColumns==2 ? Span.X>=One.GetLocalSize().X && FMath::Abs(Span.Y)<1 :
                                  Span.Y>=One.GetLocalSize().Y && FMath::Abs(Span.X)<1);
    };
    if(!LayoutOK(2))return 4;
    const FPointerEvent Pointer;
    const auto& Hover=Panel->Cards[1];
    Hover->Button->OnMouseEnter(Hover->Button->GetCachedGeometry(),Pointer);
    if(!Capture(906,910,TEXT("market-hover.png")) || Hover->Reveal<.99f || Panel->Selected!=Stock[0].Horse.HorseId)return 15;
    Hover->Button->OnMouseLeave(Pointer);
    Click(Panel->Cards[2]->BuyButton);
    if(Requests!=1 || Bought!=Stock[2].Horse.HorseId)return 5;
    Panel->SetStock(Stock,Roster,Day,5000,true);
    Click(Panel->Cards[2]->BuyButton);
    if(Requests!=2)return 6;
    Roster.Horses.Add(Stock[2].Horse);
    Panel->SetStock(Stock,Roster,Day,5000,false);
    Click(Panel->Cards[2]->BuyButton);
    if(!Panel->Cards[2]->Sold || Requests!=3)return 7;
    Click(Panel->Cards[1]->Button);
    Panel->SetStock(Stock,Roster,Day,10,false);
    if(!Capture(612,606,TEXT("market-720p.png")) || !LayoutOK(2))return 8;
    Click(Panel->Cards[1]->BuyButton);
    if(Requests!=4 || !Panel->Cards[1]->Status->GetText().ToString().Contains(TEXT("还差")))return 9;
    if(!Capture(440,450,TEXT("market-compact.png")) || !LayoutOK(1))return 10;
    Panel->Scroll->ScrollToEnd();
    if(!Capture(440,450,TEXT("market-compact-end.png")) || Panel->Scroll->GetScrollOffset()<=0)return 11;
    Panel->SetStock(StableHorseMarket::Stock(Profile,Day+1),Roster,Day+1,5000,false);
    if(Panel->Selected==Stock[1].Horse.HorseId || !Panel->Cards[0]->BuyButton->IsEnabled())return 12;
    Panel->SetStock({},Roster,Day+2,5000,false);
    if(!Panel->Cards.IsEmpty() || Panel->Selected.IsValid() || Requests!=4)return 13;
    // Exercise the owned catalog and the production detail widget with item identity
    // and same-name records, then lay out both supported drawer widths.
    auto Owned=SNew(SColdSteelHorseMarket).Owned(true).OnDetails(SColdSteelHorseMarket::FOpenHorse::CreateLambda(
        [&](FGuid Id){Bought=Id;++Requests;}));
    Surface->SetContent(Owned);
    FStableMountRoster Personal;
    Personal.Horses.Add(Stock[0].Horse);
    FStableMountRecord Duplicate=Stock[0].Horse;
    do {++Duplicate.HorseId.A;} while(Duplicate.DisplayName()!=Personal.Horses[0].DisplayName());
    Personal.Horses.Add(Duplicate);Personal.Deployed=Duplicate.HorseId;
    Owned->SetRoster(Personal);
    if(Owned->Cards.Num()!=2 || Owned->Cards[0]->Name==Owned->Cards[1]->Name || !Capture(480,660,TEXT("owned-list.png")))return 16;
    Click(Owned->Cards[1]->BuyButton);
    if(Bought!=Duplicate.HorseId || Requests!=5)return 17;
    TStrongObjectPtr<UColdSteelMountGearPanel> Details(NewObject<UColdSteelMountGearPanel>(GEditor->GetEditorWorldContext().World()));
    if(!Details->Initialize())return 19;
    const auto DetailWidget=Details->TakeWidget();
    auto& Subject=Personal.Horses[1];
    FColdSteelItem Piece;Piece.Definition=StableHorseGear::Definitions[1];Piece.InstanceId=TEXT("preview-saddle");
    Piece.Data=TEXT("{\"name\":\"皮革马鞍\",\"rarity\":\"common\"}");Subject.Equipment.Add(Piece);
    Details->ShowHorse(nullptr,Subject,true,Owned->Cards[1]->Name);
    Details->UpdateCondition(Subject,TEXT("跟随中"),Subject.MaxHealth*.70f,Subject.MaxStamina*.84f);
    static const FScrollBoxStyle DetailScroll=FScrollBoxStyle().SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource());
    Surface->SetContent(SNew(SScrollBox).Style(&DetailScroll).ScrollBarVisibility(EVisibility::Collapsed)+SScrollBox::Slot()[SNew(SDPIScaler).DPIScale(ColdSteelUI::PixelScale(Details.Get()))[DetailWidget]]);
    if(!Capture(630,820,TEXT("owned-details.png")) || !Capture(350,550,TEXT("owned-details-narrow.png")))return 18;
    UE_LOG(LogTemp,Display,TEXT("MARKET_REVIEW passed stock, two widths plus compact scrolling, ID selection, detail entry, pending, purchased, balance, rollover, empty"));
    return 0;
#else
    return 1;
#endif
}
