#include "ColdSteelWeaponIcons.h"
#include "ColdSteelStaffIcon.h"
#include "../Weapons/Staff/StaffCatalog.h"

#include "Async/Async.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Math/Float16Color.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ProfilingDebugging/MiscTrace.h"
#include "RHIGPUReadback.h"
#include "RenderingThread.h"
#include "TextureResource.h"

struct FColdSteelIconReadback
{
    enum EState : int32 { Queued, WaitingGPU, Converting, Ready, Failed };
    TAtomic<int32> State{Queued};
    TAtomic<bool> PollQueued{false}, Cancelled{false};
    // Accessed and released only by render commands; workers only touch plain CPU data.
    TUniquePtr<FRHIGPUTextureReadback> Staging;
    FString Recipe, Error;
    int32 Width=0, Height=0, Visible=0;
    int32 SampleScale=1;
    float Exposure=1.f;
    double SubmittedSeconds=0.0, CopyMs=-1.0, ConversionMs=-1.0;
    TArray<FColor> Pixels;
};

void UColdSteelWeaponIcons::BeginReadback(const FString& Key)
{
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.ReadbackSubmit"),Key);
    auto Packet=MakeShared<FColdSteelIconReadback,ESPMode::ThreadSafe>();
    Packet->Recipe=Key;Packet->Width=Target->SizeX;Packet->Height=Target->SizeY;
    Packet->Exposure=!Queue.IsEmpty()&&Queue[0].Item.Definition==TEXT("ue_m249")?6.f:1.f;
    if(!Queue.IsEmpty()&&SupersampleBowIcon(Queue[0].Item))
    {
        Packet->SampleScale=2;
        Packet->Exposure=1.65f;
    }
    TRACE_BOOKMARK(TEXT("Icon.TargetReadback %s %dx%d recipe=%s"),*Target->GetPathName(),Packet->Width,Packet->Height,*Key);
    Packet->SubmittedSeconds=FPlatformTime::Seconds();
    PendingReadback=Packet;
    auto* Resource=Target->GameThread_GetRenderTargetResource();
    ENQUEUE_RENDER_COMMAND(ColdSteelIconReadbackCopy)([Packet,Resource](FRHICommandListImmediate& RHICmdList){
        if(Packet->Cancelled.Load())return;
        FRHITexture* Source=Resource?Resource->GetRenderTargetTexture().GetReference():nullptr;
        if(!Source||Source->GetDesc().Format!=PF_FloatRGBA||Source->GetDesc().Extent!=FIntPoint(Packet->Width,Packet->Height)){
            Packet->Error=TEXT("图标回读目标缺失或不是预期尺寸的 RGBA16f 纹理");
            Packet->State.Store(FColdSteelIconReadback::Failed);return;
        }
        Packet->Staging=MakeUnique<FRHIGPUTextureReadback>(TEXT("ColdSteelWeaponIcon"));
        RHICmdList.Transition(FRHITransitionInfo(Source,ERHIAccess::Unknown,ERHIAccess::CopySrc));
        Packet->Staging->EnqueueCopy(RHICmdList,Source);
        RHICmdList.Transition(FRHITransitionInfo(Source,ERHIAccess::CopySrc,ERHIAccess::SRVMask));
        Packet->State.Store(FColdSteelIconReadback::WaitingGPU);
    });
    SetWaitState(TEXT("GPUReadback"));
}

void UColdSteelWeaponIcons::CancelReadback()
{
    if(!PendingReadback)return;
    auto Packet=MoveTemp(PendingReadback);
    Packet->Cancelled.Store(true);
    // Ordered after previously submitted copy/poll commands; never block the game thread on teardown.
    ENQUEUE_RENDER_COMMAND(ColdSteelIconReleaseReadback)([Packet](FRHICommandListImmediate&){Packet->Staging.Reset();});
}

