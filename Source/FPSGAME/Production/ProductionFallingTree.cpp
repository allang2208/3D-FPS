#include "ProductionFallingTree.h"
#include "ProductionResource.h"
#include "ProductionHarvestAssets.h"
#include "ProductionHarvestSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

AProductionFallingTree::AProductionFallingTree()
{
    PrimaryActorTick.bCanEverTick=true;
    Tree=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("FallingTree"));
    RootComponent=Tree;Tree->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Tree->SetCanEverAffectNavigation(false);Tree->SetComponentTickEnabled(false);
    CutCap=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FreshCut"));
    CutCap->SetupAttachment(Tree);CutCap->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CutCap->SetCanEverAffectNavigation(false);
}
void AProductionFallingTree::InitializeFall(const FProductionResource& Resource,const FVector& Direction)
{
    FProductionResource Target=Resource;Target.Direction=Direction;
    Plan=FProductionTreeFallPlan::Make(Target);
    Tree->SetSkeletalMesh(Cast<USkeletalMesh>(Resource.Mesh.ResolveObject()));
    Tree->SetBoundsScale(1.15f);
    SetActorTransform(Resource.Transform);InitialRotation=Resource.Transform.GetRotation();
    Scale=Resource.Transform.GetScale3D();EffectSeed=Resource.Seed;
    LocalFallDirection=InitialRotation.UnrotateVector(Plan.Direction);
    for(int32 Index=0;Index<Tree->GetNumMaterials();++Index)
        if(auto* Source=Cast<UMaterialInterface>(ProductionHarvestAssets::FallingMaterial(Index).ResolveObject()))
        {
            auto* MID=UMaterialInstanceDynamic::Create(Source,this);
            MID->SetScalarParameterValue(TEXT("HarvestCutHeight"),Plan.CutHeight);
            MID->SetScalarParameterValue(TEXT("HarvestTreeHeight"),Plan.LocalHeight);
            Tree->SetMaterial(Index,MID);Materials.Add(MID);
        }
    CutCap->SetStaticMesh(Cast<UStaticMesh>(ProductionHarvestAssets::CutCap(ProductionHarvestAssets::TreeVariant(Resource.Mesh)).ResolveObject()));
    CutCap->SetRelativeLocation(FVector(0,0,Plan.CutHeight));
    if(auto* Source=CutCap->GetMaterial(0))
    {
        auto* MID=UMaterialInstanceDynamic::Create(Source,this);CutCap->SetMaterial(0,MID);Materials.Add(MID);
    }
    if(auto* Sound=Cast<USoundBase>(ProductionHarvestAssets::TreeSound(false).ResolveObject()))
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Plan.Pivot,.7f,.94f+(EffectSeed%13)*.01f);
    SetLifeSpan(Plan.ReleaseSeconds()+Plan.FadeSeconds+.1f);
}
void AProductionFallingTree::Tick(float Delta)
{
    Super::Tick(Delta);Elapsed+=Delta;
    const float FallTime=Elapsed-Plan.AnticipationSeconds;
    float Angle=0;
    if(FallTime<0)
    {
        const float T=Elapsed/Plan.AnticipationSeconds;
        Angle=1.2f*T*T*(3-2*T)+.22f*FMath::Sin(T*2*PI)*(1-T);
    }
    else
    {
        const float T=FMath::Clamp(FallTime/Plan.FallSeconds,0.f,1.f);
        Angle=FMath::Lerp(1.2f,Plan.LandingAngle,FMath::Pow(T,1.9f));
        if(T>=1)
        {
            const float ContactAge=FallTime-Plan.FallSeconds;
            Angle-=2.2f*FMath::Exp(-5.f*ContactAge)*FMath::Abs(FMath::Sin(10.f*ContactAge));
        }
    }
    const FQuat Rotation=FQuat(Plan.Axis,FMath::DegreesToRadians(Angle))*InitialRotation;
    SetActorLocationAndRotation(Plan.Pivot-Rotation.RotateVector(FVector(0,0,Plan.CutHeight)*Scale),Rotation);
    const float Speed=(Angle-PreviousAngle)/FMath::Max(Delta,.001f);PreviousAngle=Angle;
    const float ContactAge=FallTime-Plan.FallSeconds;
    const float TargetBend=ContactAge>=0?45.f*FMath::Exp(-4.f*ContactAge)*FMath::Sin(11.f*ContactAge):-FMath::Min(55.f,Speed*.5f);
    CrownBend=FMath::FInterpTo(CrownBend,TargetBend,Delta,7.f);
    const float Fade=1-FMath::Clamp((Elapsed-Plan.ReleaseSeconds())/Plan.FadeSeconds,0.f,1.f);
    const FVector Bend=LocalFallDirection*CrownBend;
    for(auto& MID:Materials)
    {
        MID->SetVectorParameterValue(TEXT("HarvestCrownBend"),FLinearColor(Bend.X,Bend.Y,Bend.Z,0));
        MID->SetScalarParameterValue(TEXT("HarvestFade"),Fade);
    }
    auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
    if(!CrownTouched&&Angle>=Plan.CrownAngle)
    {CrownTouched=true;if(Harvest)Harvest->Burst(true,Plan.CrownContact,EffectSeed,true);}
    if(!Landed&&ContactAge>=0)
    {
        Landed=true;
        if(Harvest)Harvest->Burst(true,Plan.TrunkContact,EffectSeed+1,true);
        if(auto* Sound=Cast<USoundBase>(ProductionHarvestAssets::TreeSound(true).ResolveObject()))
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Plan.TrunkContact,.9f,.92f+(EffectSeed%15)*.01f);
    }
    CutCap->SetVisibility(Fade>0);
    if(Fade<=0){Tree->SetVisibility(false,true);SetActorTickEnabled(false);}
}
