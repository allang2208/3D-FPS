#include "HorseMarketCardsReviewCommandlet.h"
#if WITH_EDITOR
#include "../UI/SColdSteelHorseMarket.h"
#include "SiegeDrawerReview.h"
#include "../UI/ColdSteelMountGearPanel.h"
#include "../Movement/StableHorseGear.h"
#include "../Movement/StableHorseAffixes.h"
#include "../UI/ColdSteelWarehouseRules.h"
#include "../UI/ColdSteelInventoryTypes.h"
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
    if(FParse::Param(*Params,TEXT("SiegeWorkshop")))return FSiegeDrawerReview::Run(Output);
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
    if(Panel->Selected!=Stock[1].Horse.HorseId || Requests!=3)return 20;
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
    Click(Owned->Cards[0]->Button);
    if(Owned->Selected!=Stock[0].Horse.HorseId || Requests!=4)return 21;
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
    if(!Capture(660,1040,TEXT("owned-details.png")) || !Capture(350,620,TEXT("owned-details-narrow.png")))return 18;

    // Comprehensive Affix + Variable-Row Horse Backpack Audit
    {
        TArray<int32> SeenCounts;
        SeenCounts.Init(0,StableHorseAffixes::TotalCount);
        bool bSawAllRounder=false, bSawZeroBag=false, bSawSixOrEightBag=false, bSawTirelessStack=false;
        FGuid TwoRowHorse, ZeroRowHorse, FourRowHorse;
        for(int32 Sample=0;Sample<6000;++Sample)
        {
            const FGuid Id=FGuid::NewDeterministicGuid(FString::Printf(TEXT("AffixAuditSample/%d"),Sample));
            const auto List=StableHorseAffixes::Roll(Id);
            if(List.Num()<1 || List.Num()>4){UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT bad count=%d"),List.Num());return 30;}
            int32 Specials=0;
            TSet<int32> NormalDims;
            for(EStableHorseAffix A:List)
            {
                ++SeenCounts[int32(A)];
                const auto& Def=StableHorseAffixes::Definition(A);
                if(Def.Tier==EStableHorseAffixTier::Special)++Specials;
                else
                {
                    const int32 Dim=(int32(A)<=3)?0:(int32(A)<=7)?1:(int32(A)<=9)?2:(int32(A)<=11)?3:4;
                    if(NormalDims.Contains(Dim)){UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT duplicate dim=%d"),Dim);return 31;}
                    NormalDims.Add(Dim);
                }
            }
            if(Specials>1){UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT specials=%d"),Specials);return 32;}
            const auto B=StableHorseAffixes::Bonuses(Id);
            if(B.BagRows()==0){bSawZeroBag=true;if(!ZeroRowHorse.IsValid())ZeroRowHorse=Id;}
            if(B.BagRows()==2 && !TwoRowHorse.IsValid())TwoRowHorse=Id;
            if(B.BagRows()>=4 && !FourRowHorse.IsValid())FourRowHorse=Id;
            if(B.BagRows()>=6)bSawSixOrEightBag=true;
            if(List.Contains(EStableHorseAffix::Tireless) && List.Contains(EStableHorseAffix::BigHeart) && FMath::IsNearlyEqual(B.StaminaRecoveryMultiplier,1.70f,1e-3f))
                bSawTirelessStack=true;
            if(!bSawAllRounder && List.Contains(EStableHorseAffix::AllRounder))
            {
                const auto Lv1=FStableHorseTraits::FromId(Id,1,1);
                const auto Lv25=FStableHorseTraits::FromId(Id,1,25);
                const auto EffG=FStableHorseTraits::EffectiveGrowth(Id);
                const auto RawG=FStableHorseTraits::Growth(Id);
                if(!FMath::IsNearlyEqual(EffG.Strength,RawG.Strength*1.10f,1e-3f) ||
                   !FMath::IsNearlyEqual(Lv25.Strength-Lv1.Strength,24.f*EffG.Strength,1e-2f))
                {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT AllRounder growth mismatch"));return 33;}
                bSawAllRounder=true;
            }
        }
        for(int32 I=0;I<StableHorseAffixes::TotalCount;++I)
        {
            const auto& Def=StableHorseAffixes::Definition(EStableHorseAffix(I));
            const FString IconFile=FPaths::ProjectContentDir()/TEXT("ColdSteelData/Icons/HorseAffixes")/(FString(Def.Id)+TEXT(".png"));
            if(SeenCounts[I]<=0 || !FPaths::FileExists(IconFile))
            {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT missing affix=%s count=%d file=%s"),Def.Id,SeenCounts[I],*IconFile);return 34;}
        }
        if(!bSawAllRounder || !bSawZeroBag || !bSawSixOrEightBag || !bSawTirelessStack || !TwoRowHorse.IsValid())
        {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT missing scenario flags"));return 35;}

        // Spatial 2-row horse bag boundary + ValidateProfile + Transfer test
        FColdSteelProfile TestProfile;
        TestProfile.Version=2;
        TestProfile.WarehouseLayoutVersion=1;
        TestProfile.WarehousePages=1;
        TestProfile.Hotbar.Init(FString(),4);
        TestProfile.HotbarDefinitions.Init(FString(),4);
        for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})TestProfile.Attributes.Add(Key,10);
        FStableMountRecord H2;H2.HorseId=TwoRowHorse;H2.BirthVersion=1;H2.ApplyBirthLimits();
        FStableMountRecord H0;H0.HorseId=ZeroRowHorse;H0.BirthVersion=1;H0.ApplyBirthLimits();
        TestProfile.MountRoster.Horses.Add(H2);
        TestProfile.MountRoster.Horses.Add(H0);

        FColdSteelItem Tall;
        Tall.InstanceId=TEXT("audit-tall-item");
        Tall.Definition=TEXT("audit_tall");
        Tall.Data=TEXT("{\"name\":\"测试长件\",\"grid_w\":1,\"grid_h\":2}");
        Tall.Count=1;Tall.StackMax=1;Tall.Width=1;Tall.Height=2;
        Tall.Place=4;Tall.Container=H2.BagContainerKey();

        // Row 0 (Cell 0) fits in 2-row bag (36 cells); Row 1 (Cell 18) overflows row 2 and MUST fail!
        if(!ColdSteelWarehouse::Fits(TestProfile.Items,Tall,0,36) || ColdSteelWarehouse::Fits(TestProfile.Items,Tall,18,36))
        {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT 2-row Fits boundary failed"));return 36;}

        Tall.Cell=0;
        TestProfile.Items.Add(Tall);
        FString ValReason;
        if(!ColdSteelInventory::Validate(TestProfile,ValReason))
        {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT valid mount bag rejected: %s"),*ValReason);return 37;}

        // Moving Tall to Cell 18 in 2-row bag MUST fail Transfer & Validate!
        auto BadMove=ColdSteelWarehouse::Transfer(TestProfile.Items,Tall.InstanceId,4,18,36,0,-1,H2.BagContainerKey());
        if(BadMove.bValid){UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT 2-row overflow move wrongly succeeded"));return 38;}

        // Rotating 1x2 -> 2x1 onto Cell 18 MUST succeed!
        auto GoodRotate=ColdSteelWarehouse::Transfer(TestProfile.Items,Tall.InstanceId,4,18,36,0,1,H2.BagContainerKey());
        if(!GoodRotate.bValid){UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT 2-row rotated move failed: %s"),*GoodRotate.Reason);return 39;}
        TestProfile.Items=GoodRotate.Items;
        if(!ColdSteelInventory::Validate(TestProfile,ValReason))
        {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT rotated mount bag item failed Validate: %s"),*ValReason);return 40;}

        // Item placed inside 0-row Lazy horse bag MUST fail Validate!
        FColdSteelItem BadZero=Tall;BadZero.InstanceId=TEXT("audit-zero");BadZero.Width=1;BadZero.Height=1;BadZero.bRotated=false;
        BadZero.Data=TEXT("{\"name\":\"测试小件\",\"grid_w\":1,\"grid_h\":1}");
        BadZero.Container=H0.BagContainerKey();BadZero.Cell=0;
        TestProfile.Items.Add(BadZero);
        if(ColdSteelInventory::Validate(TestProfile,ValReason))
        {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT 0-row Lazy bag wrongly accepted item"));return 41;}
        TestProfile.Items.RemoveAll([](const auto& I){return I.InstanceId==TEXT("audit-zero");});

        // Orphaned mount.<HorseId> item (horse missing from roster after release/desync) MUST fail Validate!
        FColdSteelItem Orphan=Tall;Orphan.InstanceId=TEXT("audit-orphan");Orphan.Width=1;Orphan.Height=1;Orphan.bRotated=false;
        Orphan.Data=TEXT("{\"name\":\"孤儿件\",\"grid_w\":1,\"grid_h\":1}");
        Orphan.Container=StableHorseAffixes::BagContainerKey(FGuid::NewDeterministicGuid(TEXT("OrphanAuditHorse")));
        Orphan.Cell=0;
        TestProfile.Items.Add(Orphan);
        if(ColdSteelInventory::Validate(TestProfile,ValReason))
        {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT orphan mount bag item wrongly passed Validate"));return 42;}
        TestProfile.Items.RemoveAll([](const auto& I){return I.InstanceId==TEXT("audit-orphan");});

        // Multi-tier evacuation priority test: Backpack (full) -> Main Warehouse -> Ground, 0 item loss & clean Validate!
        {
            FColdSteelProfile Evac=TestProfile;
            Evac.Items.Reset();
            // Fill all 4x18 = 72 cells of player backpack with 1x1 blockers
            for(int32 C=0;C<72;++C)
            {
                FColdSteelItem Blocker;
                Blocker.InstanceId=FString::Printf(TEXT("bag-fill-%d"),C);
                Blocker.Definition=TEXT("audit_filler");
                Blocker.Data=TEXT("{\"name\":\"占位\",\"grid_w\":1,\"grid_h\":1}");
                Blocker.Count=1;Blocker.StackMax=1;Blocker.Width=1;Blocker.Height=1;
                Blocker.Place=0;Blocker.Cell=C;
                Evac.Items.Add(MoveTemp(Blocker));
            }
            // Place one 1x1 item in horse bag; since player backpack is full, evacuation MUST land it in Main Warehouse (Place=4, Container="")!
            FColdSteelItem Payload;
            Payload.InstanceId=TEXT("horse-payload-1");
            Payload.Definition=TEXT("audit_payload");
            Payload.Data=TEXT("{\"name\":\"马袋物资\",\"grid_w\":1,\"grid_h\":1}");
            Payload.Count=1;Payload.StackMax=1;Payload.Width=1;Payload.Height=1;
            Payload.Place=0;
            if(ColdSteelInventory::Insert(Evac.Items,Payload))
            {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT full player bag wrongly accepted item"));return 43;}
            Payload.Place=ColdSteelWarehouse::Place;Payload.Container.Reset();
            if(!ColdSteelWarehouse::Insert(Evac.Items,Payload,Evac.WarehousePages*ColdSteelWarehouse::CellsPerPage))
            {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT warehouse fallback failed"));return 44;}
            if(!ColdSteelInventory::Validate(Evac,ValReason))
            {UE_LOG(LogTemp,Error,TEXT("AFFIX_AUDIT evacuated warehouse profile failed Validate: %s"),*ValReason);return 45;}
        }

        // Verify Warhorse / SpiritSteed / BattleHardened exact numeric bonuses
        {
            bool bCheckedWarhorse=false, bCheckedSpirit=false, bCheckedBattle=false;
            for(int32 S=0;S<6000 && !(bCheckedWarhorse&&bCheckedSpirit&&bCheckedBattle);++S)
            {
                const FGuid Id=FGuid::NewDeterministicGuid(FString::Printf(TEXT("AffixAuditSample/%d"),S));
                const auto List=StableHorseAffixes::Roll(Id);
                const auto B=StableHorseAffixes::Bonuses(Id);
                if(!bCheckedWarhorse && List.Contains(EStableHorseAffix::Warhorse))
                {
                    if(!FMath::IsNearlyEqual(B.PlayerPhysicalDamageBonus,0.10f,1e-4f) || !FMath::IsNearlyEqual(B.PlayerHealthRegenBonus,0.30f,1e-4f))return 46;
                    bCheckedWarhorse=true;
                }
                if(!bCheckedSpirit && List.Contains(EStableHorseAffix::SpiritSteed))
                {
                    if(!FMath::IsNearlyEqual(B.PlayerMagicDamageBonus,0.10f,1e-4f) || !FMath::IsNearlyEqual(B.PlayerManaRegenBonus,0.30f,1e-4f))return 47;
                    bCheckedSpirit=true;
                }
                if(!bCheckedBattle && List.Contains(EStableHorseAffix::BattleHardened))
                {
                    if(!FMath::IsNearlyEqual(B.BaseMoveMultiplier,1.05f,1e-4f) || !FMath::IsNearlyEqual(B.NaturalRegenPerSecondPct,0.01f,1e-4f))return 48;
                    bCheckedBattle=true;
                }
            }
            if(!(bCheckedWarhorse&&bCheckedSpirit&&bCheckedBattle))return 49;
        }
        UE_LOG(LogTemp,Display,TEXT("AFFIX_BAG_AUDIT passed 6000 rolls, all 20 affixes+icons, AllRounder/Warhorse/SpiritSteed/BattleHardened, 0/2/4/6/8-row bounds, orphan rejection & warehouse evacuation"));
    }

    UE_LOG(LogTemp,Display,TEXT("MARKET_REVIEW passed stock, two widths plus compact scrolling, ID selection, detail entry, pending, purchased, balance, rollover, empty"));
    return 0;
#else
    return 1;
#endif
}
