#include "ColdSteelEnhancementWidget.h"
#include "Async/Async.h"
#include "Engine/Texture2D.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

void UColdSteelEnhancementWidget::LoadArcaneBackground()
{
    if(BackgroundTexture)return;
    const int32 Request=++BackgroundRequest;
    const TWeakObjectPtr<UColdSteelEnhancementWidget> Weak(this);
    const FString Filename=FPaths::ProjectContentDir()/TEXT("ColdSteelUI/ArcaneWorkbench/azure-forge-table-v2.png");
    Async(EAsyncExecution::ThreadPool,[Weak,Request,Filename]()
    {
        auto Image=MakeShared<FImage,ESPMode::ThreadSafe>();
        const bool Loaded=FImageUtils::LoadImage(*Filename,*Image);
        AsyncTask(ENamedThreads::GameThread,[Weak,Request,Image,Loaded]()
        {
            auto* Self=Weak.Get();if(!Self||Self->bClosing||Self->BackgroundRequest!=Request||!Loaded)return;
            if(auto* Texture=FImageUtils::CreateTexture2DFromImage(*Image))
            {
                Self->BackgroundTexture=Texture;
                Self->Background.SetResourceObject(Texture);
                Self->Background.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
                Self->Background.DrawAs=ESlateBrushDrawType::Image;
                if(auto Widget=Self->GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Layout|EInvalidateWidgetReason::Paint);
            }
        });
    });
}