void UColdSteelWeaponIcons::ReadbackPerformanceState(FFPSIconTaskState& State) const
{
    if(!PendingReadback){State.ReadbackState=TEXT("idle");return;}
    const auto& Packet=*PendingReadback;
    const int32 Status=Packet.State.Load();
    const TCHAR* Names[]={TEXT("copy_queued"),TEXT("gpu_wait"),TEXT("pixel_conversion"),TEXT("ready_to_publish"),TEXT("failed")};
    State.ReadbackState=Names[Status];
    State.ReadbackAgeSeconds=FMath::Max(0.0,State.ObservedSeconds-Packet.SubmittedSeconds);
    // Release/acquire publication through State precedes reading these non-atomic result fields.
    if(Status==FColdSteelIconReadback::Converting||Status==FColdSteelIconReadback::Ready)State.ReadbackCopyMs=Packet.CopyMs;
    if(Status==FColdSteelIconReadback::Ready)State.ReadbackConversionMs=Packet.ConversionMs;
}

void UColdSteelWeaponIcons::PollReadback()
{
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.ReadbackPoll"));
    FailureStage=TEXT("Icon.Readback");
    const auto Packet=PendingReadback;
    if(!Packet){FailureReason=TEXT("图标回读任务不存在");FinishJob(false);return;}
    const int32 Status=Packet->State.Load();
    if(Status==FColdSteelIconReadback::Ready){
        if(Queue.IsEmpty()||Queue[0].Key!=Packet->Recipe){CancelReadback();return;}
        UFPSPerformanceMetricsSubsystem::RecordMarker(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.ReadbackReady"),
            FString::Printf(TEXT("%s copy_render_cpu_ms=%.3f conversion_worker_ms=%.3f elapsed_ms=%.3f"),
                *Packet->Recipe,Packet->CopyMs,Packet->ConversionMs,(FPlatformTime::Seconds()-Packet->SubmittedSeconds)*1000.0));
        SetWaitState(NAME_None);
        FinishJob(PublishReadback(Packet->Recipe,Packet->Pixels,Packet->Width/Packet->SampleScale,Packet->Height/Packet->SampleScale,Packet->Visible));
        return;
    }
    if(Status==FColdSteelIconReadback::Failed){FailureReason=Packet->Error;FinishJob(false);return;}
    if(FPlatformTime::Seconds()-Packet->SubmittedSeconds>=10.0){
        FailureReason=TEXT("异步图标回读或转换超过 10 秒，已取消本次任务");FinishJob(false);return;
    }
    SetWaitState(Status==FColdSteelIconReadback::Converting?TEXT("PixelConversion"):TEXT("GPUReadback"));
    if(Status!=FColdSteelIconReadback::WaitingGPU||Packet->PollQueued.Exchange(true))return;
    ENQUEUE_RENDER_COMMAND(ColdSteelIconPollReadback)([Packet](FRHICommandListImmediate&){
        if(Packet->Cancelled.Load()){Packet->Staging.Reset();return;}
        if(!Packet->Staging->IsReady()){Packet->PollQueued.Store(false);return;}
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_ReadbackCopyCPU);
        const double CopyStart=FPlatformTime::Seconds();
        int32 RowPitch=0,BufferHeight=0;
        const auto* Source=static_cast<const FFloat16Color*>(Packet->Staging->Lock(RowPitch,&BufferHeight));
        if(!Source||RowPitch<Packet->Width||BufferHeight<Packet->Height){
            if(Source)Packet->Staging->Unlock();
            Packet->Staging.Reset();
            Packet->Error=TEXT("图标 staging 数据不可用或行跨度/高度不足");
            Packet->State.Store(FColdSteelIconReadback::Failed);return;
        }
        TArray<FFloat16Color> Linear;Linear.SetNumUninitialized(Packet->Width*Packet->Height);
        for(int32 Y=0;Y<Packet->Height;++Y)
            FMemory::Memcpy(Linear.GetData()+Y*Packet->Width,Source+Y*RowPitch,Packet->Width*sizeof(FFloat16Color));
        Packet->Staging->Unlock();Packet->Staging.Reset();
        Packet->CopyMs=(FPlatformTime::Seconds()-CopyStart)*1000.0;
        Packet->State.Store(FColdSteelIconReadback::Converting);
        Async(EAsyncExecution::ThreadPool,[Packet,Linear=MoveTemp(Linear)](){
            if(Packet->Cancelled.Load())return;
            TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_ConvertPixels);
            const double Begin=FPlatformTime::Seconds();
            const int32 Width=Packet->Width/Packet->SampleScale,Height=Packet->Height/Packet->SampleScale;
            TArray<FColor> Pixels;Pixels.SetNumUninitialized(Width*Height);int32 Visible=0;
            auto Store=[&](int32 Index,FLinearColor P,float Alpha){
                if(Alpha>.1f)++Visible;
                const float Gain=Packet->Exposure/(1.f+(Packet->Exposure-1.f)*FMath::Max3(P.R,P.G,P.B));
                P.R*=Gain;P.G*=Gain;P.B*=Gain;
                auto Color=P.ToFColorSRGB();Color.A=FMath::RoundToInt(Alpha*255);Pixels[Index]=Color;
            };
            if(Packet->SampleScale==2)
            {
                // Preserve subpixel cable coverage in the transparent PNG and the live Slate texture.
                for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)
                {
                    const int32 TopLeft=2*Y*Packet->Width+2*X;
                    FLinearColor Weighted(0,0,0,0);float Coverage=0.f;
                    for(const int32 Offset:{0,1,Packet->Width,Packet->Width+1})
                    {
                        const FLinearColor Sample=Linear[TopLeft+Offset].GetFloats();
                        const float Alpha=FMath::Clamp(1.f-Sample.A,0.f,1.f);
                        Coverage+=Alpha;Weighted+=Sample*Alpha;
                    }
                    if(Coverage>0.f)Weighted*=1.f/Coverage;
                    Store(Y*Width+X,Weighted,Coverage*.25f);
                }
            }
            else
            {
                for(int32 Index=0;Index<Linear.Num();++Index)
                {
                    const FLinearColor Sample=Linear[Index].GetFloats();
                    Store(Index,Sample,FMath::Clamp(1.f-Sample.A,0.f,1.f));
                }
            }
            Packet->Pixels=MoveTemp(Pixels);Packet->Visible=Visible;
            Packet->ConversionMs=(FPlatformTime::Seconds()-Begin)*1000.0;
            Packet->State.Store(FColdSteelIconReadback::Ready);
        });
    });
}

