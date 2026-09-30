#include "FluidPresentationSubsystem.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/SmeltingSystem.h"
#include "../Production/ProductionHarvestAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Scalability.h"

namespace FurnaceCasting
{
    constexpr double PourSeconds=3.2;
    constexpr double ArrivalSeconds=.4776727;
    constexpr double SolidSeconds=5.4;
    constexpr int32 MaxCasting=4;
    constexpr int32 MaxIngots=32;

    UStaticMeshComponent* NewSurface(UWorld* World)
    {
        auto* Owner=World->GetWorldSettings();
        auto* Comp=NewObject<UStaticMeshComponent>(Owner,NAME_None,RF_Transient);
        Owner->AddInstanceComponent(Comp);
        Comp->SetMobility(EComponentMobility::Movable);
        Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Comp->SetGenerateOverlapEvents(false);
        Comp->SetCanEverAffectNavigation(false);
        Comp->SetCastShadow(false);
        Comp->SetVisibility(false);
        Comp->SetCullDistance(8500.f);
        Comp->RegisterComponent();
        return Comp;
    }
}

void UFluidPresentationSubsystem::ReleaseFurnaceTap(FFurnaceSmoke& Entry)
{
    if(auto* FX=Entry.TapFX.Get())
    {
        FX->SetVariableFloat(TEXT("User.Flow"),0.f);
        FX->DeactivateImmediate();
        FX->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    }
    // Return the borrower's pointer as well: stale entries must not control another furnace.
    Entry.TapFX.Reset();
    if(auto* Comp=Entry.CastingMesh.Get())
    {
        Comp->SetVisibility(false);
        Comp->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    }
    Entry.CastingMesh.Reset();
}

void UFluidPresentationSubsystem::ReleaseFurnaceIngot(FFurnaceSmoke& Entry)
{
    if(auto* Comp=Entry.Ingot.Get())
    {
        Comp->SetVisibility(false);
        Comp->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    }
    Entry.Ingot.Reset();Entry.IngotDef.Empty();
}

