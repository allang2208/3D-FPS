#include "RiverPilotFXSubsystem.h"
#include "FluidPresentationSubsystem.h"
#include "TemperateHillsWorld.h"
#include "WaterImpactFootprints.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/Level.h"
#include "GameFramework/WorldSettings.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

bool URiverPilotFXSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game||Type==EWorldType::PIE;}

void URiverPilotFXSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    if(InWorld.GetNetMode()==NM_DedicatedServer)return;
    LastBudgetTime=InWorld.GetTimeSeconds();
    SteamLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(SteamTemplate.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this](){PrepareSteamPool();SteamLoad.Reset();}));
    for(ULevel* Level:InWorld.GetLevels())RegisterLevelWater(Level,&InWorld);
    LevelAddedHandle=FWorldDelegates::LevelAddedToWorld.AddUObject(this,&URiverPilotFXSubsystem::RegisterLevelWater);
    SplashLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(ImpactTemplate.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this](){PrepareSplashPool(ImpactTemplate.Get());SplashLoad.Reset();}));
}

void URiverPilotFXSubsystem::RegisterLevelWater(ULevel* Level,UWorld* World)
{
    if(World!=GetWorld()||!Level||World->GetNetMode()==NM_DedicatedServer)return;
    // Once at level arrival, never a world scan on fire or Tick.
    for(AActor* Actor:Level->Actors)if(IsValid(Actor))
    {
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Actor);
        for(auto* Mesh:Meshes)RegisterWaterSurface(Mesh);
    }
}

