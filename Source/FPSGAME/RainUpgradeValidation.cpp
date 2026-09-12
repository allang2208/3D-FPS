#include "RainUpgradeValidation.h"
#include "FPSWeatherManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DecalComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMemory.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "DynamicRHI.h"
#include "RenderTimer.h"
#include "WeatherSurfaceComponent.h"
#include "Components/BoxComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstanceController.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraSimCache.h"
#include "NiagaraSimCacheFunctionLibrary.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
struct FRainSurfaceAudit
{
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    FTimerHandle Timer;
    int32 Step=0,Failures=0,MaxTraces=0;
    float DryStartWetness=0;
    TMap<FName,FVector> Positions;
    TWeakObjectPtr<AActor> Roof;
    FVector RoofCenter;
    void Check(bool Pass,const TCHAR* Name)
    {
        Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("RAIN_CONTRACT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);
    }
    void Quality(int32 Value){IConsoleManager::Get().FindConsoleVariable(TEXT("fps.RainQuality"))->Set(Value,ECVF_SetByCode);}
    void Tick()
    {
        if(!Weather.IsValid())return;
        ++Step;
        UWorld* W=Weather->GetWorld();
        auto* Surface=Weather->FindComponentByClass<UWeatherSurfaceComponent>();
        MaxTraces=FMath::Max(MaxTraces,Surface->GetTraceCount());
        TInlineComponentArray<UDecalComponent*> Decals(Weather.Get());
        TInlineComponentArray<UNiagaraComponent*> Particles(Weather.Get());
        int32 Visible=0;UNiagaraComponent* Rain=nullptr;
        for(auto* D:Decals)Visible+=D->IsVisible();
        for(auto* FX:Particles)if(FX->GetFName()==TEXT("CameraRain"))Rain=FX;
        auto* PC=UGameplayStatics::GetPlayerController(W,0);
        auto* Pawn=UGameplayStatics::GetPlayerPawn(W,0);
        bool Valid=false;
        if(Step==1)
        {
            Quality(2);Weather->TransitionSeconds=1;Weather->SetWeatherState(EFPSWeatherState::Rain);
            if(Pawn)Pawn->SetCanBeDamaged(false);
        }
        if(Step==8)
        {
            Check(Surface->GetPatchCount()==16&&Particles.Num()==22,TEXT("fixed pool: 16 surfaces, 22 particle components"));
            Check(Visible>0&&Visible<=16&&Surface->GetWetness()>.1f,TEXT("balanced wet surfaces accumulate"));
            Check(Rain&&Rain->GetAsset()==Weather->RainSystem&&Weather->SplashSystem,TEXT("configured rain assets active"));
            for(auto* D:Decals)if(D->IsVisible())Positions.Add(D->GetFName(),D->GetComponentLocation());
            if(Pawn)Pawn->AddActorWorldOffset(FVector(30,0,0),true);
        }
        if(Step==10)
        {
            int32 Shared=0;bool Stable=true;
            for(auto* D:Decals)if(D->IsVisible())if(const FVector* P=Positions.Find(D->GetFName())){++Shared;Stable&=P->Equals(D->GetComponentLocation(),1);}
            Check(Shared>0&&Stable,TEXT("wet patches do not follow camera motion"));Quality(0);
        }
        if(Step==12)
        {
            bool Zero=true;for(auto* FX:Particles)Zero&=FX->GetVariableFloat(TEXT("User.SpawnRate"),Valid)<.1f;
            Check(Zero&&Visible==0,TEXT("quality zero stops all emissions and decals"));Quality(1);
        }
        if(Step==15)
        {
            Check(Visible>0&&Visible<=4,TEXT("low quality capped at four surface patches"));
            Check(Rain&&FMath::IsNearlyEqual(Rain->GetVariableFloat(TEXT("User.SpawnRate"),Valid),.68f*800,2.f),TEXT("low rain spawn budget"));
            Weather->SetWeatherState(EFPSWeatherState::Clear);DryStartWetness=Surface->GetWetness();
        }
        if(Step==19)
        {
            Check(Surface->GetWetness()>0&&Surface->GetWetness()<DryStartWetness,TEXT("dry weather gradually dries existing wet surfaces"));
            bool Zero=true;for(auto* FX:Particles)Zero&=FX->GetVariableFloat(TEXT("User.SpawnRate"),Valid)<.1f;
            Check(Zero,TEXT("clear weather stops all rain layers"));Quality(3);Weather->SetWeatherState(EFPSWeatherState::Storm);
        }
        if(Step==24)
        {
            Check(Visible>0&&Visible<=16&&Particles.Num()==22,TEXT("high quality reuses bounded pool"));
            RoofCenter=UGameplayStatics::GetPlayerCameraManager(W,0)->GetCameraLocation()+FVector(0,0,500);
            AActor* A=W->SpawnActor<AActor>();Roof=A;
            auto* Box=NewObject<UBoxComponent>(A);A->SetRootComponent(Box);Box->SetBoxExtent(FVector(360,360,15));
            Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();A->SetActorLocation(RoofCenter);
        }
        if(Step==34)
        {
            Check(Rain&&Rain->GetVariableFloat(TEXT("User.SpawnRate"),Valid)<.1f,TEXT("roof blocks camera rain"));
            bool Exposed=true;int32 RoofHits=0;
            for(auto* D:Decals)if(D->IsVisible())
            {
                const FVector P=D->GetComponentLocation();
                if(FMath::Abs(P.X-RoofCenter.X)<350&&FMath::Abs(P.Y-RoofCenter.Y)<350){++RoofHits;Exposed&=P.Z>=RoofCenter.Z;}
            }
            Check(RoofHits>0&&Exposed,TEXT("new roof receives surface effects instead of indoor floor"));
            int32 Drips=0;for(auto* FX:Particles)if(FX->GetName().StartsWith(TEXT("RainRoofDrip"))&&FX->IsActive()&&FX->GetVariableFloat(TEXT("User.SpawnRate"),Valid)>.1f)++Drips;
            Check(Drips>0&&Drips<=4,TEXT("exposed eaves emit bounded roof drips"));
            if(Roof.IsValid())Roof->Destroy();
        }
        if(Step==21&&Pawn)
        {
            // The nearby melee fixture can block a swept move; use deterministic ground displacement.
            const FVector Before=Pawn->GetActorLocation();
            UDecalComponent* Nearest=nullptr;
            for(auto* D:Decals)if(D->IsVisible()&&(!Nearest||FVector::DistSquared2D(Before,D->GetComponentLocation())<FVector::DistSquared2D(Before,Nearest->GetComponentLocation())))Nearest=D;
            FVector Destination=Before+FVector(180,0,0);
            if(Nearest)
            {
                const FVector Contact=Nearest->GetComponentLocation();
                FVector Direction=(Contact-Before).GetSafeNormal2D();
                if(Direction.IsNearlyZero())Direction=FVector::ForwardVector;
                Destination=Contact+Direction*180;
                Destination.Z=Contact.Z+Pawn->GetSimpleCollisionHalfHeight()+4;
            }
            Pawn->SetActorLocation(Destination,false,nullptr,ETeleportType::TeleportPhysics);
            UE_LOG(LogTemp,Display,TEXT("RAIN_FOOTSTEP_FIXTURE moved=%.1f wet=%.3f"),FVector::Dist2D(Before,Pawn->GetActorLocation()),Surface->GetWetness());
        }
        if(Step==23)
        {
            bool Ripple=false;
            for(auto* D:Decals)if(auto* M=Cast<UMaterialInstanceDynamic>(D->GetDecalMaterial()))Ripple|=M->K2_GetScalarParameterValue(TEXT("StepTime"))>0;
            Check(Ripple,TEXT("high-quality ground movement triggers analytic footstep ripple"));
        }
        if(Step==38)
        {
            Check(Rain&&Rain->GetVariableFloat(TEXT("User.SpawnRate"),Valid)>1900,TEXT("rain resumes after roof removed"));
            Check(MaxTraces<=8,TEXT("bounded surface ray budget"));
            UE_LOG(LogTemp,Display,TEXT("RAIN_SURFACE_AUDIT_%s map=%s failures=%d max_traces=%d"),Failures?TEXT("FAIL"):TEXT("PASS"),*UGameplayStatics::GetCurrentLevelName(W,true),Failures,MaxTraces);
            W->GetTimerManager().ClearTimer(Timer);if(PC)PC->ConsoleCommand(TEXT("quit"));
        }
    }
};
struct FRainAudit : TSharedFromThis<FRainAudit>
{
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    FTimerHandle Timer;
    int32 Step = 0;
    FString Label;
    FString Rows = TEXT("sample,frame_ms,gpu_ms,game_ms,render_ms,resident_mb,rain\n");
    TArray<double> GPU, Frame;
    int32 VisibilityFailures=0,MaxVisibilityTraces=0;
    TWeakObjectPtr<AActor> VisibilityRoof;
    void CheckVisibility(bool Pass,const TCHAR* Name)
    {
        VisibilityFailures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("RAIN_VISIBILITY_CHECK %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);
    }
    void Tick()
    {
        if (!Weather.IsValid()) return;
        UWorld* World = Weather->GetWorld();
        ++Step;
        const bool Quick=FParse::Param(FCommandLine::Get(),TEXT("RainQuick"));
        const bool Visibility=FParse::Param(FCommandLine::Get(),TEXT("RainVisibilityAudit"));
        const int32 EndStep=Visibility?208:Quick?64:160;
        if(Visibility)MaxVisibilityTraces=FMath::Max(MaxVisibilityTraces,Weather->FindComponentByClass<UWeatherSurfaceComponent>()->GetTraceCount());
        if (Step == 1)
        {
            Weather->TransitionSeconds = 1;
            Weather->SetWeatherState(EFPSWeatherState::Rain);
            if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0)) Pawn->SetCanBeDamaged(false);
            if (APlayerController* PC = UGameplayStatics::GetPlayerController(World,0))
            {
                PC->SetIgnoreMoveInput(true);
                PC->SetIgnoreLookInput(true);
                PC->SetControlRotation(FRotator(-17, -30, 0));
                PC->ConsoleCommand(TEXT("t.MaxFPS 0"));
            }
        }
        if(Step==32)
        {
            uint64 Bytes=0;
            for(UNiagaraComponent* FX:TInlineComponentArray<UNiagaraComponent*>(Weather.Get()))
            {
                Bytes+=FX->GetApproxMemoryUsage();
                if((Quick||Visibility)&&FX->GetFName()==TEXT("CameraRain"))
                {
                    UNiagaraSimCache* Cache=nullptr;
                    if(UNiagaraSimCacheFunctionLibrary::CaptureNiagaraSimCacheImmediate(NewObject<UNiagaraSimCache>(FX),FNiagaraSimCacheCreateParameters(),FX,Cache))
                    {
                        TArray<FVector> P;TArray<FVector2D> S;TArray<float> Ages;
                        Cache->ReadPositionAttribute(P,TEXT("Position"),TEXT("RainDrops"));
                        Cache->ReadVector2Attribute(S,TEXT("SpriteSize"),TEXT("RainDrops"));
                        Cache->ReadFloatAttribute(Ages,TEXT("NormalizedAge"),TEXT("RainDrops"));
                        FBox Box(ForceInit);for(FVector V:P)Box+=V;
                        if(Visibility)
                        {
                            TArray<FVector> Velocities;
                            Cache->ReadVectorAttribute(Velocities,TEXT("Velocity"),TEXT("RainDrops"));
                            int32 Falling=0,InView=0;
                            const auto* Camera=UGameplayStatics::GetPlayerCameraManager(World,0);
                            auto* PC=UGameplayStatics::GetPlayerController(World,0);
                            for(int32 I=0;I<P.Num();++I)
                            {
                                const bool Down=Velocities.IsValidIndex(I)&&Velocities[I].Z<-300;
                                Falling+=Down;
                                FVector2D Screen;
                                if(Down&&P[I].Z>Camera->GetCameraLocation().Z-170&&
                                    PC->ProjectWorldLocationToScreen(P[I],Screen)&&Screen.X>0&&Screen.X<1280&&Screen.Y>0&&Screen.Y<720)++InView;
                            }
                            UE_LOG(LogTemp,Display,TEXT("RAIN_VISIBLE_GPU total=%d falling=%d falling_in_view_above_ground=%d"),P.Num(),Falling,InView);
                            CheckVisibility(P.Num()>200&&Falling>100&&InView>10,TEXT("GPU particles fall through the gameplay view"));
                            CheckVisibility(!S.IsEmpty()&&FMath::IsNearlyEqual(S[0].X,3.2f,.01f),TEXT("revised rain asset is actually loaded"));
                        }
                        UE_LOG(LogTemp,Display,TEXT("RAIN_GPU_CAPTURE count=%d bounds=%s size=%s age=%.3f component_bounds=%s"),P.Num(),*Box.ToString(),S.IsEmpty()?TEXT("none"):*S[0].ToString(),Ages.IsEmpty()?-1:Ages[0],*FX->Bounds.GetBox().ToString());
                    }
                }
                if(auto Controller=FX->GetSystemInstanceController())
                {
                    Controller->WaitForConcurrentTickAndFinalize();
                    if(auto* Instance=Controller->GetSystemInstance_Unsafe())
                        for(const auto& E:Instance->GetEmitters())
                            UE_LOG(LogTemp,Display,TEXT("RAIN_EMITTER component=%s system=%s active=%d particles_estimate=%d state=%d bounds=%s location=%s"),*FX->GetName(),*FX->GetAsset()->GetName(),FX->IsActive(),E->GetNumParticles(),int32(E->GetExecutionState()),*E->GetBounds().ToString(),*FX->GetComponentLocation().ToString());
                }
            }
            UE_LOG(LogTemp,Display,TEXT("RAIN_COMPONENT_MEMORY_ESTIMATE_KB %.1f"),Bytes/1024.0);
        }
        if (Step >= (Quick?20:40) && Step < EndStep)
        {
            const double Gpu = FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles());
            const double Ms = World->GetDeltaSeconds()*1000.0;
            GPU.Add(Gpu); Frame.Add(Ms);
            Rows += FString::Printf(TEXT("%d,%.3f,%.3f,%.3f,%.3f,%.2f,%.4f\n"),Step,Ms,Gpu,
                FPlatformTime::ToMilliseconds(GGameThreadTime),FPlatformTime::ToMilliseconds(GRenderThreadTime),
                FPlatformMemory::GetStats().UsedPhysical / 1048576.0,Weather->GetEffectiveRainIntensity());
        }
        const FString Dir = FPaths::ProjectSavedDir()/TEXT("RainUpgrade");
        const FString Name = UGameplayStatics::GetCurrentLevelName(World,true)+TEXT("-")+Label;
        if(Visibility)
        {
            auto* PC=UGameplayStatics::GetPlayerController(World,0);
            TInlineComponentArray<UNiagaraComponent*> Particles(Weather.Get());
            UNiagaraComponent* RainFX=nullptr;
            for(auto* FX:Particles)if(FX->GetFName()==TEXT("CameraRain"))RainFX=FX;
            if(Step>=40&&Step<56)
                FScreenshotRequest::RequestScreenshot(Dir/(Name+FString::Printf(TEXT("-frame-%02d.png"),Step-40)),true,false);
            if(Step==144)
            {
                TArray<FVector> Locations;
                float Furthest=0,FurthestProjected=0,ClosestPair=MAX_flt;
                const FVector Camera=UGameplayStatics::GetPlayerCameraManager(World,0)->GetCameraLocation();
                for(auto* D:TInlineComponentArray<UDecalComponent*>(Weather.Get()))if(D->IsVisible())
                {
                    Furthest=FMath::Max(Furthest,float(FVector::Dist2D(Camera,D->GetComponentLocation())));
                    FVector2D Screen;
                    if(PC->ProjectWorldLocationToScreen(D->GetComponentLocation(),Screen)&&Screen.X>0&&Screen.X<1280&&Screen.Y>0&&Screen.Y<720)
                        FurthestProjected=FMath::Max(FurthestProjected,float(FVector::Dist2D(Camera,D->GetComponentLocation())));
                    for(const FVector& P:Locations)ClosestPair=FMath::Min(ClosestPair,float(FVector::Dist2D(P,D->GetComponentLocation())));
                    Locations.Add(D->GetComponentLocation());
                }
                UE_LOG(LogTemp,Display,TEXT("PUDDLE_COVERAGE visible=%d farthest_cm=%.1f in_view_cm=%.1f minimum_spacing_cm=%.1f particle_components=%d"),Locations.Num(),Furthest,FurthestProjected,ClosestPair,Particles.Num());
                CheckVisibility(Locations.Num()>0&&Locations.Num()<=16&&Particles.Num()==22,TEXT("extended puddle coverage retains the fixed pool"));
                // Decals are offset 2cm along each receiver normal, including its XY
                // component on slopes; allow both offsets when measuring the grid.
                CheckVisibility(Furthest>2400&&ClosestPair>=1596,TEXT("puddles extend beyond 24m with a 16m grid (4cm normal-offset tolerance)"));
                if(UGameplayStatics::GetCurrentLevelName(World,true)==TEXT("DayNight_Lighting"))
                    CheckVisibility(FurthestProjected>3000,TEXT("a puddle center beyond 30m projects into the gameplay view"));
                FScreenshotRequest::RequestScreenshot(Dir/(Name+TEXT("-puddles.png")),true,false);
            }
            if(Step==152)IConsoleManager::Get().FindConsoleVariable(TEXT("fps.RainQuality"))->Set(0,ECVF_SetByCode);
            if(Step==156)
            {
                bool Zero=true,Valid=false;for(auto* FX:Particles)Zero&=FX->GetVariableFloat(TEXT("User.SpawnRate"),Valid)<.1f;
                for(auto* D:TInlineComponentArray<UDecalComponent*>(Weather.Get()))Zero&=!D->IsVisible();
                CheckVisibility(Zero,TEXT("quality zero clears all weather emissions and decals"));
                IConsoleManager::Get().FindConsoleVariable(TEXT("fps.RainQuality"))->Set(2,ECVF_SetByCode);
            }
            if(Step==160)
            {
                AActor* A=World->SpawnActor<AActor>();VisibilityRoof=A;
                auto* Box=NewObject<UBoxComponent>(A);A->SetRootComponent(Box);Box->SetBoxExtent(FVector(350,350,15));
                Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();
                A->SetActorLocation(UGameplayStatics::GetPlayerCameraManager(World,0)->GetCameraLocation()+FVector(0,0,400));
            }
            if(Step==180)
            {
                bool Valid=false;CheckVisibility(RainFX&&RainFX->GetVariableFloat(TEXT("User.SpawnRate"),Valid)<.1f,TEXT("shelter stops new camera rain"));
                if(VisibilityRoof.IsValid())VisibilityRoof->Destroy();
            }
            if(Step==204)
            {
                bool Valid=false;CheckVisibility(RainFX&&RainFX->GetVariableFloat(TEXT("User.SpawnRate"),Valid)>900,TEXT("falling rain resumes outdoors"));
                CheckVisibility(MaxVisibilityTraces<=8,TEXT("surface raycasts stay within the existing budget"));
            }
        }
        if (Step == (Quick?40:100))
            FScreenshotRequest::RequestScreenshot(Dir/(Name+TEXT(".png")),true,false);
        if (Step == EndStep)
        {
            GPU.Sort(); Frame.Sort();
            FFileHelper::SaveStringToFile(Rows,*(Dir/(Name+TEXT(".csv"))));
            UE_LOG(LogTemp,Display,TEXT("RAIN_PERF label=%s samples=%d gpu_median=%.3f gpu_p95=%.3f frame_median=%.3f frame_p95=%.3f"),
                *Label,GPU.Num(),GPU[GPU.Num()/2],GPU[FMath::FloorToInt(GPU.Num()*.95)],Frame[Frame.Num()/2],Frame[FMath::FloorToInt(Frame.Num()*.95)]);
            UE_LOG(LogTemp,Display,TEXT("RAIN_RENDER_AUDIT_PASS rain=%.3f"),Weather->GetEffectiveRainIntensity());
            if(Visibility)UE_LOG(LogTemp,Display,TEXT("RAIN_VISIBILITY_AUDIT_%s failures=%d"),VisibilityFailures?TEXT("FAIL"):TEXT("PASS"),VisibilityFailures);
            World->GetTimerManager().ClearTimer(Timer);
            if (APlayerController* PC = UGameplayStatics::GetPlayerController(World,0)) PC->ConsoleCommand(TEXT("quit"));
        }
    }
};
}
void StartRainUpgradeValidation(AFPSWeatherManager* Weather)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("RainSurfaceAudit")))
    {
        auto Audit=MakeShared<FRainSurfaceAudit>();Audit->Weather=Weather;
        Weather->GetWorld()->GetTimerManager().SetTimer(Audit->Timer,[Audit](){Audit->Tick();},1.f,true,3.f);return;
    }
    if (!FParse::Param(FCommandLine::Get(),TEXT("RainUpgradeAudit"))) return;
    auto Audit=MakeShared<FRainAudit>(); Audit->Weather=Weather; Audit->Label=TEXT("candidate");
    FParse::Value(FCommandLine::Get(),TEXT("RainLabel="),Audit->Label);
    IFileManager::Get().MakeDirectory(*(FPaths::ProjectSavedDir()/TEXT("RainUpgrade")),true);
    Weather->GetWorld()->GetTimerManager().SetTimer(Audit->Timer,[Audit](){Audit->Tick();},.25f,true,1.0f);
}
