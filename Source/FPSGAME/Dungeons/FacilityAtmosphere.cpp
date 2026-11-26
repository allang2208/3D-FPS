#include "FacilityAtmosphere.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Scalability.h"
#include "Misc/Crc.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"

namespace
{
    TAutoConsoleVariable<int32> Enabled(TEXT("fps.Dungeon.Atmosphere"),1,
        TEXT("Local facility cosmetic mist/steam/dust. Does not affect spawn-door concealment or hazards."));
    FVector VectorField(const TSharedPtr<FJsonObject>& O,const TCHAR* Key)
    {
        const auto& A=O->GetArrayField(Key);
        return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());
    }
}

FFacilityAtmosphereSite FFacilityAtmosphereSite::FromJson(const TSharedPtr<FJsonObject>& Spec,
    const FTransform& Room,int32 ModuleIndex,UNiagaraSystem* Asset,UStaticMesh* Mesh,UMaterialInterface* Material)
{
    FFacilityAtmosphereSite S;
    S.Transform=FTransform(FRotator(0,Spec->GetNumberField(TEXT("yaw")),0),VectorField(Spec,TEXT("position")))*Room;
    S.Extent=VectorField(Spec,TEXT("extent"));
    const auto Color=VectorField(Spec,TEXT("tint"));S.Tint=FLinearColor(Color.X,Color.Y,Color.Z);
    S.Module=ModuleIndex;S.System=Asset;S.Kind=Spec->GetIntegerField(TEXT("kind"));
    S.FogMesh=Mesh;S.FogMaterial=Material;
    S.Density=Spec->GetNumberField(TEXT("density"));S.Rate=Spec->GetNumberField(TEXT("rate"));
    S.Distance=Spec->GetNumberField(TEXT("distance"));
    S.Seed=int32(HashCombineFast(FCrc::StrCrc32(*Spec->GetStringField(TEXT("id"))),uint32(ModuleIndex))&0x7fffffff);
    return S;
}

void FFacilityAtmosphere::Reset()
{
    for(auto& Slot:Slots)
    {
        if(auto* FX=Slot.FX.Get())
        {
            FX->DeactivateImmediate();
            if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);
            FX->DestroyComponent();
        }
        if(auto* Fog=Slot.Fog.Get())
        {
            if(auto* Owner=Fog->GetOwner())Owner->RemoveInstanceComponent(Fog);
            Fog->DestroyComponent();
        }
    }
    Slots.Reset();Sites.Reset();
}

void FFacilityAtmosphere::Install(AActor* Owner,TArray<FFacilityAtmosphereSite>&& InSites)
{
    Reset();
    if(!Owner||!Owner->GetWorld()->IsGameWorld()||Owner->GetNetMode()==NM_DedicatedServer)return;
    Sites=MoveTemp(InSites);
    for(int32 Kind=0;Kind<3;++Kind)
    {
        const auto* Template=Sites.FindByPredicate([Kind](const auto& Site){return Site.Kind==Kind&&Site.HasAsset();});
        if(!Template)continue;
        const int32 Count=Kind==0?4:2;
        for(int32 Index=0;Index<Count;++Index)
        {
            FSlot Slot;Slot.Kind=Kind;
            if(Kind==0)
            {
                // Same mesh/material pipeline as TemperateHills::BuildValleyFog, without BP ticks.
                auto* Fog=NewObject<UStaticMeshComponent>(Owner);
                Fog->SetMobility(EComponentMobility::Movable);
                Fog->SetupAttachment(Owner->GetRootComponent());
                Fog->SetCollisionEnabled(ECollisionEnabled::NoCollision);Fog->SetCanEverAffectNavigation(false);
                Fog->SetCastShadow(false);Fog->SetGenerateOverlapEvents(false);
                Fog->SetStaticMesh(Template->FogMesh.Get());
                auto* MID=UMaterialInstanceDynamic::Create(Template->FogMaterial.Get(),Fog);
                MID->SetScalarParameterValue(TEXT("FogOverallDensity"),0.f);
                Fog->SetMaterial(0,MID);Fog->SetVisibility(false);
                Owner->AddInstanceComponent(Fog);Fog->RegisterComponent();
                Fog->SetComponentTickEnabled(false);Fog->PrecachePSOs();
                Slot.Fog=Fog;Slot.FogMID=MID;Slots.Add(Slot);
                continue;
            }
            auto* FX=NewObject<UNiagaraComponent>(Owner);
            FX->SetAutoActivate(false);FX->SetAutoDestroy(false);
            FX->SetCanEverAffectNavigation(false);FX->SetCastShadow(false);
            FX->SetMobility(EComponentMobility::Movable);
            FX->SetupAttachment(Owner->GetRootComponent());
            FX->SetAsset(Template->System.Get());
            Owner->AddInstanceComponent(FX);FX->RegisterComponent();
            FX->SetVisibility(false);FX->SetComponentTickEnabled(false);
            Slot.FX=FX;Slots.Add(Slot);
        }
    }
}