void UFluidPresentationSubsystem::UpdateFurnaceTap(FFurnaceSmoke& Entry,AVoxelBuildWorld* Build,
    const FVoxelSmeltingJob* Job,const UStaticMeshComponent* Body,const FVector& Mouth,bool bDone,double Now)
{
    // Cosmetic only. SmeltingSystem continues to own completion, inventory, fuel and saves.
    auto* Piece=Entry.Piece.Get();
    UpdateCastingRack(Entry,Build,Job);
    const bool bBuffered=Job&&Job->bCasting;
    double BufferedAge=0,TimeRate=1;
    if(bBuffered)
    {
        auto* Smelt=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
        const auto* Recipe=Smelt?Smelt->Find(Job->Recipe):nullptr;
        if(Recipe&&Build)
        {
            const double Unit=Smelt->JobTotalSeconds(Build,*Job,*Recipe)/FMath::Max<int64>(1,Job->BatchCount);
            const double Progress=Smelt->Progress(Build,Job->Cell)*Smelt->JobTotalSeconds(Build,*Job,*Recipe);
            BufferedAge=FMath::Clamp((Progress-Job->ProducedBatches*Unit)/Unit,0.,1.)*FurnaceCasting::SolidSeconds;
            TimeRate=Smelt->IsBurning(Build,Job->Cell)&&!Smelt->CastingBlocked(Build,*Job)?FurnaceCasting::SolidSeconds/Unit:0;
            bDone=BufferedAge>0||TimeRate>0;
        }
        else bDone=false;
        ReleaseFurnaceIngot(Entry);
    }
    if(!Piece||!Body||!Body->IsRegistered()||Piece->IsFalling())bDone=false;
    if(!bDone)
    {
        ReleaseFurnaceTap(Entry);ReleaseFurnaceIngot(Entry);
        Entry.bWasDone=false;Entry.TapAt=-1;
        return;
    }
    if(!Entry.bWasDone){Entry.TapAt=Now;Entry.bWasDone=true;}
    const double Elapsed=bBuffered?BufferedAge:FMath::Max(0.,Now-Entry.TapAt);
    const float Distance=bHasView?float(FVector::Distance(Mouth,Eye)):TNumericLimits<float>::Max();
    if(Distance>8500.f)
    {
        ReleaseFurnaceTap(Entry);ReleaseFurnaceIngot(Entry);
        return; // Retain the clock: returning does not replay a completed pour.
    }
    auto* Parent=const_cast<UStaticMeshComponent*>(Body);
    if(Elapsed<FurnaceCasting::SolidSeconds&&!Entry.CastingMesh.IsValid())
    {
        auto* Mesh=CastingTemplate.Get();
        if(Mesh)
        {
            UStaticMeshComponent* Free=nullptr;
            for(auto& Candidate:CastingPool)
            {
                if(!IsValid(Candidate))continue;
                bool Taken=false;
                for(const auto& Other:Furnaces)if(Other.CastingMesh.Get()==Candidate.Get()){Taken=true;break;}
                if(!Taken){Free=Candidate.Get();break;}
            }
            if(!Free&&CastingPool.Num()<FurnaceCasting::MaxCasting)
            {Free=FurnaceCasting::NewSurface(GetWorld());CastingPool.Add(Free);}
            if(Free)
            {
                Free->SetStaticMesh(Mesh);
                Free->EmptyOverrideMaterials();
                Free->AttachToComponent(Parent,FAttachmentTransformRules::SnapToTargetIncludingScale);
                Free->SetRelativeTransform(FTransform::Identity);
                Free->SetCustomPrimitiveDataFloat(0,float(Entry.TapAt));
                Free->SetCustomPrimitiveDataFloat(1,float(GetTypeHash(Piece->AnchorCell())%4096)/4096.f);
                Free->SetCustomPrimitiveDataFloat(2,1.f);
                Free->SetCustomPrimitiveDataFloat(3,0.f);
                Free->SetVisibility(true);Entry.CastingMesh=Free;
            }
        } // Retry asynchronous readiness within the original time window.
    }
    if(bBuffered)if(auto* Surface=Entry.CastingMesh.Get())
    {
        static const FSoftObjectPath Stream(TEXT("/Game/Fluids/FurnaceCasting20260926/M_CastingStreamBuffered.M_CastingStreamBuffered"));
        static const FSoftObjectPath Pool(TEXT("/Game/Fluids/FurnaceCasting20260926/M_CastingPoolBuffered.M_CastingPoolBuffered"));
        if(auto* Mat=Cast<UMaterialInterface>(Stream.ResolveObject()))Surface->SetMaterialByName(TEXT("CastingStream"),Mat);
        if(auto* Mat=Cast<UMaterialInterface>(Pool.ResolveObject()))Surface->SetMaterialByName(TEXT("CastingPool"),Mat);
        Surface->SetCustomPrimitiveDataFloat(0,float(Now));
        Surface->SetCustomPrimitiveDataFloat(2,float(TimeRate));
        Surface->SetCustomPrimitiveDataFloat(3,float(Elapsed));
    }
    // Decorative droplets start at actual impact; their budget cannot erase the liquid.
    const bool bDroplets=Entry.CastingMesh.IsValid()&&Elapsed>=FurnaceCasting::ArrivalSeconds
        &&Elapsed<FurnaceCasting::PourSeconds+FurnaceCasting::ArrivalSeconds
        &&(!bBuffered||TimeRate>0)&&Distance<=3500.f&&Scalability::GetQualityLevels().EffectsQuality>=1;
    const float Fill=FMath::Clamp(float((Elapsed-FurnaceCasting::ArrivalSeconds)/(FurnaceCasting::PourSeconds-FurnaceCasting::ArrivalSeconds)),0.f,1.f);
    const float ImpactHeight=22.4f+3.8f*Fill*Fill*(3.f-2.f*Fill);
    if(bDroplets&&!Entry.TapFX.IsValid()&&TapAsset)
    {
        UNiagaraComponent* Free=nullptr;
        for(auto& Candidate:TapPool)
        {
            if(!IsValid(Candidate))continue;
            bool Taken=false;
            for(const auto& Other:Furnaces)if(Other.TapFX.Get()==Candidate.Get()){Taken=true;break;}
            if(!Taken){Free=Candidate.Get();break;}
        }
        if(!Free&&TapPool.Num()<FurnaceCasting::MaxCasting)
        {
            auto* Owner=GetWorld()->GetWorldSettings();
            Free=NewObject<UNiagaraComponent>(Owner,NAME_None,RF_Transient);
            Owner->AddInstanceComponent(Free);
            Free->SetAutoActivate(false);Free->SetAutoDestroy(false);Free->SetAsset(TapAsset);
            Free->SetCastShadow(false);Free->SetCanEverAffectNavigation(false);Free->RegisterComponent();
            TapPool.Add(Free);
        }
        if(Free)
        {
            Free->AttachToComponent(Parent,FAttachmentTransformRules::SnapToTargetIncludingScale);
            Free->SetRelativeTransform(FTransform::Identity);
            Free->SetVariableFloat(TEXT("User.Flow"),1.f);
            Free->SetVariableFloat(TEXT("User.SparkGate"),1.f);
            Free->SetVariableFloat(TEXT("User.ImpactHeight"),ImpactHeight);
            Free->SetVariableFloat(TEXT("User.DetailReduction"),1.f-float(AllocateDetail(Mouth,12,false))/12.f);
            Free->Activate(true);Entry.TapFX=Free;
        }
    }
    if(auto* FX=Entry.TapFX.Get())
    {
        FX->SetVariableFloat(TEXT("User.Flow"),bDroplets?1.f:0.f);
        FX->SetVariableFloat(TEXT("User.ImpactHeight"),ImpactHeight);
    }
    if(Elapsed>=FurnaceCasting::SolidSeconds)ReleaseFurnaceTap(Entry);
    if(!bBuffered&&Elapsed>=FurnaceCasting::SolidSeconds&&!Entry.Ingot.IsValid())
    {
        auto* Smelt=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
        const FColdSteelSmeltingRecipe* Recipe=(Job&&Smelt)?Smelt->Find(Job->Recipe):nullptr;
        auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Items/Smelting/Ingot/SM_Ingot.SM_Ingot")).ResolveObject());
        auto* Material=Recipe?Cast<UMaterialInterface>(ProductionHarvestAssets::PickupMaterial(Recipe->Output).ResolveObject()):nullptr;
        if(Mesh&&Material)
        {
            UStaticMeshComponent* Free=nullptr;
            for(auto& Candidate:IngotPool)
            {
                if(!IsValid(Candidate))continue;
                bool Taken=false;
                for(const auto& Other:Furnaces)if(Other.Ingot.Get()==Candidate.Get()){Taken=true;break;}
                if(!Taken){Free=Candidate.Get();break;}
            }
            if(!Free&&IngotPool.Num()<FurnaceCasting::MaxIngots)
            {Free=FurnaceCasting::NewSurface(GetWorld());IngotPool.Add(Free);}
            if(Free)
            {
                Free->AttachToComponent(Parent,FAttachmentTransformRules::SnapToTargetIncludingScale);
                Free->SetStaticMesh(Mesh);Free->SetMaterial(0,Material);
                const auto Bounds=Mesh->GetBounds();
                const float Scale=14.8f/FMath::Max(1.f,2.f*float(FMath::Max(Bounds.BoxExtent.X,Bounds.BoxExtent.Y)));
                const FRotator Rotation(0,Bounds.BoxExtent.Y>Bounds.BoxExtent.X?90.f:0.f,0);
                const FVector CentreOffset=Rotation.RotateVector(Bounds.Origin*Scale);
                // Fit the 14.8 cm ingot inside the mould; use its true bottom and pivot.
                const FVector Centre(45,0,21.85+Bounds.BoxExtent.Z*Scale);
                Free->SetRelativeTransform(FTransform(Rotation,Centre-CentreOffset,FVector(Scale)));
                Free->SetVisibility(true);Entry.Ingot=Free;Entry.IngotDef=Recipe->Output;
            }
        }
    }
}
