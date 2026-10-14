#include "RootCrownRigPreview.h"
#include "RootCrownSlashTiming.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"

void ARootCrownRigPreview::UpdateSlashArc()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const float Age=SlashAge();
    const float Last=SlashFrames.IsEmpty()?0.f:FMath::Min(SlashFrames.Last().Time,RootCrownSlashTiming::ContactEnd);
    constexpr float Afterglow=.22f;
    const bool Live=IsSlashing()&&SlashArcMaterial&&SlashFrames.Num()>1
        &&Age>=RootCrownSlashTiming::ContactStart&&Age<Last+Afterglow;
    if(!Live)
    {
        if(SlashArc&&SlashArc->IsVisible())SlashArc->SetVisibility(false);
        return;
    }
    int32 Frame=INDEX_NONE;
    for(int32 I=1;I<SlashFrames.Num();++I)
        if(SlashFrames[I].Time>=RootCrownSlashTiming::ContactStart
            &&SlashFrames[I].Time<=FMath::Min(Age,Last)+.0001f)Frame=I;
    if(Frame==INDEX_NONE)return;
    if(SlashArcSerial!=SlashClock.Serial||SlashArcFrame!=Frame)
    {
        BuildSlashArc(Frame);SlashArcFrame=Frame;SlashArcSerial=SlashClock.Serial;
    }
    if(!SlashArcMID)return;
    // Same replicated attack clock as the damage. Fade freezes at the final
    // contact location; there is no travelling damage after the hit window.
    const float Fade=FMath::SmoothStep(RootCrownSlashTiming::ContactStart,RootCrownSlashTiming::ContactStart+.015f,Age)
        *(1.f-FMath::SmoothStep(Last,Last+Afterglow,Age));
    SlashArcMID->SetScalarParameterValue(TEXT("Opacity"),Fade);
    SlashArcMID->SetScalarParameterValue(TEXT("Seconds"),Age-RootCrownSlashTiming::ContactStart);
    SlashArc->SetVisibility(bSlashArcGeometry);
}

void ARootCrownRigPreview::BuildSlashArc(int32 FrameIndex)
{
    if(!SlashArc)
    {
        SlashArc=NewObject<UDynamicMeshComponent>(this,TEXT("CrownSlashWhiteArc"));
        SlashArc->SetCollisionEnabled(ECollisionEnabled::NoCollision);SlashArc->SetGenerateOverlapEvents(false);
        SlashArc->SetCanEverAffectNavigation(false);SlashArc->SetCastShadow(false);SlashArc->SetReceivesDecals(false);
        SlashArc->bAffectDistanceFieldLighting=false;SlashArc->SetVisibleInRayTracing(false);
        SlashArc->SetComponentTickEnabled(false);SlashArc->SetVisibility(false);
        AddInstanceComponent(SlashArc);SlashArc->RegisterComponent();
        SlashArcMID=UMaterialInstanceDynamic::Create(SlashArcMaterial,this);SlashArc->SetMaterial(0,SlashArcMID);
    }
    using namespace UE::Geometry;
    const auto& Frame=SlashFrames[FrameIndex];
    const int32 Count=FMath::Min(Frame.Points.Num(),32);
    const FVector Origin=GetActorLocation();
    const FTransform GroundedRoot=GetMesh()->GetSocketTransform(TEXT("Root"));
    const FVector Sight=GetNavAgentLocation()+FVector(0,0,100);
    const float Cone=FMath::Cos(FMath::DegreesToRadians(50.f));
    // 24 authored points normally: two endpoints per point, one small ribbon
    // per monster, rebuilt only when the 60 Hz contact sample changes.
    auto Visible=[&](const FVector& P)
    {
        const FVector Delta=P-Origin;
        if(Delta.Size2D()>SlashTriggerRange+70.f*SlashReachScale
            ||FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<Cone)return false;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownSlashArc),false,this);FHitResult Hit;
        // Bodies can be struck without cutting a hole in the glow. Re-query
        // beyond them so closed doors and walls still cut the visible arc.
        for(int32 Skip=0;Skip<8;++Skip)
        {
            if(!GetWorld()->LineTraceSingleByChannel(Hit,Sight,P,ECC_Visibility,Query))return true;
            AActor* Actor=Hit.GetActor();
            if(!Actor||(!Actor->IsA<APawn>()&&!Cast<APawn>(Actor->GetOwner())&&!Cast<APawn>(Actor->GetAttachParentActor())))return false;
            Query.AddIgnoredActor(Actor);
        }
        return false;
    };
    FDynamicMesh3 ArcGeometry;ArcGeometry.EnableAttributes();
    TArray<bool,TInlineAllocator<64>> Valid;Valid.SetNumZeroed(Count*2);
    for(int32 I=0;I<Count;++I)
    {
        // Exactly the same expanded centreline and sphere radius as the hit
        // sweeps. No separate circle radius or artist-estimated attack reach.
        const FVector P=SlashPointWorld(Frame.Points[I],true,GroundedRoot);
        const FVector Radial=(P-Origin).GetSafeNormal2D();
        for(int32 Side=0;Side<2;++Side)
        {
            const FVector Edge=P+Radial*(Side?SlashHitRadius:-SlashHitRadius);
            Valid[I*2+Side]=Visible(Edge);
            ArcGeometry.AppendVertex(FVector3d(Edge-Origin));
            ArcGeometry.Attributes()->PrimaryUV()->AppendElement(FVector2f(float(I)/FMath::Max(1,Count-1),float(Side)));
            ArcGeometry.Attributes()->PrimaryNormals()->AppendElement(FVector3f(0,0,1));
        }
    }
    auto Triangle=[&](int32 A,int32 B,int32 C)
    {
        if(!Valid[A]||!Valid[B]||!Valid[C])return;
        const FIndex3i Indices(A,B,C);const int32 T=ArcGeometry.AppendTriangle(Indices);
        if(T>=0)
        {
            ArcGeometry.Attributes()->PrimaryUV()->SetTriangle(T,Indices);
            ArcGeometry.Attributes()->PrimaryNormals()->SetTriangle(T,Indices);
        }
    };
    for(int32 I=1;I<Count;++I)
    {
        const int32 A=(I-1)*2,B=I*2;
        Triangle(A,B,B+1);Triangle(A,B+1,A+1);
    }
    bSlashArcGeometry=ArcGeometry.TriangleCount()>0;
    SlashArc->SetWorldTransform(FTransform(FQuat::Identity,Origin,FVector::OneVector));
    SlashArc->SetMesh(MoveTemp(ArcGeometry));
}