void FFacilityAtmosphere::Update(AActor* Owner,const TArray<bool>& WantedRooms,double Now,float Delta)
{
    if(Slots.IsEmpty())return;
    TArray<FVector,TInlineAllocator<2>> Eyes;
    if(Enabled.GetValueOnGameThread()!=0)
        for(auto It=Owner->GetWorld()->GetPlayerControllerIterator();It;++It)
            if(auto* PC=It->Get();PC&&PC->IsLocalController()&&PC->GetLocalPlayer())
            {FVector Eye;FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);Eyes.Add(Eye);}
    const int32 Quality=Scalability::GetQualityLevels().EffectsQuality;
    const int32 Limits[3]={Quality<=0?2:4,Quality<=0?1:2,Quality<=0?0:2};
    TArray<int32,TInlineAllocator<8>> Desired;
    // Prefer retained sites slightly, so nearly equal doorway distances do not churn pool slots.
    for(int32 Kind=0;Kind<3;++Kind)
        for(int32 Pick=0;Pick<Limits[Kind];++Pick)
        {
            int32 Best=INDEX_NONE;double Score=TNumericLimits<double>::Max();
            for(int32 I=0;I<Sites.Num();++I)
            {
                const auto& Site=Sites[I];
                if(Site.Kind!=Kind||Desired.Contains(I)||!Site.HasAsset())continue;
                if(WantedRooms.IsValidIndex(Site.Module)&&!WantedRooms[Site.Module])continue;
                double Distance=TNumericLimits<double>::Max();
                for(const FVector& Eye:Eyes)Distance=FMath::Min(Distance,FVector::DistSquared(Eye,Site.Transform.GetLocation()));
                if(Distance>FMath::Square(Site.Distance))continue;
                if(Slots.ContainsByPredicate([I](const FSlot& S){return S.Site==I;}))Distance*=.75;
                if(Distance<Score){Score=Distance;Best=I;}
            }
            if(Best!=INDEX_NONE)Desired.Add(Best);
        }
    auto* Budget=Owner->GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    for(auto& Slot:Slots)
    {
        auto* FX=Slot.FX.Get();auto* Fog=Slot.Fog.Get();auto* MID=Slot.FogMID.Get();
        if(Slot.Kind==0?(!Fog||!MID):!FX)continue;
        bool Keep=Desired.Contains(Slot.Site);
        if(Slot.Site!=INDEX_NONE&&!Keep)
        {
            Slot.Alpha=FMath::FInterpConstantTo(Slot.Alpha,0.f,Delta,1.25f);
            if(FX)
            {
                FX->SetVariableFloat(TEXT("User.Visibility"),Slot.Alpha);
                FX->SetVariableFloat(TEXT("User.SpawnRate"),0.f);
            }
            else MID->SetScalarParameterValue(TEXT("FogOverallDensity"),Sites[Slot.Site].Density*Slot.Alpha);
            if(Slot.Alpha>0.f)continue;
            if(FX){FX->DeactivateImmediate();FX->SetVisibility(false);FX->SetComponentTickEnabled(false);}
            else Fog->SetVisibility(false);
            Slot.Site=INDEX_NONE;
        }
        if(Slot.Site==INDEX_NONE)
        {
            for(int32 I:Desired)
                if(Sites[I].Kind==Slot.Kind&&!Slots.ContainsByPredicate([I](const FSlot& S){return S.Site==I;}))
                {Slot.Site=I;break;}
            if(Slot.Site==INDEX_NONE)continue;
            const auto& Site=Sites[Slot.Site];
            if(Fog)
            {
                const auto Bounds=Site.FogMesh->GetBounds();
                const FVector Scale=Site.Extent/Bounds.BoxExtent;
                FTransform Placement=Site.Transform;
                Placement.SetScale3D(Scale);
                Placement.SetLocation(Site.Transform.TransformPosition(-Bounds.Origin*Scale));
                Fog->SetStaticMesh(Site.FogMesh.Get());Fog->SetWorldTransform(Placement);
                MID->SetScalarParameterValue(TEXT("FogOverallDensity"),0.f);
                Fog->SetVisibility(true);
            }
            else
            {
                FX->SetWorldTransform(Site.Transform);
                FX->SetAsset(Site.System.Get());FX->SetRandomSeedOffset(Site.Seed);
                FX->SetSystemFixedBounds(FBox(-Site.Extent-FVector(40),Site.Extent+FVector(40)));
                FX->SetVariableVec3(TEXT("User.Extent"),Site.Extent);
                FX->SetVariableLinearColor(TEXT("User.Tint"),Site.Tint);
                FX->SetVariableFloat(TEXT("User.Density"),Site.Density);
                FX->SetVariableFloat(TEXT("User.Phase"),float(Site.Seed%997)/997.f);
                FX->SetVariableFloat(TEXT("User.Visibility"),0.f);
                FX->SetVariableFloat(TEXT("User.SpawnRate"),0.f);
                FX->SetVisibility(true);FX->SetComponentTickEnabled(true);FX->Activate(true);
            }
            Slot.NextBudget=0;Slot.Alpha=0;
        }
        const auto& Site=Sites[Slot.Site];
        if(FX&&Now>=Slot.NextBudget)
        {
            // Reserve the next half-second of decorative emissions in the shared impact/FX budget.
            const int32 Request=FMath::Max(1,FMath::CeilToInt(Site.Rate*.5f));
            const int32 Allowed=Budget?Budget->AllocateDetail(Site.Transform.GetLocation(),Request,false):0;
            Slot.Detail=FMath::Clamp(float(Allowed)/Request,0.f,1.f);Slot.NextBudget=Now+.5;
        }
        float Distance=TNumericLimits<float>::Max();
        for(const FVector& Eye:Eyes)Distance=FMath::Min(Distance,float(FVector::Distance(Eye,Site.Transform.GetLocation())));
        const float Fade=FMath::Clamp((Site.Distance-Distance)/600.f,0.f,1.f);
        // Alpha stores the actual visible weight: leaving a distant site must not briefly brighten it.
        Slot.Alpha=FMath::FInterpConstantTo(Slot.Alpha,Fade,Delta,.8f);
        if(FX)
        {
            FX->SetVariableFloat(TEXT("User.Visibility"),Slot.Alpha);
            FX->SetVariableFloat(TEXT("User.SpawnRate"),Site.Rate*Slot.Detail*Fade);
        }
        else MID->SetScalarParameterValue(TEXT("FogOverallDensity"),Site.Density*Slot.Alpha);
    }
}
