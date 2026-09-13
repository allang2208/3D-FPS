#include "VoxelBuildGrounding.h"
#include "VoxelBuildWorld.h"
#include "VoxelCollapseFragment.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"

bool VoxelGrounding::FFootprint::Contains(const UPrimitiveComponent* Component) const
{
    for(const auto& Surface:Surfaces)if(Surface.Get()==Component)return true;
    return false;
}

FCollisionQueryParams VoxelGrounding::Query(UWorld* World,const AActor* Ignore)
{
    FCollisionQueryParams Params(SCENE_QUERY_STAT(VoxelGrounding),true,Ignore);
    for(TActorIterator<APawn> It(World);It;++It)Params.AddIgnoredActor(*It);
    return Params;
}

bool VoxelGrounding::IsSurface(const FHitResult& Hit)
{
    const auto* Component=Hit.GetComponent();
    return Hit.bBlockingHit&&Component&&Hit.ImpactNormal.Z>=MinimumNormalZ
        &&!Component->IsSimulatingPhysics()&&!Cast<APawn>(Hit.GetActor())
        &&!Cast<AVoxelBuildWorld>(Hit.GetActor())&&!Cast<AVoxelCollapseFragment>(Hit.GetActor());
}

bool VoxelGrounding::Sample(UWorld* World,FVector Min,double Top,double Bottom,
    const FCollisionQueryParams& Params,FFootprint& Out,const FHitResult* Reference)
{
    Out=FFootprint();
    const FVector2D Samples[]={{.5,.5},{19.5,.5},{.5,19.5},{19.5,19.5},{10,10}};
    for(const auto& Offset:Samples)
    {
        const FVector Foot=Min+FVector(Offset.X,Offset.Y,0);FHitResult Ground;
        if(!World->LineTraceSingleByChannel(Ground,FVector(Foot.X,Foot.Y,Top),FVector(Foot.X,Foot.Y,Bottom),ECC_Visibility,Params)
            ||!IsSurface(Ground))return false;
        // Do not jump from an aimed floor onto a different floor/overhang
        // found by a vertical probe. A 45-degree surface has this height bound.
        if(Reference&&FMath::Abs(Ground.ImpactPoint.Z-Reference->ImpactPoint.Z)>
            FVector::Dist2D(Ground.ImpactPoint,Reference->ImpactPoint)+1.)return false;
        Out.Low=FMath::Min(Out.Low,Ground.ImpactPoint.Z);Out.High=FMath::Max(Out.High,Ground.ImpactPoint.Z);
        Out.Surfaces.AddUnique(Ground.GetComponent());
    }
    return true;
}