void URiverPilotFXSubsystem::RegisterWaterSurface(UStaticMeshComponent* Component)
{
    if(!Component||GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    const auto* Shape=FindWaterImpactFootprint(Component->GetStaticMesh());
    if(!Shape)return;
    StaticSurfaces.RemoveAll([](const FRegisteredWaterSurface& S){return !S.Component.IsValid();});
    for(const auto& Surface:StaticSurfaces)if(Surface.Component.Get()==Component)return;
    if(auto* Material=Component->CreateDynamicMaterialInstance(0))
    {
        Material->SetScalarParameterValue(TEXT("WaterImpactEnabled"),1.f);
        for(int32 I=0;I<RippleSlots;++I)
            Material->SetVectorParameterValue(FName(*FString::Printf(TEXT("WaterHit%d"),I)),FLinearColor(0,0,-10000,0));
        StaticSurfaces.Add({Component,Material,Shape});
    }
}

void URiverPilotFXSubsystem::UnregisterWaterSurface(UStaticMeshComponent* Component)
{
    StaticSurfaces.RemoveAll([Component](const FRegisteredWaterSurface& S){return !S.Component.IsValid()||S.Component.Get()==Component;});
}

bool URiverPilotFXSubsystem::IsWaterSurfaceRegistered(const UStaticMeshComponent* Component) const
{
    if(!Component)return false;
    for(const auto& Surface:StaticSurfaces)if(Surface.Component.Get()==const_cast<UStaticMeshComponent*>(Component))return true;
    return false;
}

void URiverPilotFXSubsystem::PrepareSplashPool(UNiagaraSystem* Splash)
{
    if(!Splash||!SplashPool.IsEmpty()||GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    // World-owned: removing a river/fountain must not destroy another water body's active hit.
    auto* Owner=GetWorld()->GetWorldSettings();
    for(int32 I=0;I<SplashSlots;++I)
    {
        auto* FX=NewObject<UNiagaraComponent>(Owner,NAME_None,RF_Transient);
        Owner->AddInstanceComponent(FX);
        FX->SetAutoActivate(false);FX->SetAutoDestroy(false);FX->SetAsset(Splash);
        FX->SetCastShadow(false);FX->SetCanEverAffectNavigation(false);
        FX->RegisterComponent();SplashPool.Add(FX);
    }
}

void URiverPilotFXSubsystem::BindRiver(ATemperateHillsWorld* River,TemperateRiver::FPlanPtr Plan,
    UMaterialInterface* Material,UNiagaraSystem* Splash)
{
    if(OwnerRiver.Get()==River&&WaterMID)return;
    if(OwnerRiver.IsValid())UnbindRiver(OwnerRiver.Get());
    if(!River||!Plan||Plan->Points.Num()<2||!Material||!Splash||GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    OwnerRiver=River;RiverPlan=MoveTemp(Plan);
    WaterMID=UMaterialInstanceDynamic::Create(Material,this);
    WaterMID->SetScalarParameterValue(TEXT("WaterImpactEnabled"),1.f);
    for(int32 I=0;I<RippleSlots;++I)
        WaterMID->SetVectorParameterValue(FName(*FString::Printf(TEXT("WaterHit%d"),I)),FLinearColor(0,0,-10000,0));
    PrepareSplashPool(Splash);
    UE_LOG(LogTemp,Display,TEXT("WATER_IMPACTS full river seed=%d length_m=%.0f splash=%s"),
        River->Seed,RiverPlan->Points.Last().Distance/100.,*Splash->GetPathName());
}

UMaterialInterface* URiverPilotFXSubsystem::GetRiverMaterial() const{return WaterMID.Get();}

bool URiverPilotFXSubsystem::FindStaticCrossing(const FVector& Start,const FVector& End,FVector& Position,
    FVector& Normal,UMaterialInstanceDynamic*& Material,float& Scale) const
{
    double Best=2.;
    for(const auto& Surface:StaticSurfaces)
    {
        const auto* Component=Surface.Component.Get();
        if(!Component||!Surface.Material.IsValid()||!Component->IsRegistered()||!Component->IsVisible()
            ||Component->GetOwner()->IsHidden())continue;
        const FTransform& Transform=Component->GetComponentTransform();
        const FVector A=Transform.InverseTransformPosition(Start),B=Transform.InverseTransformPosition(End);
        if(B.Z>=A.Z-KINDA_SMALL_NUMBER)continue;
        for(const auto& Patch:Surface.Footprint->Patches)
        {
            const double T=(Patch.Z-A.Z)/(B.Z-A.Z);
            if(T<0||T>1||T>=Best)continue;
            const FVector2D P(FMath::Lerp(A,B,T));
            if(!Patch.Bounds.IsInsideOrOn(P))continue;
            bool Inside=false;
            for(int32 I=0,J=Patch.Polygon.Num()-1;I<Patch.Polygon.Num();J=I++)
            {
                const FVector2D& V=Patch.Polygon[I];const FVector2D& W=Patch.Polygon[J];
                if((V.Y>P.Y)!=(W.Y>P.Y)&&P.X<(W.X-V.X)*(P.Y-V.Y)/(W.Y-V.Y)+V.X)Inside=!Inside;
            }
            if(!Inside)continue;
            Best=T;Position=FMath::Lerp(Start,End,T);
            Normal=Transform.TransformVectorNoScale(FVector::UpVector).GetSafeNormal();
            Material=Surface.Material.Get();Scale=Surface.Footprint->StrengthScale;
        }
    }
    return Best<=1.;
}

bool URiverPilotFXSubsystem::FindWaterCrossing(const FVector& Start,const FVector& End,FFluidWaterContact& Contact) const
{
    Contact=FFluidWaterContact();double Along=0;
    FVector Position=End,Normal=FVector::UpVector;UMaterialInstanceDynamic* Material=nullptr;float Scale=1;
    if(OwnerRiver.IsValid()&&WaterMID&&RiverPlan&&RiverPlan->IntersectWaterSegment(Start,End,
        0.,RiverPlan->Points.Last().Distance,Position,Normal,Along)
        &&OwnerRiver->Height(Position.X,Position.Y)<Position.Z-1.)Material=WaterMID;
    const FVector WaterEnd=Material?Position:End;
    Contact.Static=FindStaticCrossing(Start,WaterEnd,Position,Normal,Material,Scale);
    Contact.Position=Position;Contact.Normal=Normal;Contact.Material=Material;Contact.Scale=Scale;
    return Material!=nullptr;
}

bool URiverPilotFXSubsystem::SampleWater(const FVector& Feet,float MaxDepth,FFluidWaterContact& Contact) const
{
    if(!FindWaterCrossing(Feet+FVector(0,0,MaxDepth),Feet-FVector(0,0,2),Contact))return false;
    Contact.Depth=FMath::Max(0.f,float(Contact.Position.Z-Feet.Z));
    return true;
}

bool URiverPilotFXSubsystem::TryBulletCrossing(const FVector& Start,const FVector& End,float SpeedCM)
{
    FFluidWaterContact Contact;if(!FindWaterCrossing(Start,End,Contact))return false;
    const FVector Direction=(End-Start).GetSafeNormal();
    const float Incidence=FMath::Clamp(float(-FVector::DotProduct(Direction,Contact.Normal)),0.f,1.f);
    const float Strength=FMath::Clamp(SpeedCM/35000.f,.75f,1.25f)*FMath::Lerp(.7f,1.f,Incidence);
    EmitWater(Contact,FMath::Max(.85f,Strength),Direction*45.f+FVector(0,0,15),true);
    return true;
}

void URiverPilotFXSubsystem::EmitWater(const FFluidWaterContact& Contact,float Strength,const FVector& Flow,bool bImportant,float Spread)
{
    auto* Material=Contact.Material.Get();if(!Material)return;
    const double Now=GetWorld()->GetTimeSeconds();
    Tokens=FMath::Min(6.f,Tokens+float(FMath::Max(0.,Now-LastBudgetTime))*30.f);LastBudgetTime=Now;
    if(Tokens<(bImportant?1.f:3.f))return;
    --Tokens;
    const FVector& Position=Contact.Position;const float Scale=Contact.Scale;
    const FName HitName(*FString::Printf(TEXT("WaterHit%d"),RippleCursor));
    if(auto* Previous=RippleOwners[RippleCursor].Get())
        Previous->SetVectorParameterValue(HitName,FLinearColor(0,0,-10000,0));
    Material->SetVectorParameterValue(HitName,FLinearColor(Position.X,Position.Y,Now,Strength*Scale));
    Material->SetVectorParameterValue(FName(*FString::Printf(TEXT("WaterHitMeta%d"),RippleCursor)),
        FLinearColor(Position.Z,Strength*Scale,Scale*Spread,Contact.Static?12.f:0.f));
    RippleOwners[RippleCursor]=Material;RippleCursor=(RippleCursor+1)%RippleSlots;
    auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    const int32 Granted=Budget?Budget->AllocateDetail(Position,8,bImportant):8;
    if(Granted==0)return; // Low-cost surface rings survive when splash detail is exhausted.
    for(auto& FX:SplashPool)if(FX&&!FX->IsActive())
    {
        FX->SetWorldLocationAndRotation(Position+Contact.Normal*1.5,FRotator::ZeroRotator);
        FX->SetVariableFloat(TEXT("User.Strength"),Strength*Scale);
        FX->SetVariableVec3(TEXT("User.Flow"),Flow*Scale);
        FX->SetVariableFloat(TEXT("User.DetailReduction"),1.f-float(Granted)/8.f);
        FX->Activate(true);break;
    }
}

void URiverPilotFXSubsystem::CharacterWater(const FFluidWaterContact& Contact,const FVector& Velocity,float LandingSpeed,bool bPlayer)
{
    const float Speed=Velocity.Size2D();
    const float DepthScale=FMath::Lerp(.52f,1.05f,FMath::Clamp(Contact.Depth/65.f,0.f,1.f));
    const float Strength=LandingSpeed>0?FMath::Clamp(LandingSpeed/500.f,.9f,1.75f)
        :FMath::Lerp(.34f,.85f,FMath::Clamp(Speed/650.f,0.f,1.f))*DepthScale;
    EmitWater(Contact,Strength,Velocity.GetClampedToMaxSize(650.f)*.07f+FVector(0,0,LandingSpeed>0?32:10),bPlayer);
}

void URiverPilotFXSubsystem::PrepareSteamPool()
{
    auto* Asset=SteamTemplate.Get();if(!Asset||!SteamPool.IsEmpty())return;
    auto* Owner=GetWorld()->GetWorldSettings();
    for(int32 I=0;I<6;++I)
    {
        auto* FX=NewObject<UNiagaraComponent>(Owner,NAME_None,RF_Transient);Owner->AddInstanceComponent(FX);
        FX->SetAutoActivate(false);FX->SetAutoDestroy(false);FX->SetAsset(Asset);FX->SetCastShadow(false);
        FX->SetCanEverAffectNavigation(false);FX->RegisterComponent();SteamPool.Add(FX);
    }
}

bool URiverPilotFXSubsystem::TryFireCrossing(const FVector& Start,const FVector& End,float Radius,bool bMeteor)
{
    FFluidWaterContact Contact;if(!FindWaterCrossing(Start,End,Contact))return false;
    const float Size=FMath::Clamp(Radius/210.375f,.6f,2.f);
    EmitWater(Contact,(bMeteor?1.9f:1.4f)*Size,FVector(0,0,bMeteor?85:55),true,(bMeteor?1.65f:1.2f)*Size);
    for(auto& FX:SteamPool)if(FX&&!FX->IsActive())
    {
        FX->SetWorldLocationAndRotation(Contact.Position+Contact.Normal*8,FRotationMatrix::MakeFromZ(Contact.Normal).Rotator());
        FX->SetWorldScale3D(FVector(Size));
        FX->SetVariableVec3(TEXT("User.LocalUp"),FX->GetComponentTransform().InverseTransformVectorNoScale(FVector::UpVector));
        FX->SetVariableFloat(TEXT("User.ImpactGrowth"),Size-1);
        FX->SetVariableFloat(TEXT("User.SurfaceHit"),1);
        FX->SetVariableFloat(TEXT("User.SteamCount"),bMeteor?6.f:4.f);
        if(auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Budget->ConfigureSmoke(FX,bMeteor?6:4,true);
        FX->Activate(true);break;
    }
    return true;
}

bool URiverPilotFXSubsystem::IsSubmergedRiverbed(const FHitResult& Hit) const
{
    if(RiverPlan&&OwnerRiver.IsValid()&&Hit.GetActor()==OwnerRiver.Get())
    {
        const auto Sample=RiverPlan->Sample(Hit.ImpactPoint.X,Hit.ImpactPoint.Y);
        if(Sample.Distance<Sample.HalfWidth&&Hit.ImpactPoint.Z<Sample.WaterZ-1.)return true;
    }
    // Only the thin wet floor directly below a registered surface suppresses dry dust.
    FVector Position,Normal;UMaterialInstanceDynamic* Material=nullptr;float Scale=1.f;
    return FindStaticCrossing(Hit.ImpactPoint+FVector(0,0,3),Hit.ImpactPoint,Position,Normal,Material,Scale);
}

void URiverPilotFXSubsystem::UnbindRiver(ATemperateHillsWorld* River)
{
    if(River&&River!=OwnerRiver.Get())return;
    WaterMID=nullptr;RiverPlan.Reset();OwnerRiver.Reset();
}

void URiverPilotFXSubsystem::Deinitialize()
{
    FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
    if(SplashLoad){SplashLoad->CancelHandle();SplashLoad.Reset();}
    if(SteamLoad){SteamLoad->CancelHandle();SteamLoad.Reset();}
    for(auto& FX:SteamPool)if(FX)
    {
        FX->DeactivateImmediate();
        if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);
        FX->DestroyComponent();
    }
    SteamPool.Reset();
    UnbindRiver(nullptr);StaticSurfaces.Reset();
    for(auto& Owner:RippleOwners)Owner.Reset();
    for(auto& FX:SplashPool)if(FX)
    {
        FX->DeactivateImmediate();
        if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);
        FX->DestroyComponent();
    }
    SplashPool.Reset();Super::Deinitialize();
}

void URiverPilotFXSubsystem::UpdateWake(AActor* Owner,const FFluidWaterContact& Contact,const FVector& Velocity,float Width)
{
    auto* Material=Contact.Material.Get();const float Speed=Velocity.Size2D();
    if(!Owner||!Material||Speed<55.f||Contact.Depth<3.f)return;
    const double Now=GetWorld()->GetTimeSeconds();
    const auto* Pawn=Cast<APawn>(Owner);const bool Player=Pawn&&Pawn->IsPlayerControlled();
    int32 Slot=Player?0:1;
    if(!Player)
    {
        for(int32 I=1;I<4;++I)
        {
            if(Wakes[I].Owner.Get()==Owner){Slot=I;break;}
            if(Wakes[I].Time<Wakes[Slot].Time)Slot=I;
        }
        if(Wakes[Slot].Owner.Get()!=Owner&&Now-Wakes[Slot].Time<.24)return;
    }
    auto& Wake=Wakes[Slot];if(Wake.Owner.Get()==Owner&&Now-Wake.Time<.10)return;
    const FName MotionName(*FString::Printf(TEXT("WaterWakeMotion%d"),Slot));
    if(auto* Old=Wake.Material.Get();Old&&Old!=Material)Old->SetVectorParameterValue(MotionName,FLinearColor(1,0,0,-10000));
    const FVector Direction=Velocity.GetSafeNormal2D();
    Material->SetVectorParameterValue(FName(*FString::Printf(TEXT("WaterWake%d"),Slot)),
        FLinearColor(Contact.Position.X,Contact.Position.Y,Contact.Position.Z,FMath::Clamp(Width,12.f,100.f)*Contact.Scale));
    Material->SetVectorParameterValue(MotionName,FLinearColor(Direction.X,Direction.Y,FMath::Clamp(Speed/650.f,.08f,1.f),Now));
    Wake.Owner=Owner;Wake.Material=Material;Wake.Time=Now;
}

bool URiverPilotFXSubsystem::BodyWater(const FVector& Previous,const FVector& Position,const FVector& Velocity,const FVector& Extent,float Mass)
{
    if(Mass<2.f||Velocity.Z> -60.f||Extent.GetMax()<12)return false;
    FFluidWaterContact Contact;if(!FindWaterCrossing(Previous,Position,Contact))return false;
    const float Radius=FMath::Clamp(float(FMath::Sqrt(Extent.X*Extent.Y)),12.f,180.f);
    const float Energy=FMath::Clamp(FMath::Sqrt(Mass/20.f)*FMath::Abs(float(Velocity.Z))/400.f,.45f,2.f);
    EmitWater(Contact,Energy,Velocity*.045f+FVector(0,0,35),true,FMath::Clamp(Radius/35.f,.7f,3.f));
    if(Radius>40.f)
    {
        const FVector Side=FVector::CrossProduct(Contact.Normal,Velocity.GetSafeNormal2D(UE_SMALL_NUMBER,FVector::ForwardVector)).GetSafeNormal();
        for(int32 Sign=-1;Sign<=1;Sign+=2)
        {
            FFluidWaterContact Edge;
            if(SampleWater(Contact.Position+Side*(Radius*.5f*Sign)-FVector(0,0,2),40,Edge))
                EmitWater(Edge,Energy*.7f,Velocity*.03f+FVector(0,0,25),false,FMath::Clamp(Radius/50.f,.6f,2.f));
        }
    }
    return true;
}
