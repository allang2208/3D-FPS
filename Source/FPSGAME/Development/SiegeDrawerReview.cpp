#include "SiegeDrawerReview.h"
#if WITH_EDITOR
#include "../UI/ColdSteelNpcDialogue.h"
#include "../UI/ColdSteelNpcDialogueSpeech.h"
#include "../UI/SSiegeWorkshopMarket.h"
#include "../UI/SSmartTurretDrawer.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/VillageMasterArtisan.h"
#include "../WorldGeneration/VillageSiegeUpgrades.h"
#include "../WorldGeneration/VillageSmartTurret.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "Slate/SceneViewport.h"
#include "Slate/WidgetRenderer.h"
#include "Widgets/SViewport.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Engine/Texture2D.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Async/TaskGraphInterfaces.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"
#include "RenderingThread.h"

namespace
{
class FReviewViewport final : public FSceneViewport
{
public:
    using FSceneViewport::FSceneViewport;
    FIntPoint Pixels{1440,900};
    virtual FIntPoint GetSizeXY() const override {return Pixels;}
};
}
int32 FSiegeDrawerReview::Run(const FString& Output)
{
    const FString Profile=TEXT("SiegeDrawerAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    TStrongObjectPtr<UGameInstance> GI(NewObject<UGameInstance>(GEngine));
    GI->InitializeStandalone(TEXT("SiegeDrawerAudit"));
    FCommandLine::Set(*Original);
    UWorld* World=GI->GetWorld();
    if(!World)return 2;
    ON_SCOPE_EXIT{GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Wallet=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!Wallet || !Wallet->IsAudit() || Wallet->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 3;
    auto& Context=GEngine->GetWorldContextFromWorldChecked(World);
    auto* Client=NewObject<UGameViewportClient>(GEngine);
    FReviewViewport View{TSharedPtr<SViewport>()};
    Context.GameViewport=Client;Client->Viewport=&View;
    ON_SCOPE_EXIT{Client->Viewport=nullptr;Context.GameViewport=nullptr;};
    AActor* Owner=World->SpawnActor<AActor>();
    auto* Master=World->SpawnActor<AVillageMasterArtisan>();
    if(!Owner || !Master)return 4;
    auto* Conversation=NewObject<UChapelDialogueComponent>(Owner);
    Owner->AddInstanceComponent(Conversation);Conversation->RegisterComponent();
    TStrongObjectPtr<UColdSteelNpcDialogue> Dialogue(NewObject<UColdSteelNpcDialogue>(World));
    Dialogue->Initialize();Dialogue->Configure(Conversation);
    Conversation->LocalMerchant=Master;Conversation->Screen=Dialogue.Get();
    using namespace VillageSiegeUpgrades;
    uint64 SeedRanks=0;
    SeedRanks=SetRank(SeedRanks,Index(Trebuchet,Damage),6);
    SeedRanks=SetRank(SeedRanks,Index(Trebuchet,Reload),4);
    SeedRanks=SetRank(SeedRanks,Index(Trebuchet,Special),2);
    SeedRanks=SetRank(SeedRanks,Index(Trebuchet,Reach),9);
    SeedRanks=SetRank(SeedRanks,Index(Ballista,Damage),7);
    SeedRanks=SetRank(SeedRanks,Index(Ballista,Reload),3);
    SeedRanks=SetRank(SeedRanks,Index(Ballista,Special),2);
    SeedRanks=SetRank(SeedRanks,Index(Ballista,Reach),5);
    SeedRanks=SetRank(SeedRanks,Index(HotOil,OilDamage),5);
    SeedRanks=SetRank(SeedRanks,Index(HotOil,OilRadius),8);
    SeedRanks=SetRank(SeedRanks,Index(HotOil,OilDuration),2);
    SeedRanks=SetRank(SeedRanks,Index(HotOil,OilBurnStacks),1);
    SeedRanks=SetRank(SeedRanks,Index(LightningSpire,SpireDamage),6);
    SeedRanks=SetRank(SeedRanks,Index(LightningSpire,SpireReach),4);
    SeedRanks=SetRank(SeedRanks,Index(LightningSpire,SpireCooldown),3);
    SeedRanks=SetRank(SeedRanks,Index(LightningSpire,SpireElectrify),1);
    Conversation->ConfirmedWorkshopRanks=SeedRanks;
    Conversation->ConfirmedWorkshopCredits=3000;
    auto Widget=Dialogue->TakeWidget();
    auto Layer=SNew(SOverlay);
    TStrongObjectPtr<UTexture2D> Backdrop;
    FSlateBrush BackdropBrush;
    FString BackdropFile;
    if(FParse::Value(FCommandLine::Get(),TEXT("SiegeBackdrop="),BackdropFile))
    {
        Backdrop.Reset(FImageUtils::ImportFileAsTexture2D(BackdropFile));
        if(!Backdrop.IsValid())return 18;
        BackdropBrush.SetResourceObject(Backdrop.Get());
        BackdropBrush.SetImageSize(FVector2D(Backdrop->GetSizeX(),Backdrop->GetSizeY()));
        BackdropBrush.DrawAs=ESlateBrushDrawType::Image;
        Layer->AddSlot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&BackdropBrush)]];
    }
    Layer->AddSlot()[SNew(SDPIScaler).DPIScale_Lambda([&]{return UWidgetLayoutLibrary::GetViewportScale(Dialogue.Get());})[Widget]];
    FWidgetRenderer Renderer(true,true);
    auto Capture=[&](const TCHAR* Name,int32 Width,int32 Height,int32 Frames=10)
    {
        View.Pixels=FIntPoint(Width,Height);
        FVector2D Size(Width,Height);
        TStrongObjectPtr<UTextureRenderTarget2D> Target(FWidgetRenderer::CreateTargetFor(Size,TF_Bilinear,false));
        for(int32 I=0;I<Frames;++I)
        {
            Renderer.DrawWidget(Target.Get(),Layer,Size,.04f);
            FTaskGraphInterface::Get().ProcessThreadUntilIdle(ENamedThreads::GameThread);
        }
        FlushRenderingCommands();TArray<FColor> Pixels;
        FReadSurfaceDataFlags Read(RCM_UNorm);Read.SetLinearToGamma(false);
        if(!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels,Read))return false;
        TArray64<uint8> Data;FImageUtils::PNGCompressImageArray(Width,Height,Pixels,Data);
        return FFileHelper::SaveArrayToFile(Data,*(Output/(FString(Name)+TEXT(".png"))));
    };
    auto Reveal=[&]{if(Dialogue->Speech)for(int32 I=0;I<8 && Dialogue->Speech->HasMore();++I)Dialogue->Speech->RevealOrAdvance();};
    auto Click=[](const TSharedPtr<SButton>& Button)
    {
        FKeyEvent Key(EKeys::Enter,FModifierKeysState(),0,false,0,0);
        Button->OnKeyDown(Button->GetCachedGeometry(),Key);
        Button->OnKeyUp(Button->GetCachedGeometry(),Key);
    };
    Reveal();
    if(!Capture(TEXT("01-dialogue"),1440,900))return 5;
    Dialogue->ChooseMerchantAction(2);
    if(!Dialogue->WorkshopMarket || !Capture(TEXT("01b-opening"),1440,900,2) || !Capture(TEXT("02-trebuchet"),1440,900))return 6;
    auto Market=Dialogue->WorkshopMarket;
    const auto& Frame=Market->Drawer->GetCachedGeometry();
    const FVector2D Left=Frame.GetAbsolutePosition(),Right=Frame.LocalToAbsolute(Frame.GetLocalSize());
    UE_LOG(LogTemp,Display,TEXT("WORKSHOP_DRAWER desktop left=%.1f right=%.1f width=%.1f open=%.2f"),Left.X,Right.X,Frame.GetLocalSize().X,Market->OpenFraction);
    if(Left.X<=720 || FMath::Abs(Right.X-1440.f)>3.f || Market->OpenFraction<1.f)return 11;
    if(Market->Offers[4].Buy->IsEnabled())return 24;
    Market->OffersScroll->ScrollToEnd();
    if(!Capture(TEXT("02b-trebuchet-hotoil-locked"),1440,900))return 25;
    Conversation->ConfirmedWorkshopExtraRanks=SetRank(FRanks{SeedRanks,0},TrebuchetHotOilIdx,1).High;
    Dialogue->Refresh();
    Market->OffersScroll->ScrollToEnd();
    if(!Capture(TEXT("02c-trebuchet-hotoil-unlocked"),1440,900) || Market->Offers[4].Full->GetVisibility()!=EVisibility::HitTestInvisible)return 26;
    Market->OffersScroll->ScrollToStart();
    Click(Market->Tabs[1]);
    if(Market->Selected!=1 || !Capture(TEXT("03-ballista"),1440,900))return 7;
    Click(Market->Tabs[2]);
    if(Market->Selected!=2 || !Capture(TEXT("03c-hotoil"),1440,900))return 21;
    if(Market->Tabs.Num()<5)return 22;
    Click(Market->Tabs[3]);
    if(Market->Selected!=3 || !Capture(TEXT("03d-spire"),1440,900))return 23;
    FRanks SeedAll{SeedRanks, 0};
    SeedAll=SetRank(SeedAll,Index(SmartTurret,TurretDamage),5);
    SeedAll=SetRank(SeedAll,Index(SmartTurret,TurretFeed),4);
    SeedAll=SetRank(SeedAll,Index(SmartTurret,TurretOptics),6);
    SeedAll=SetRank(SeedAll,Index(SmartTurret,TurretWeakpoint),2);
    SeedAll=SetRank(SeedAll,Index(SmartTurret,TurretMagExpand),1);
    SeedAll=SetRank(SeedAll,Index(SmartTurret,TurretPierce),2);
    Conversation->ConfirmedWorkshopExtraRanks=SeedAll.High;
    Dialogue->Refresh();
    Click(Market->Tabs[4]);
    Market->OffersScroll->ScrollToStart();
    if(Market->Selected!=4 || !Capture(TEXT("03e-smart-turret"),1440,900))return 27;
    Market->OffersScroll->ScrollToEnd();
    if(!Capture(TEXT("03f-smart-turret-bottom"),1440,900))return 28;
    Market->OffersScroll->ScrollToStart();
    Click(Market->Tabs[3]);
    Conversation->bPending=true;Dialogue->Refresh();
    if(!Capture(TEXT("03b-pending"),1440,900) || Market->Offers[0].Buy->IsEnabled())return 12;
    Conversation->bPending=false;
    Conversation->ConfirmedWorkshopRanks=SetRank(SeedRanks,Index(LightningSpire,SpireDamage),15);
    Conversation->ConfirmedWorkshopCredits=0;
    Conversation->ConfirmedWorkshopDebits=Wallet->SoulBalance();
    Conversation->Message=TEXT("升级完成，村庄内的同类设施已生效。");
    Dialogue->Refresh();
    if(!Capture(TEXT("04-compact"),1024,576) || !Market->bCompactHeader || Market->Offers[0].Full->GetVisibility()!=EVisibility::HitTestInvisible)return 8;
    const auto& Last=Market->Offers[3].Buy->GetCachedGeometry();
    UE_LOG(LogTemp,Display,TEXT("WORKSHOP_DRAWER compact last-action-bottom=%.1f viewport-height=576"),Last.LocalToAbsolute(Last.GetLocalSize()).Y);
    if(Market->Offers[0].Buy->IsEnabled() || Market->Offers[1].Buy->IsEnabled())return 13;
    if(!Capture(TEXT("04b-short"),800,450))return 14;
    Market->OffersScroll->ScrollToEnd();
    if(!Capture(TEXT("04c-scroll"),800,450) || Market->OffersScroll->GetScrollOffset()<=0.)return 15;
    const FKeyEvent Escape(EKeys::Escape,FModifierKeysState(),0,false,0,0);
    Dialogue->NativeOnPreviewKeyDown(FGeometry(),Escape);
    if(!Market->bClosing || !Capture(TEXT("04d-closing"),800,450,2))return 16;
    if(!Capture(TEXT("05-return"),1440,900) || Dialogue->WorkshopMarket || Dialogue->Page!=0 || !Dialogue->DefaultChoice)return 9;
    Dialogue->ChooseMerchantAction(2);
    if(!Capture(TEXT("06-reopen"),1440,900) || !Dialogue->WorkshopMarket || Dialogue->WorkshopMarket->OpenFraction<1.f)return 17;
    TFunction<TSharedPtr<SButton>(const TSharedRef<SWidget>&)> FindClose=[&](const TSharedRef<SWidget>& Node)->TSharedPtr<SButton>
    {
        if(Node->GetTypeAsString()==TEXT("SButton") && Node->GetToolTip().IsValid())return StaticCastSharedRef<SButton>(Node);
        FChildren* Children=Node->GetChildren();
        for(int32 I=0;Children && I<Children->Num();++I)
            if(auto Button=FindClose(Children->GetChildAt(I)))return Button;
        return nullptr;
    };
    auto Close=FindClose(Dialogue->WorkshopMarket.ToSharedRef());
    if(!Close)return 19;
    Click(Close);
    if(!Capture(TEXT("07-button-return"),1440,900) || Dialogue->Page!=0 || Dialogue->WorkshopMarket)return 20;
    UE_LOG(LogTemp,Display,TEXT("WORKSHOP_DRAWER passed enter, switch, pending, full rank, affordability, short scrolling, escape, reopen and close button"));
    Conversation->Screen=nullptr;
    return 0;
}