bool AVoxelBuildWorld::ResolveGroundPlacement(const FHitResult& Surface,FIntVector Size,bool bSnap,
    FVector& Origin,TArray<FIntVector>& Positions,FString& Reason) const
{
    using namespace VoxelGrounding;
    FIntVector Base=ToCell(Surface.ImpactPoint);Base.X-=Size.X/2;Base.Y-=Size.Y/2;
    Origin=bSnap?FVector::ZeroVector:Surface.ImpactPoint-FVector(Size.X*10,Size.Y*10,0);
    if(!bSnap)Base=FIntVector::ZeroValue;
    auto Fill=[&]()
    {
        Positions.Reset();
        for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
            Positions.Add(Base+FIntVector(X,Y,Z));
    };
    Fill(); // Keep a red, non-committable brush visible on invalid terrain.
    if(!IsSurface(Surface)){Reason=TEXT("需要稳定地面 · 坡度不能超过 45°");return false;}
    const auto Params=Query(GetWorld(),this);const FVector FootprintMin=Origin+CellMin(Base);
    TArray<FFootprint,TInlineAllocator<25>> Samples;
    double Highest=TNumericLimits<double>::Lowest();
    const double Range=(MaxFoundationLayers+1)*CellSizeCm;
    for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
    {
        FFootprint Foot;
        if(!Sample(GetWorld(),FootprintMin+FVector(X*20,Y*20,0),Surface.ImpactPoint.Z+Range,
            Surface.ImpactPoint.Z-Range,Params,Foot,&Surface)||Foot.High-Foot.Low>18.)
        {Reason=TEXT("地面有陡坡、断崖或障碍 · 请换到更平缓的位置");return false;}
        Highest=FMath::Max(Highest,Foot.High);Samples.Add(MoveTemp(Foot));
    }
    // The visible brush stays level and entirely above its highest ground
    // sample. Only the explicitly previewed foundation enters the terrain.
    if(bSnap)Base.Z=FMath::CeilToInt(Highest/CellSizeCm);
    else Origin.Z=Highest;
    Fill();
    const double BaseHeight=Origin.Z+Base.Z*CellSizeCm;
    TArray<FIntVector> Foundations;int32 Deepest=0;
    for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
    {
        const int32 Bottom=FMath::Min(0,FMath::FloorToInt((Samples[X+Y*Size.X].Low+ContactToleranceCm-BaseHeight)/CellSizeCm));
        if(Bottom < -MaxFoundationLayers)
        {Reason=TEXT("地基需要超过 1.2 米 · 请分级搭建或换到更平缓的位置");return false;}
        Deepest=FMath::Max(Deepest,-Bottom);
        for(int32 Z=-1;Z>=Bottom;--Z)Foundations.Add(Base+FIntVector(X,Y,Z));
    }
    Positions.Append(Foundations);
    Reason=Foundations.IsEmpty()?TEXT("水平贴地"):FString::Printf(TEXT("水平贴地 · 地基 %d 格 · 最深 %d cm"),Foundations.Num(),Deepest*CellSizeCm);
    return true;
}

bool AVoxelBuildWorld::IsGroundAnchor(FVector Min) const
{
    VoxelGrounding::FFootprint Ground;
    return VoxelGrounding::Sample(GetWorld(),Min,Min.Z+VoxelGrounding::AnchorProbeRiseCm,
        Min.Z-VoxelGrounding::ContactToleranceCm,VoxelGrounding::Query(GetWorld(),this),Ground);
}

bool AVoxelBuildWorld::ScenePlacementAllowed(FVector Min,FString& Reason,bool* OutAnchor) const
{
    const FVector Center=Min+FVector(10);const FBox Box(Min+FVector(.25),Min+FVector(19.75));
    if(OutAnchor)*OutAnchor=false;
    for(TActorIterator<ACharacter> It(GetWorld());It;++It)
        if(auto* Capsule=It->GetCapsuleComponent();Capsule&&Capsule->IsCollisionEnabled()&&Box.Intersect(Capsule->Bounds.GetBox()))
        {Reason=TEXT("位置被角色占用");return false;}
    const auto Params=VoxelGrounding::Query(GetWorld(),this);VoxelGrounding::FFootprint Ground;
    // A slope may cross an upper foundation cell without supporting every
    // corner of that cell. Permit that terrain intersection, but only mark
    // the fully seated bottom cell as a structural anchor.
    const bool HasGround=VoxelGrounding::Sample(GetWorld(),Min,Min.Z+VoxelGrounding::AnchorProbeRiseCm,
        Min.Z-CellSizeCm-VoxelGrounding::ContactToleranceCm,Params,Ground);
    const bool Anchored=HasGround&&Ground.Low>=Min.Z-VoxelGrounding::ContactToleranceCm;
    if(OutAnchor)*OutAnchor=Anchored;
    for(const FVector Axis:{FVector(1,0,0),FVector(0,1,0),FVector(0,0,1)})
    {
        FHitResult Obstacle;
        if(GetWorld()->LineTraceSingleByChannel(Obstacle,Center-Axis*8,Center+Axis*8,ECC_Visibility,Params)
            &&!(HasGround&&Ground.Contains(Obstacle.GetComponent())
                &&Obstacle.ImpactPoint.Z>=Ground.Low-VoxelGrounding::ContactToleranceCm
                &&Obstacle.ImpactPoint.Z<=Ground.High+VoxelGrounding::ContactToleranceCm))
        {Reason=TEXT("位置与场景障碍重叠");return false;}
    }
    return true;
}
