#include "ColdSteelAmmoReadout.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMECharacter.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SizeBox.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UColdSteelAmmoReadout::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(false);SetVisibility(ESlateVisibility::HitTestInvisible);
    bPreview=FParse::Param(FCommandLine::Get(),TEXT("AmmoReadoutAudit"));
    const float S=ColdSteelUI::PixelScale(this);
    auto Text=[&](float Pixels,bool Numeric=false,bool Bold=false){auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetFont(Numeric?ColdSteelUI::NumberFont(Pixels*.75f/S,Bold):ColdSteelUI::TextFont(Pixels*.75f/S));T->SetColorAndOpacity(ColdSteelUI::TextSecondary);return T;};
    auto* Surface=WidgetTree->ConstructWidget<UBorder>();WidgetTree->RootWidget=Surface;
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,6/S));Surface->SetPadding(FMargin(8/S,4/S));
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();Surface->SetContent(Row);
    auto* IdentityWidth=WidgetTree->ConstructWidget<USizeBox>();IdentityWidth->SetWidthOverride(54/S);
    auto* IdentitySlot=Row->AddChildToHorizontalBox(IdentityWidth);IdentitySlot->SetVerticalAlignment(VAlign_Center);IdentitySlot->SetPadding(FMargin(0,0,8/S,0));
    auto* Identity=WidgetTree->ConstructWidget<UVerticalBox>();IdentityWidth->SetContent(Identity);
    Weapon=Text(12);Weapon->SetColorAndOpacity(ColdSteelUI::TextPrimary);Weapon->SetClipping(EWidgetClipping::ClipToBounds);Weapon->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);Weapon->SetAutoWrapText(false);Identity->AddChildToVerticalBox(Weapon);
    Calibre=Text(10);Calibre->SetAutoWrapText(false);Identity->AddChildToVerticalBox(Calibre);
    auto* Numbers=WidgetTree->ConstructWidget<UHorizontalBox>();auto* NumberSlot=Row->AddChildToHorizontalBox(Numbers);NumberSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));NumberSlot->SetHorizontalAlignment(HAlign_Right);NumberSlot->SetVerticalAlignment(VAlign_Center);
    Current=Text(22,true,true);Current->SetMinDesiredWidth(28/S);Current->SetAutoWrapText(false);Numbers->AddChildToHorizontalBox(Current)->SetVerticalAlignment(VAlign_Center);
    auto* Divider=Text(12,true);Divider->SetText(FText::FromString(TEXT("/")));auto* DividerSlot=Numbers->AddChildToHorizontalBox(Divider);DividerSlot->SetVerticalAlignment(VAlign_Center);DividerSlot->SetPadding(FMargin(4/S,0,6/S,0));
    auto* ReserveColumn=WidgetTree->ConstructWidget<UVerticalBox>();Numbers->AddChildToHorizontalBox(ReserveColumn)->SetVerticalAlignment(VAlign_Center);
    auto* Label=Text(10);Label->SetText(FText::FromString(TEXT("备弹")));Label->SetJustification(ETextJustify::Right);ReserveColumn->AddChildToVerticalBox(Label);
    Spare=Text(14,true);Spare->SetAutoWrapText(false);Spare->SetJustification(ETextJustify::Right);ReserveColumn->AddChildToVerticalBox(Spare);
    Present(TEXT("未装备武器"),TEXT(""),0,0,0,false,false);
}

void UColdSteelAmmoReadout::Present(const FString& Name,const FString& Ammo,int32 Magazine,int32 Reserve,int32 Capacity,bool Reloading,bool Equipped)
{
    const int32 M=FMath::Max(0,Magazine),R=FMath::Max(0,Reserve),C=FMath::Max(1,Capacity);
    const bool Low=M>0&&M<=FMath::Max(1,FMath::CeilToInt(C*.2f));
    const FLinearColor Color=!Equipped?ColdSteelUI::TextTertiary:Reloading?ColdSteelUI::Accent:M==0?ColdSteelUI::Danger:Low?ColdSteelUI::Warning:ColdSteelUI::TextPrimary;
    Weapon->SetText(FText::FromString(Equipped?Name:TEXT("未装备武器")));Calibre->SetText(FText::FromString(Equipped?Ammo:TEXT("")));
    // Never abbreviate reserves: displayed values remain exact, including large stacks.
    Current->SetText(FText::FromString(Equipped?FString::Printf(TEXT("%02d"),M):TEXT("--")));Current->SetColorAndOpacity(Color);
    Spare->SetText(FText::FromString(Equipped?FString::FromInt(R):TEXT("--")));Spare->SetColorAndOpacity(Equipped&&R==0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

void UColdSteelAmmoReadout::Refresh(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model,bool MenuOpen)
{
    if(!Current)return;SetVisibility(MenuOpen?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    if(auto* CanvasSlot=Cast<UCanvasPanelSlot>(Slot)){
        const float S=ColdSteelUI::PixelScale(this);
        CanvasSlot->SetPosition(FVector2D(-20/S,-20/S));
        CanvasSlot->SetSize(FVector2D(184/S,38/S));
    }
    const auto* Item=Model?Model->Equipped():nullptr;
    FString AmmoName;
    if(Model){const FString Definition=Model->AmmoDefinition();AmmoName=Definition==TEXT("ammo_556")?TEXT("5.56 mm"):Definition==TEXT("ammo_762")?TEXT("7.62 mm"):TEXT("");}
    Present(Item?ColdSteelInventory::Text(*Item,TEXT("name")):TEXT(""),AmmoName,Character?Character->GetMagazineAmmo():0,Character?Character->GetReserveAmmo():0,Character?Character->GetMagazineCapacity():0,Character&&Character->IsReloading(),Character&&Character->HasInventoryWeapon()&&Item);
    if(Character && Item && Character->HasInventoryWeapon() && Character->HasInfiniteReserveAmmo())
    {
        Spare->SetText(FText::FromString(TEXT("∞")));
        Spare->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    }
    if(bPreview&&Model&&Model->IsAudit())Preview(Character,Model);
}
