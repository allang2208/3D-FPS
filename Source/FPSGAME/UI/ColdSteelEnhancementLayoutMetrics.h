#pragma once
#include "CoreMinimal.h"

/** Physical-pixel geometry shared by the world camera and the Slate panel.
 * Inventory keeps its ordinary drawer size. Compact view stacks controls below
 * the scene instead of shrinking the bag, text or the complete canvas.
 */
struct FColdSteelEnhancementLayoutMetrics
{
    FVector2D PanelPosition,PanelSize,ScenePosition,SceneSize;
    bool bStacked=false;
    static FColdSteelEnhancementLayoutMetrics ForViewport(FVector2D Viewport)
    {
        const float W=FMath::Max(1.f,float(Viewport.X)),H=FMath::Max(1.f,float(Viewport.Y));
        const float Bag=FMath::Min(W-12.f,FMath::Clamp(W*.48f,720.f,1040.f));
        const float Available=FMath::Max(1.f,W-Bag-36.f);
        FColdSteelEnhancementLayoutMetrics Out;
        Out.bStacked=Available<772.f||H<650.f;
        const float PanelWidth=FMath::Min(440.f,Available);
        const float PanelHeight=Out.bStacked?FMath::Min(H-24.f,FMath::Max(300.f,H*.56f)):H-24.f;
        Out.PanelPosition=FVector2D(12.f,Out.bStacked?H-12.f-PanelHeight:12.f);
        Out.PanelSize=FVector2D(PanelWidth,FMath::Max(1.f,PanelHeight));
        Out.ScenePosition=Out.bStacked?FVector2D(12.f,12.f):FVector2D(24.f+PanelWidth,12.f);
        Out.SceneSize=Out.bStacked?FVector2D(Available,FMath::Max(1.f,Out.PanelPosition.Y-24.f))
            :FVector2D(FMath::Max(1.f,Available-PanelWidth-12.f),H-24.f);
        return Out;
    }
};
