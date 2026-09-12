#include "WeatherSurfaceComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Engine/World.h"

static TAutoConsoleVariable<int32> CVarRainQuality(TEXT("fps.RainQuality"),2,
    TEXT("Rain quality: 0 off, 1 low, 2 balanced, 3 high (footstep ripples)."),ECVF_Scalability);

namespace RainSurface
{
    constexpr double CellSize=1600.0;
    constexpr float PatchRadius=450.f;
}

UWeatherSurfaceComponent::UWeatherSurfaceComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickInterval=.1f;
}
int32 UWeatherSurfaceComponent::GetQuality(){return FMath::Clamp(CVarRainQuality.GetValueOnGameThread(),0,3);}
int32 UWeatherSurfaceComponent::GetValidPatchCount() const
{
    int32 Count=0;for(const auto& P:Patches) Count+=P.bValid;return Count;
}
void UWeatherSurfaceComponent::Initialize(UNiagaraSystem* Splashes,UNiagaraSystem* Drips,UMaterialInterface* Material)
{
    SplashAsset=Splashes; SurfaceMaterial=Material;
    // Pools are allocated once and share the same material/shader and Niagara assets.
    for(int32 Index=0;Index<16;++Index)
    {
        FWeatherSurfacePatch& Patch=Patches.AddDefaulted_GetRef();
        Patch.Decal=NewObject<UDecalComponent>(GetOwner(),*FString::Printf(TEXT("RainWetPatch%d"),Index));
        Patch.Decal->SetAbsolute(true,true,true);
        Patch.Decal->DecalSize=FVector(14,RainSurface::PatchRadius,RainSurface::PatchRadius);
        Patch.Decal->SetFadeScreenSize(.0002f);
        Patch.Decal->SetVisibility(false);
        Patch.Decal->RegisterComponent();
        if(Material)
        {
            Patch.Material=UMaterialInstanceDynamic::Create(Material,this);
            Patch.Decal->SetDecalMaterial(Patch.Material);
        }
        Patch.Splash=NewObject<UNiagaraComponent>(GetOwner(),*FString::Printf(TEXT("RainSurfaceSplash%d"),Index));
        Patch.Splash->SetAutoActivate(false);
        Patch.Splash->SetAsset(Splashes);
        Patch.Splash->SetAbsolute(true,true,true);
        Patch.Splash->SetCastShadow(false);
        Patch.Splash->RegisterComponent();
    }
    for(int32 Index=0;Index<4;++Index)
    {
        auto* Drip=NewObject<UNiagaraComponent>(GetOwner(),*FString::Printf(TEXT("RainRoofDrip%d"),Index));
        Drip->SetAutoActivate(false);Drip->SetAsset(Drips);Drip->SetAbsolute(true,true,true);
        Drip->SetCastShadow(false);Drip->RegisterComponent();DripPool.Add(Drip);
    }
}
bool UWeatherSurfaceComponent::Trace(const FVector& Start,const FVector& End,FHitResult& Hit)
{
    ++LastTraceCount;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(RainSurface),true,GetOwner());
    if(APawn* Pawn=UGameplayStatics::GetPlayerPawn(this,0))Params.AddIgnoredActor(Pawn);
    return GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Params);
}
void UWeatherSurfaceComponent::Place(FWeatherSurfacePatch& Patch,FIntPoint Cell,const FVector& Camera)
{
    constexpr double CellSize=RainSurface::CellSize;
    const FVector Origin((Cell.X+.5)*CellSize,(Cell.Y+.5)*CellSize,Camera.Z+2000);
    FHitResult Hit;
    const bool bWasValid=Patch.bValid&&Patch.Cell==Cell;
    Patch.Cell=Cell;
    Patch.bValid=Trace(Origin,Origin-FVector(0,0,5000),Hit)&&Hit.ImpactNormal.Z>.72f;
    if(Patch.bValid&&bWasValid&&Patch.Contact.Equals(Hit.ImpactPoint,1.f))return;
    Patch.Decal->SetVisibility(false);
    Patch.Splash->DeactivateImmediate();
    if(!Patch.bValid)return;
    Patch.Contact=Hit.ImpactPoint;
    Patch.Decal->SetWorldLocation(Hit.ImpactPoint+Hit.ImpactNormal*2);
    // UE decals project along local X; orient the volume into the receiving surface.
    Patch.Decal->SetWorldRotation(FRotationMatrix::MakeFromX(-Hit.ImpactNormal).Rotator());
    Patch.Splash->SetWorldLocation(Hit.ImpactPoint+Hit.ImpactNormal*3);
    Patch.Splash->SetWorldRotation(FRotationMatrix::MakeFromZ(Hit.ImpactNormal).Rotator());
}
void UWeatherSurfaceComponent::TickComponent(float Dt,ELevelTick TickType,FActorComponentTickFunction* TF)
{
    Super::TickComponent(Dt,TickType,TF);
    TRACE_CPUPROFILER_EVENT_SCOPE(RainSurfacePool);
    LastTraceCount=0;
    Wetness=FMath::Clamp(Wetness+(Rain>.04f ? Rain*.035f : -.006f)*Dt,0.f,1.f);
    const int32 Quality=GetQuality();
    auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if(!Camera || Patches.IsEmpty())return;
    const FVector Position=Camera->GetCameraLocation();
    const int32 Side=Quality>=2?4:Quality==1?2:0;
    TArray<FIntPoint,TInlineAllocator<16>> Wanted;
    // Even-sided grids center on the nearest cell boundary, avoiding a full-cell
    // backward bias (especially when the player straddles world coordinate zero).
    const FIntPoint Center(FMath::RoundToInt(Position.X/RainSurface::CellSize),FMath::RoundToInt(Position.Y/RainSurface::CellSize));
    for(int32 X=0;X<Side;++X)for(int32 Y=0;Y<Side;++Y)Wanted.Add(Center+FIntPoint(X-Side/2,Y-Side/2));
    // At most two placements per update. Existing cells never drift with the camera.
    if(Rain>.01f || Wetness>.01f)
    {
        int32 Budget=2;
        for(const FIntPoint Cell:Wanted)
        {
            if(Patches.ContainsByPredicate([Cell](const auto& P){return P.Cell==Cell;}))continue;
            auto* Patch=Patches.FindByPredicate([&Wanted](const auto& P){return !Wanted.Contains(P.Cell);});
            if(Patch){Place(*Patch,Cell,Position);if(--Budget<=0)break;}
        }
        // Revisit one cell twice per second for streamed or newly placed roofs.
        if(Budget>0&&!Wanted.IsEmpty()&&Cursor%5==0)
        {
            const FIntPoint Cell=Wanted[(Cursor/5)%Wanted.Num()];
            if(auto* Patch=Patches.FindByPredicate([Cell](const auto& P){return P.Cell==Cell;}))Place(*Patch,Cell,Position);
        }
    }
    for(auto& Patch:Patches)
    {
        const bool Enabled=Quality>0&&Patch.bValid&&Wanted.Contains(Patch.Cell);
        Patch.Decal->SetVisibility(Enabled&&Wetness>.015f);
        if(Patch.Material)
        {
            Patch.Material->SetScalarParameterValue(TEXT("Wetness"),Enabled?Wetness:0);
            Patch.Material->SetScalarParameterValue(TEXT("Rain"),Rain);
        }
        // Far puddles retain reflections; tiny splash particles are useful only nearby.
        const float SplashFade=1.f-FMath::Clamp((FVector::Dist2D(Position,Patch.Contact)-800.f)/600.f,0.f,1.f);
        const float Rate=Enabled?Rain*(Quality==1?5.f:14.f)*SplashFade:0;
        Patch.Splash->SetFloatParameter(TEXT("User.SpawnRate"),Rate);
        Patch.Splash->SetFloatParameter(TEXT("User.RainIntensity"),Rain);
        if(Rate>.1f&&!Patch.Splash->IsActive())Patch.Splash->Activate();
        if(Rate<=.1f&&Patch.Splash->IsActive())Patch.Splash->Deactivate();
    }
    // Probe one possible eave at a time, never raycast for every rain particle.
    const int32 Slot=Cursor++%4;
    UNiagaraComponent* Drip=DripPool[Slot];
    if(Quality>=2&&Rain>.1f)
    {
        const FVector Direction=FRotator(0,Slot*90,0).Vector();
        const FVector Near=Position+Direction*200;
        FHitResult Roof,Outside;
        const bool bRoof=Trace(Near+FVector(0,0,1800),Near-FVector(0,0,300),Roof)&&Roof.ImpactPoint.Z>Position.Z+40;
        const FVector Far=Near+Direction*250;
        const bool bOutside=bRoof&&Trace(Far+FVector(0,0,1800),Far-FVector(0,0,1800),Outside)&&Outside.ImpactPoint.Z<Roof.ImpactPoint.Z-120;
        if(bOutside)
        {
            // A short binary search finds the eave, bounded to this one slot/update.
            FVector A=Near,B=Far;
            for(int32 I=0;I<3;++I)
            {
                FVector Mid=(A+B)*.5;FHitResult Edge;
                if(Trace(Mid+FVector(0,0,1800),Mid-FVector(0,0,1800),Edge)&&Edge.ImpactPoint.Z>Roof.ImpactPoint.Z-60)A=Mid;else B=Mid;
            }
            Drip->SetWorldLocation(FVector(B.X,B.Y,Roof.ImpactPoint.Z-5));
        }
        Drip->SetFloatParameter(TEXT("User.SpawnRate"),bOutside?Rain*12:0);
        if(bOutside&&!Drip->IsActive())Drip->Activate();
        if(!bOutside&&Drip->IsActive())Drip->Deactivate();
    }
    else for(UNiagaraComponent* D:DripPool){D->SetFloatParameter(TEXT("User.SpawnRate"),0);D->Deactivate();}
    // High quality uses analytic ripple rings: no render targets or fluid grid allocations.
    if(Quality==3&&Wetness>.25f)
    {
        if(!bHasFootstep){LastFootstep=Position;bHasFootstep=true;}
        if(FVector::DistSquared2D(Position,LastFootstep)>FMath::Square(90.f))
        {
            FHitResult Foot;
            if(Trace(Position,Position-FVector(0,0,240),Foot))
                for(auto& P:Patches)if(P.bValid&&FVector::DistSquared2D(P.Contact,Foot.ImpactPoint)<FMath::Square(500.f)&&P.Material)
                {
                    P.Material->SetVectorParameterValue(TEXT("StepPosition"),FLinearColor(Foot.ImpactPoint.X,Foot.ImpactPoint.Y,0,0));
                    P.Material->SetScalarParameterValue(TEXT("StepTime"),GetWorld()->GetTimeSeconds());
                }
            LastFootstep=Position;
        }
    }
}
