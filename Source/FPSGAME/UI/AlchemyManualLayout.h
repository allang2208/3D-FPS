#pragma once
#include "CoreMinimal.h"
#include "Styling/SlateTypes.h"
#include "../Building/AlchemyTypes.h"

struct FAlchemyManualStepFragment
{
    int32 Step=0;
    FString Text;
    bool bContinuation=false,bParameters=true;
};
struct FAlchemyManualLeaf
{
    TArray<FAlchemyManualStepFragment> Steps;
    bool bOverview=false,bNotes=false,bFinish=false;
    float UsedHeight=0;
};
namespace AlchemyManualLayout
{
constexpr float PageWidth=1024,PageHeight=1536,ContentWidth=830,StepWidth=758;
constexpr float Top=82,Bottom=68,HeadingHeight=150,FooterHeight=62;
constexpr float BodyHeight=PageHeight-Top-Bottom-HeadingHeight-FooterHeight;
constexpr float ContentsHeading=142,ContentsRow=160;
constexpr int32 ContentsRows=4;
inline const FLinearColor Ink=FLinearColor::FromSRGBColor(FColor(49,40,33));
inline const FLinearColor Muted=FLinearColor::FromSRGBColor(FColor(101,88,70));
inline const FLinearColor Gold=FLinearColor::FromSRGBColor(FColor(119,83,38));
inline const FLinearColor Material=FLinearColor::FromSRGBColor(FColor(45,89,62));
inline const FLinearColor Heat=FLinearColor::FromSRGBColor(FColor(139,54,35));
inline const FLinearColor Time=FLinearColor::FromSRGBColor(FColor(37,77,112));
inline const FLinearColor Stir=FLinearColor::FromSRGBColor(FColor(88,57,112));
FSlateFontInfo Font(float Pixels,bool Strong=false);
FString Action(const FString& Name);
struct FParameter {FString Label,Value;FLinearColor Color;};
TArray<FParameter> Parameters(const FAlchemyRecipe& Recipe,const FAlchemyStep& Step);
const TArray<FAlchemyManualLeaf>& Leaves(const FAlchemyRecipe& Recipe);
}
