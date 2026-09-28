#include "ColdSteelGunRecipeOptionWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/TextBlock.h"

void UColdSteelGunRecipeOptionWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    OptionBox=WidgetTree->ConstructWidget<USizeBox>();
    WidgetTree->RootWidget=OptionBox;
    Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetAutoWrapText(true);
    Label->SetJustification(ETextJustify::Center);
    Label->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    OptionBox->SetContent(Label);
    Cast<USizeBoxSlot>(Label->Slot)->SetVerticalAlignment(VAlign_Center);
}

void UColdSteelGunRecipeOptionWidget::Configure(const FString& Option,float PixelScale)
{
    Label->SetText(FText::FromString(Option));
    SetPixelScale(PixelScale);
}

void UColdSteelGunRecipeOptionWidget::SetPixelScale(float PixelScale)
{
    const float S=FMath::Max(.1f,PixelScale);
    Label->SetFont(GunsmithUI::TextFont(14/S,true));
    OptionBox->SetMinDesiredHeight(ColdSteelUI::ActionHeight/S);
}