bool UColdSteelWeaponIcons::PublishReadback(const FString& K,const TArray<FColor>& Pixels,int32 Width,int32 Height,int32 Visible)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_PublishTexture);
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.PublishTexture"),K);
    if(Visible<100){FailureReason=FString::Printf(TEXT("捕获图像有效像素不足：%d < 100"),Visible);return false;}
    auto* Texture=UTexture2D::CreateTransient(Width,Height,PF_B8G8R8A8);
    if(!Texture){FailureReason=TEXT("无法创建图标纹理");return false;}
    Texture->SRGB=true;Texture->NeverStream=true;Texture->Filter=TF_Bilinear;
    auto& Mip=Texture->GetPlatformData()->Mips[0];void* Data=Mip.BulkData.Lock(LOCK_READ_WRITE);
    FMemory::Memcpy(Data,Pixels.GetData(),Pixels.Num()*sizeof(FColor));Mip.BulkData.Unlock();Texture->UpdateResource();
    if(Cache.Num()>=64){FString Old;uint64 Use=MAX_uint64;for(const auto& Pair:Cache)if(Pair.Value.Use<Use){Use=Pair.Value.Use;Old=Pair.Key;}Cache.Remove(Old);Textures.Remove(Old);}
    Textures.Add(K,Texture);auto& E=Cache.Add(K);E.Use=++Serial;E.Brush.SetResourceObject(Texture);E.Brush.ImageSize=FVector2D(Width,Height);E.Brush.DrawAs=ESlateBrushDrawType::Image;
    // The live brush uses the same silhouette framing as its catalog fallback.
    if(!Queue.IsEmpty()&&(ColdSteelStaff::IsStaff(Queue[0].Item)||
        ColdSteelInventory::IsOneHandedMelee(Queue[0].Item)||Queue[0].Item.Definition==TEXT("ue_m870")))
        ColdSteelStaffIcon::FrameVisiblePixels(E.Brush,Pixels.GetData(),Width,Height);
    ++Completed;UE_LOG(LogTemp,Display,TEXT("WeaponIcon: ready key=%s visible=%d renders=%d"),*K,Visible,Completed);return true;
}
