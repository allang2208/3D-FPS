#pragma once
#include "CoreMinimal.h"
#include "Components/ProgressBar.h"

// One presentation path for furnace and campfire. No inventory or fuel mutation.
namespace ColdSteelSmeltingPresentation
{
    inline FLinearColor SmeltingProgressColor(float T)
    {
        static const FLinearColor Stops[4]=
        {
            FLinearColor::FromSRGBColor(FColor(0xE5,0x41,0x3E)),   // #E5413E 红
            FLinearColor::FromSRGBColor(FColor(0xF1,0xC1,0x3F)),   // #F1C13F 黄
            FLinearColor::FromSRGBColor(FColor(0x41,0x8B,0xE7)),   // #418BE7 蓝
            FLinearColor::FromSRGBColor(FColor(0x3D,0xC4,0x5B))    // #3DC45B 绿
        };
        const float X=FMath::Clamp(T,0.f,1.f)*3.f;
        const int32 Step=FMath::Clamp(FMath::FloorToInt(X),0,2);
        const float A=X-Step;
        return Stops[Step]*(1.f-A)+Stops[Step+1]*A;   // 线性插值（sRGB 空间，与原项目 CSS 侧一致）
    }

    inline FLinearColor FuelFillColor(float Ratio)
    {
        const FLinearColor Low=FLinearColor::FromSRGBColor(FColor(0xF0,0xBE,0x71));
        const FLinearColor High=FLinearColor::FromSRGBColor(FColor(0xF1,0xC1,0x3F));
        const float X=FMath::Clamp(Ratio,0.f,1.f);
        return Low*(1.f-X)+High*X;
    }

    inline void RefreshProgressBars(UProgressBar* SmeltBar,UProgressBar* FuelBar,
        float SmeltRatio,float FuelRatio,bool bBurning,bool bFuelAlive)
    {
        SmeltBar->SetPercent(FMath::Clamp(SmeltRatio,0.f,1.f));
        FuelBar->SetPercent(FMath::Clamp(bFuelAlive?FuelRatio:0.f,0.f,1.f));
        FuelBar->SetFillColorAndOpacity(FuelFillColor(FuelRatio));
        if(!bBurning)SmeltBar->SetFillColorAndOpacity(SmeltingProgressColor(SmeltRatio));
    }
}