int32 FSiegeDrawerReview::RunSmartTurret(const FString& Output)
{
    const FString ProfileId=TEXT("SmartTurretUIAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+ProfileId));
    TStrongObjectPtr<UGameInstance> GI(NewObject<UGameInstance>(GEngine));
    GI->InitializeStandalone(TEXT("SmartTurretUIAudit"));
    FCommandLine::Set(*Original);
    UWorld* World=GI->GetWorld();
    if(!World)return 2;
    ON_SCOPE_EXIT{GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Wallet=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!Wallet || !Wallet->IsAudit())return 3;

    auto& Context=GEngine->GetWorldContextFromWorldChecked(World);
    auto* Client=NewObject<UGameViewportClient>(GEngine);
    FReviewViewport View{TSharedPtr<SViewport>()};
    Context.GameViewport=Client;Client->Viewport=&View;
    ON_SCOPE_EXIT{Client->Viewport=nullptr;Context.GameViewport=nullptr;};

    auto* Hills=World->SpawnActor<ATemperateHillsWorld>();
    auto* Turret=World->SpawnActor<AVillageSmartTurret>();
    if(!Hills || !Turret)return 4;

    using namespace VillageSiegeUpgrades;
    FRanks Ranks{};
    Ranks=SetRank(Ranks,Index(SmartTurret,TurretDamage),8);
    Ranks=SetRank(Ranks,Index(SmartTurret,TurretFeed),6);
    Ranks=SetRank(Ranks,Index(SmartTurret,TurretOptics),6);
    Ranks=SetRank(Ranks,Index(SmartTurret,TurretWeakpoint),2);
    Ranks=SetRank(Ranks,Index(SmartTurret,TurretMagExpand),2);
    Ranks=SetRank(Ranks,Index(SmartTurret,TurretPierce),2);
    if(auto* P=FindFProperty<FUInt64Property>(ATemperateHillsWorld::StaticClass(),TEXT("SiegeExtraRanks")))
        P->SetPropertyValue_InContainer(Hills,Ranks.High);

    auto MakeGun=[&](const TCHAR* Def,int32 Enhance,int32 Place)
    {
        FColdSteelItem Item=Wallet->CreateItem(Def);
        Item.InstanceId=FString(Def)+TEXT("_audit");
        Item.Place=Place;
        if(Enhance>0)
        {
            TSharedPtr<FJsonObject> Data;
            if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data) && Data)
            {
                Data->SetNumberField(TEXT("enhanceLevel"),Enhance);
                Item.Data.Empty();
                FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
            }
        }
        return Item;
    };

    FColdSteelProfile Bag=Wallet->Snapshot();
    Bag.Items.Reset();
    Bag.Items.Add(MakeGun(TEXT("ue_m4a1"),7,0));
    Bag.Items.Add(MakeGun(TEXT("ue_m249"),4,0));
    Bag.Items.Add(MakeGun(TEXT("ue_saiga12k"),2,0));
    Bag.Items.Add(MakeGun(TEXT("ue_svd"),5,ColdSteelInventory::ColdSteelCompartment::Place));
    Bag.Items.Add(MakeGun(TEXT("ue_hk416"),3,0));
    Bag.Items.Add(MakeGun(TEXT("ue_m1911"),6,0)); // pistol must be filtered out
    Wallet->AdoptNetMirror(Bag,false);

    TSharedPtr<SSmartTurretDrawer> DrawerWidget;
    SAssignNew(DrawerWidget,SSmartTurretDrawer).Turret(Turret).Model(Wallet);
    if(!DrawerWidget.IsValid())return 5;

    auto Layer=SNew(SOverlay);
    TStrongObjectPtr<UTexture2D> Backdrop;
    FSlateBrush BackdropBrush;
    FString BackdropFile;
    if(FParse::Value(FCommandLine::Get(),TEXT("SiegeBackdrop="),BackdropFile))
    {
        Backdrop.Reset(FImageUtils::ImportFileAsTexture2D(BackdropFile));
        if(Backdrop.IsValid())
        {
            BackdropBrush.SetResourceObject(Backdrop.Get());
            BackdropBrush.SetImageSize(FVector2D(Backdrop->GetSizeX(),Backdrop->GetSizeY()));
            BackdropBrush.DrawAs=ESlateBrushDrawType::Image;
            Layer->AddSlot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&BackdropBrush)]];
        }
    }
    Layer->AddSlot()[SNew(SDPIScaler).DPIScale(1.f)[DrawerWidget.ToSharedRef()]];

    FWidgetRenderer Renderer(true,true);
    auto Capture=[&](const TCHAR* Name,int32 Width,int32 Height,int32 Frames=10)
    {
        View.Pixels=FIntPoint(Width,Height);
        FVector2D Size(Width,Height);
        TStrongObjectPtr<UTextureRenderTarget2D> Target(FWidgetRenderer::CreateTargetFor(Size,TF_Bilinear,false));
        if(!Target.IsValid())return false;
        for(int32 I=0;I<Frames;++I)
        {
            Renderer.DrawWidget(Target.Get(),Layer,Size,.04f);
            FTaskGraphInterface::Get().ProcessThreadUntilIdle(ENamedThreads::GameThread);
        }
        FlushRenderingCommands();
        TArray<FColor> Pixels;
        FReadSurfaceDataFlags Read(RCM_UNorm);Read.SetLinearToGamma(false);
        if(!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels,Read))return false;
        TArray64<uint8> Data;FImageUtils::PNGCompressImageArray(Width,Height,Pixels,Data);
        return FFileHelper::SaveArrayToFile(Data,*(Output/(FString(Name)+TEXT(".png"))));
    };

    if(!Capture(TEXT("01-empty-1440x900"),1440,900))return 6;

    // Simulate mounted M4A1 +7 (removed from backpack) + active mag + feedback banner.
    FColdSteelItem MountedM4=MakeGun(TEXT("ue_m4a1"),7,2);
    Bag.Items.RemoveAll([](const FColdSteelItem& E){return E.Definition==TEXT("ue_m4a1");});
    Wallet->AdoptNetMirror(Bag,false);
    Turret->MountedWeapon=MountedM4;
    const FSmartTurretWeaponStats M4Stats=Turret->GetCurrentWeaponStats();
    Turret->MaxAmmo=FMath::Max(1,M4Stats.ExpandedCapacity);
    Turret->CurrentAmmo=FMath::RoundToInt(Turret->MaxAmmo*0.72f);
    DrawerWidget->RefreshAll();
    DrawerWidget->SetFeedback(true,TEXT("已挂载「M4A1 卡宾枪」，智能索敌系统就绪。"));
    if(!Capture(TEXT("02-mounted-1440x900"),1440,900))return 7;
    if(!Capture(TEXT("03-compact-1024x576"),1024,576))return 8;

    UE_LOG(LogTemp,Display,TEXT("SMART_TURRET_UI_REVIEW passed desktop empty, mounted and compact captures"));
    return 0;
}
#endif
