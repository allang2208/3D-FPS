#pragma once

#include "CoreMinimal.h"
#include "ColdSteelUIStyle.h"
#include "Components/TextBlock.h"

// Shared presentation only; each workbench supplies its authoritative result.
namespace ColdSteelCraftingResultStyle
{
inline void SetBonus(UTextBlock* Widget,const TCHAR* Label,double Bonus)
{
    if(!Widget)return;
    // Match the color to the displayed precision, including rounded negative zero.
    const int32 Hundredths=FMath::RoundToInt(Bonus*10000.);
    const FString Value=Hundredths==0?TEXT("0.00%"):FString::Printf(TEXT("%+.2f%%"),Hundredths/100.);
    const FString Caption=FString::Printf(TEXT("%s %s"),Label,*Value);
    if(Widget->GetText().ToString()!=Caption)Widget->SetText(FText::FromString(Caption));
    Widget->SetColorAndOpacity(Hundredths>0?ColdSteelUI::Success:Hundredths<0?ColdSteelUI::Danger:ColdSteelUI::TextTertiary);
}

inline FLinearColor ScoreColor(float Score)
{
    return FLinearColor::LerpUsingHSV(ColdSteelUI::Danger,ColdSteelUI::Success,FMath::Clamp(Score/100.f,0.f,1.f));
}
}
