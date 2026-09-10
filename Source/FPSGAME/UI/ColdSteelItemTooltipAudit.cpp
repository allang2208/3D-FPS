#include "ColdSteelHUDWidget.h"
#include "ColdSteelItemTooltip.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelWarehouseChest.h"
#include "EngineUtils.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/SizeBox.h"
#include "Components/Button.h"
#include "Components/HorizontalBox.h"
#include "Blueprint/WidgetTree.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
using namespace ColdSteelInventory;

void UColdSteelHUDWidget::RunItemTooltipAudit()
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* GS=GetGameInstance()->GetSubsystem<UGunsmithSystem>();if(!M||!M->IsAudit())return;
    struct FRun{int32 Checks=0,Failures=0,Phase=0;FString Gun,Potion;int64 Generation=0;FTimerHandle Timer;};auto R=MakeShared<FRun>();
    auto Check=[R](bool Pass,const TCHAR* Name){++R->Checks;if(!Pass)++R->Failures;UE_LOG(LogTemp,Display,TEXT("ItemTooltip: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto Gun=M->CreateItem(TEXT("ue_m4a1"));TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
    Check(Data.IsValid(),TEXT("catalog supplies native firearm fixture"));
    if(!Data){UE_LOG(LogTemp,Display,TEXT("ItemTooltip: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("audit"),TEXT("fixture"));
    // Isolated presentation fixture, not an applied gameplay modification.
    auto CraftEffects=MakeShared<FJsonObject>();CraftEffects->SetNumberField(TEXT("damagePercent"),.1);CraftEffects->SetNumberField(TEXT("reloadTimeDelta"),250);Data->SetObjectField(TEXT("_craftEffects"),CraftEffects);
    Data->SetObjectField(TEXT("_craftData"),Parts);Data->SetNumberField(TEXT("enhanceLevel"),10);Data->SetStringField(TEXT("rarity"),TEXT("legendary"));
    auto Enchant=MakeShared<FJsonObject>(),Prefix=MakeShared<FJsonObject>();Prefix->SetStringField(TEXT("name"),TEXT("锋利"));Enchant->SetObjectField(TEXT("prefix"),Prefix);Data->SetObjectField(TEXT("_enchantData"),Enchant);
    auto Effects=MakeShared<FJsonObject>();Effects->SetNumberField(TEXT("damagePercent"),.1);Effects->SetBoolField(TEXT("poisonOnHit"),true);Data->SetObjectField(TEXT("_enchantEffects"),Effects);
    FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Gun.Data));
    auto Potion=M->CreateItem(TEXT("hp_potion"),3);auto P=M->Snapshot();P.Items.Empty();P.Hotbar.Init(TEXT(""),4);P.HotbarDefinitions.Init(TEXT(""),4);Insert(P.Items,Gun);Insert(P.Items,Potion);
    Check(M->CommitState(P),TEXT("isolated profile owns tooltip fixtures"));R->Gun=Gun.InstanceId;R->Potion=Potion.InstanceId;
    const auto A=BuildColdSteelItemTooltip(Gun,M,GS),B=BuildColdSteelItemTooltip(Potion,M,GS);
    Check(A.Cards.Num()==3&&A.Cards[0].Title==TEXT("附魔效果")&&A.Cards[1].Title==TEXT("改造项目"),TEXT("enchant craft main order with isolated processing fixture"));
    Check(B.Cards.Num()==1&&B.Enhancement.IsEmpty(),TEXT("plain potion hides processing cards and enhancement badge"));
    bool Healing=false;for(const auto& Row:B.Cards.Last().Rows)if(Row.Label==TEXT("恢复生命")&&Row.Value==TEXT("+30"))Healing=true;
    Check(Healing,TEXT("consumable value comes from item effect"));
    const int32 CapacityExpected=GetDefault<AFPSGAMECharacter>()->GetMagazineCapacity();bool Capacity=false;for(const auto& Row:A.Cards.Last().Rows)if(Row.Label==TEXT("子弹数")&&Row.Value.Contains(FString::Printf(TEXT("/ %d"),CapacityExpected)))Capacity=true;
    Check(Capacity,TEXT("native gun capacity uses runtime defaults"));
    SetInventoryTab(false);SetInventoryOpen(true);
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,M,R,Check]()
    {
        const auto View=UWidgetLayoutLibrary::GetViewportSize(this);const FString Out=FPaths::ProjectSavedDir()/TEXT("ItemTooltip");
        auto Capture=[&](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("ue-%s-%dx%d.png"),Name,int32(View.X),int32(View.Y)),true,false);};
        const auto& RootG=WidgetTree->RootWidget->GetCachedGeometry();auto Screen=[&](FVector2D UV){return RootG.LocalToAbsolute(RootG.GetLocalSize()*UV);};
        switch(R->Phase++){
        case 0:{auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0));const auto G=Board->GetCachedGeometry();const auto L=Board->Layout(G);const auto* I=M->FindItem(R->Potion);FVector2D Pt=G.LocalToAbsolute(FVector2D(14+I->Cell%18*L.Cell,L.BagY+2+I->Cell/18*L.Cell)/Board->Scale);FPointerEvent E(0,Pt,Pt-FVector2D(1,0),TSet<FKey>(),EKeys::Invalid,0,FModifierKeysState());R->Generation=M->Snapshot().Generation;Board->NativeOnMouseMove(G,E);Check(ItemTooltip&&ItemTooltip->IsVisible()&&ItemTooltip->ItemId()==R->Potion,TEXT("native backpack hover opens shared tooltip"));break;}
        case 1:Check(M->Snapshot().Generation==R->Generation,TEXT("hover is read only"));Capture(TEXT("potion"));break;
        case 2:ShowItemTooltip(R->Gun,Screen(FVector2D(.97,.93)),true,this);break;
        case 3:{Check(ItemTooltip->Content().Cards.Num()==3,TEXT("three independent processing cards rendered"));const FVector2D Size=ItemTooltip->Extent()*ItemTooltip->Scale;Check(Size.X<=View.X-20&&Size.Y<=View.Y-20,TEXT("tooltip fits viewport"));Check(ItemTooltip->HasHorizontalOverflow()==(ItemTooltip->Cards->GetDesiredSize().X*ItemTooltip->Scale>View.X-24),TEXT("horizontal scrolling follows actual natural content width"));bool Wrap=false;TArray<UWidget*> Widgets;ItemTooltip->WidgetTree->GetAllWidgets(Widgets);for(auto* W:Widgets)if(auto* T=Cast<UTextBlock>(W))Wrap|=T->GetAutoWrapText();Check(!Wrap,TEXT("all tooltip labels keep source no wrap rule"));Check(ItemTooltip->Close->GetCachedGeometry().GetLocalSize().X>0,TEXT("fixed close button has live geometry"));Capture(TEXT("gun-main"));break;}
        case 4:ItemTooltip->ScrollToSideCards();break;
        case 5:Capture(TEXT("processing"));ShowItemTooltip(R->Potion,Screen(FVector2D(.1,.1)),false,this);Check(ItemTooltip->ItemId()==R->Gun,TEXT("pinned item survives hovering another item"));break;
        case 6:HideItemTooltip(true);ShowItemTooltip(R->Potion,Screen(FVector2D(.02,.02)),false,this);break;
        case 7:Check(ItemTooltip->Content().Cards.Num()==1&&ItemTooltip->Extent().X*ItemTooltip->Scale<View.X,TEXT("switching to plain item shrinks and clears processing"));Capture(TEXT("edge"));break;
        case 8:HideItemTooltip(true);ShowItemTooltip(R->Gun,Screen(FVector2D(.8,.3)),true,this);FocusItemTooltip();break;
        case 9:{FKeyEvent E(EKeys::Escape,FModifierKeysState(),0,false,0,0);NativeOnPreviewKeyDown(GetCachedGeometry(),E);Check(!HasPinnedItemTooltip()&&IsInventoryOpen(),TEXT("Escape dismisses pinned detail before inventory"));Check(M->TransferWarehouse(R->Gun,4,0),TEXT("warehouse tooltip fixture transfer"));for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It){OpenWarehouse(*It);break;}break;}
        case 10:{auto* Cell=WarehouseWidget->Cells[0].Get();const auto G=Cell->GetCachedGeometry();const FVector2D Pt=G.LocalToAbsolute(G.GetLocalSize()*.5);FPointerEvent E(0,Pt,Pt-FVector2D(1,0),TSet<FKey>(),EKeys::Invalid,0,FModifierKeysState());Cell->NativeOnMouseEnter(G,E);Check(ItemTooltip&&ItemTooltip->IsVisible()&&ItemTooltip->ItemId()==R->Gun,TEXT("native warehouse hover uses same item inspector"));break;}
        case 11:Capture(TEXT("warehouse"));break;
        case 12:CloseWarehouse();Check(!ItemTooltip->IsVisible(),TEXT("closing warehouse clears inspection"));ShowItemTooltip(R->Potion,Screen(FVector2D(.8,.3)),false,this);SetInventoryOpen(false);Check(!ItemTooltip->IsVisible(),TEXT("closing panel removes tooltip"));{
            GetWorld()->GetTimerManager().ClearTimer(R->Timer);UE_LOG(LogTemp,Display,TEXT("ItemTooltip: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));break;}
        }
    }),.6f,true);
}
