#include "ColdSteelGunAssemblyWidget.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetSwitcher.h"
#include "Styling/SlateTypes.h"

void UColdSteelGunAssemblyWidget::BuildManufacturingNavigation(UVerticalBox* Parent)
{
    ManufacturingNavigation=WidgetTree->ConstructWidget<UBorder>();
    ManufacturingNavigation->SetBrushColor(FLinearColor::Transparent);
    Parent->AddChildToVerticalBox(ManufacturingNavigation);
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();ManufacturingNavigation->SetContent(Row);
    auto AddCard=[&](const TCHAR* Title,const TCHAR* Description,USizeBox*& Size)
    {
        auto* Entry=WidgetTree->ConstructWidget<UButton>();Entry->SetIsEnabled(bInputReady);
        auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();Entry->SetContent(Content);
        auto* Label=Text(Title,16,false,true);Label->SetJustification(ETextJustify::Center);
        Space(Content->AddChildToVerticalBox(Label),FMargin(0,0,0,4));
        auto* Hint=Text(Description,12);Hint->SetJustification(ETextJustify::Center);Hint->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        Content->AddChildToVerticalBox(Hint);
        auto* ContentSlot=Cast<UButtonSlot>(Content->Slot);ContentSlot->SetHorizontalAlignment(HAlign_Fill);ContentSlot->SetVerticalAlignment(VAlign_Center);
        Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetContent(Entry);
        Row->AddChildToHorizontalBox(Size)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        return Entry;
    };
    USizeBox* AmmoSize=nullptr;AmmoPageButton=AddCard(TEXT("弹药制造"),TEXT("选择弹药 · 直接制作"),AmmoSize);AmmoPageSize=AmmoSize;
    USizeBox* GunSize=nullptr;GunPageButton=AddCard(TEXT("枪械制造"),TEXT("散件组装 · 制作新枪"),GunSize);GunPageSize=GunSize;
    AmmoPageButton->OnClicked.AddDynamic(this,&ThisClass::HandleAmmoPage);
    GunPageButton->OnClicked.AddDynamic(this,&ThisClass::HandleGunPage);
}

void UColdSteelGunAssemblyWidget::UpdateManufacturingNavigation()
{
    const float S=FMath::Max(.1f,Scale);
    ManufacturingNavigation->SetPadding(FMargin(12/S,12/S,12/S,0));
    AmmoPageSize->SetMinDesiredHeight(72/S);GunPageSize->SetMinDesiredHeight(72/S);
    Cast<UHorizontalBoxSlot>(AmmoPageSize->Slot)->SetPadding(FMargin(0,0,4/S,0));
    Cast<UHorizontalBoxSlot>(GunPageSize->Slot)->SetPadding(FMargin(4/S,0,0,0));
    for(UButton* Entry:{AmmoPageButton.Get(),GunPageButton.Get()})
    {
        const bool Selected=(Entry==AmmoPageButton.Get())==bAmmoPage;
        auto Style=ColdSteelUI::ButtonStyle(S);
        Style.SetNormal(ColdSteelUI::RoundedBrush(Selected?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,
            ColdSteelUI::CardRadius/S,Selected?ColdSteelUI::Accent:ColdSteelUI::Border,(Selected?2.f:1.f)/S));
        Style.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/S,ColdSteelUI::Accent,2/S));
        Style.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/S,ColdSteelUI::Accent,2/S));
        Style.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonDisabled,ColdSteelUI::CardRadius/S,ColdSteelUI::Border,1/S));
        Entry->SetStyle(Style);
        Cast<UButtonSlot>(Entry->GetContent()->Slot)->SetPadding(FMargin(12/S,10/S));
    }
}

void UColdSteelGunAssemblyWidget::SelectManufacturingPage(bool bAmmo)
{
    if(!bInputReady||bAmmoPage==bAmmo)return;
    bAmmoPage=bAmmo;
    // Switch presentation only: neither changing recipes nor consuming any materials.
    ManufacturingPages->SetActiveWidgetIndex(bAmmo?0:1);
    ManufacturingActions->SetActiveWidgetIndex(bAmmo?0:1);
    Scroll->ScrollToStart();UpdateManufacturingNavigation();
    (bAmmo?AmmoPageButton.Get():GunPageButton.Get())->SetKeyboardFocus();
    if(bAmmo)bAmmoDirty=true;
    else{bMaterialsDirty=true;LoadMold();}
    Refresh();
}

void UColdSteelGunAssemblyWidget::HandleAmmoPage(){SelectManufacturingPage(true);}
void UColdSteelGunAssemblyWidget::HandleGunPage(){SelectManufacturingPage(false);}
