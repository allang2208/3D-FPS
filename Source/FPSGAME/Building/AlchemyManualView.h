#pragma once
#include "AlchemyTypes.h"

/** Reader-only print state; never a production recipe or save transaction. */
struct FAlchemyManualContentsEntry
{
    FName Recipe;
    FString Title;
    int32 FirstFolio=1,TargetSpread=0;
};
struct FAlchemyManualView
{
    FAlchemyRecipe Recipe;
    TArray<FAlchemyManualContentsEntry> Chapters;
    int32 Spread=0,FirstFolio=0,TotalFolios=0;
    bool bContents=false;
    bool SamePage(const FAlchemyManualView& Other) const
    {
        if(bContents!=Other.bContents||Spread!=Other.Spread||FirstFolio!=Other.FirstFolio||TotalFolios!=Other.TotalFolios||Recipe.Raw!=Other.Recipe.Raw)return false;
        if(bContents)
        {
            if(Chapters.Num()!=Other.Chapters.Num())return false;
            for(int32 I=0;I<Chapters.Num();++I)if(Chapters[I].Recipe!=Other.Chapters[I].Recipe||Chapters[I].Title!=Other.Chapters[I].Title||Chapters[I].FirstFolio!=Other.Chapters[I].FirstFolio||Chapters[I].TargetSpread!=Other.Chapters[I].TargetSpread)return false;
        }
        return true;
    }
};
