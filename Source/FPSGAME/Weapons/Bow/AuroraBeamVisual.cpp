#include "AuroraBeamVisual.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInterface.h"

namespace
{
constexpr double SamplePeriod=.020;
constexpr double CoreSeconds=.075;
constexpr double TrailSeconds=.38;
constexpr double MaxLife=.55;
constexpr int32 TrailMoteLimit=384;
// One shared rain batch supports 32 contacts plus the guiding pulse.
constexpr int32 MoteLimit=TrailMoteLimit+32*14+40;
}

double AuroraBeamVisual::Clock(const UWorld* World)
{
    const auto* State=World->GetGameState();
    return State?State->GetServerWorldTimeSeconds():World->GetTimeSeconds();
}

AAuroraBeamVisual::AAuroraBeamVisual()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Origin")));
    Beams=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("LightPaths"));
    Sparks=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("LightParticles"));
    for(auto* Mesh:{Beams.Get(),Sparks.Get()})
    {
        Mesh->SetupAttachment(GetRootComponent());
        Mesh->SetNumCustomDataFloats(4);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetGenerateOverlapEvents(false);
        Mesh->SetCanEverAffectNavigation(false);
        Mesh->SetCastShadow(false);
        Mesh->SetVisibleInRayTracing(false);
        Mesh->SetReceivesDecals(false);
    }
}

AAuroraBeamVisual* AAuroraBeamVisual::Open(AActor* Source,const FVector& Origin)
{
    if(!Source||Source->GetNetMode()==NM_DedicatedServer)return nullptr;
    FActorSpawnParameters Params;
    Params.Owner=Source;
    Params.ObjectFlags|=RF_Transient;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* FX=Source->GetWorld()->SpawnActor<AAuroraBeamVisual>(Origin,FRotator::ZeroRotator,Params);
    if(FX)
    {
        FX->Random.Initialize(FMath::Rand());
        FX->AddTickPrerequisiteActor(Source);
        FX->PrepareMeshes();
    }
    return FX;
}

void AAuroraBeamVisual::PrepareMeshes()
{
    using namespace AuroraBeamVisual;
    const TArray<FSoftObjectPath> Paths{FSoftObjectPath(Cylinder),FSoftObjectPath(Sphere),FSoftObjectPath(MaterialPath)};
    auto Bind=[this,Paths]()
    {
        auto* Material=Cast<UMaterialInterface>(Paths[2].ResolveObject());
        if(!Material)return;
        Beams->SetMaterial(0,Material);Sparks->SetMaterial(0,Material);
        Beams->SetStaticMesh(Cast<UStaticMesh>(Paths[0].ResolveObject()));
        Sparks->SetStaticMesh(Cast<UStaticMesh>(Paths[1].ResolveObject()));
    };
    if(Paths[0].ResolveObject()&&Paths[1].ResolveObject()&&Paths[2].ResolveObject())Bind();
    else Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,Bind));
}

void AAuroraBeamVisual::AddMote(const FVector& Point,const FVector& Direction,double At,float Scale,bool bImpact)
{
    if(Motes.Num()>=(bImpact?MoteLimit:TrailMoteLimit))return;
    const float Speed=bImpact?Random.FRandRange(180.f,430.f):Random.FRandRange(16.f,55.f);
    const float Size=Scale*Random.FRandRange(.8f,2.0f);
    Motes.Add({Point,Direction*Speed,At,float(Random.FRandRange(.24f,float(MaxLife))),Size});
}

void AAuroraBeamVisual::Trace(int32 Lane,const FVector& Origin,double Started,const FVector& Tip,double At,float Scale)
{
    if(bReleased)return;
    auto& Stroke=Strokes.FindOrAdd(Lane);
    if(Stroke.bClosed)return;
    if(Stroke.Knots.IsEmpty())
    {
        // A newly relevant remote shot reconstructs only the still-visible part.
        const double Start=FMath::Clamp(Started,At-TrailSeconds,At);
        const double Alpha=At>Started?(Start-Started)/(At-Started):0.;
        Stroke.Tip={FMath::Lerp(Origin,Tip,Alpha),Start};
        Stroke.Knots.Add(Stroke.Tip);
        Stroke.Scale=Scale;
        Stroke.ToNextMote=12.;
    }
    const FKnot Prev=Stroke.Tip;
    if(At<Prev.At||Prev.Point.Equals(Tip,.02))return;
    const FVector Path=Tip-Prev.Point;
    const double Elapsed=At-Prev.At;
    const double Length=Path.Size();
    const FVector Axis=Path/Length;
    double Sample=Stroke.Knots.Last().At+SamplePeriod;
    Sample=FMath::Max(Sample,At-TrailSeconds);
    for(;Sample<=At&&Elapsed>0.;Sample+=SamplePeriod)
        Stroke.Knots.Add({FMath::Lerp(Prev.Point,Tip,FMath::Clamp((Sample-Prev.At)/Elapsed,0.,1.)),Sample});

    const double Spacing=Scale<1.f?155.:95.;
    const double LatestStart=Elapsed>MaxLife?Length*(1.-MaxLife/Elapsed):0.;
    double Distance=Stroke.ToNextMote;
    if(Distance<LatestStart)Distance+=FMath::CeilToDouble((LatestStart-Distance)/Spacing)*Spacing;
    for(;Distance<=Length;Distance+=Spacing)
    {
        const FVector Out=FVector::VectorPlaneProject(Random.VRand(),Axis).GetSafeNormal();
        AddMote(Prev.Point+Axis*Distance,Out-Axis*.12,Prev.At+Elapsed*Distance/Length,Scale,false);
    }
    Stroke.ToNextMote=Distance-Length;
    Stroke.Tip={Tip,At};
}

void AAuroraBeamVisual::Finish(int32 Lane,const FVector& Origin,double Started,const FAuroraBeamContact& Contact,float Scale)
{
    if(Contact.At<0.||AuroraBeamVisual::Clock(GetWorld())-Contact.At>MaxLife)return;
    // A contact can arrive after a newer movement packet. Trim the provisional
    // tail to the authority's timestamp before committing the actual endpoint.
    if(auto* Previous=Strokes.Find(Lane);Previous&&!Previous->bClosed&&Previous->Tip.At>Contact.At)
    {
        while(Previous->Knots.Num()&&Previous->Knots.Last().At>=Contact.At)Previous->Knots.Pop(EAllowShrinking::No);
        if(Previous->Knots.Num())Previous->Tip=Previous->Knots.Last();
    }
    Trace(Lane,Origin,Started,Contact.Point,Contact.At,Scale);
    auto* Stroke=Strokes.Find(Lane);
    if(!Stroke||Stroke->bClosed)return;
    Stroke->bClosed=true;
    Burst(Contact,Scale);
}

void AAuroraBeamVisual::Burst(const FAuroraBeamContact& Contact,float Scale)
{
    const FVector Normal=FVector(Contact.Normal).GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector);
    for(int32 I=0;I<(Scale<1.f?14:40);++I)
    {
        FVector Scatter=Random.VRand();
        if(FVector::DotProduct(Scatter,Normal)<0.)Scatter=-Scatter;
        AddMote(Contact.Point,(Scatter+Normal*.3).GetSafeNormal(),Contact.At,Scale,true);
    }
}

void AAuroraBeamVisual::Release()
{
    bReleased=true;
    for(auto& Pair:Strokes)Pair.Value.bClosed=true;
}

void AAuroraBeamVisual::FBatch::Put(const FTransform& Transform,const FVector2f& Tail,const FVector2f& Tip)
{
    Transforms.Add(Transform);
    Values.Append({Tail.X,Tail.Y,Tip.X,Tip.Y});
}

void AAuroraBeamVisual::FBatch::Flush(UInstancedStaticMeshComponent* Mesh)
{
    const int32 Count=Transforms.Num();
    if(Mesh->GetStaticMesh()&&(Visible||Count))
    {
        for(int32 I=Mesh->GetInstanceCount();I<Count;++I)Mesh->AddInstance(Transforms[I]);
        if(Count)Mesh->BatchUpdateInstancesTransforms(0,Transforms,false,false,true);
        // Clear the unused tail of last frame's pool in the same contiguous write.
        if(Visible>Count)Values.AddZeroed((Visible-Count)*4);
        Mesh->SetCustomData(0,FMath::Max(Visible,Count)-1,Values,false);
        Visible=Count;
    }
    Transforms.Reset();Values.Reset();
}

void AAuroraBeamVisual::DrawSegment(const FKnot& A,const FKnot& B,double Now,float Scale)
{
    if(A.At>Now||B.At<Now-TrailSeconds)return;
    const double Span=B.At-A.At;
    const FVector From=Span>0.?FMath::Lerp(A.Point,B.Point,FMath::Clamp((Now-TrailSeconds-A.At)/Span,0.,1.)):A.Point;
    const FVector To=Span>0.?FMath::Lerp(A.Point,B.Point,FMath::Clamp((Now-A.At)/Span,0.,1.)):B.Point;
    const FVector Axis=To-From;
    const double Length=Axis.Size();
    if(Length<.05)return;
    auto Light=[Now](double At)
    {
        const float Age=FMath::Max(0.,Now-At);
        const float Heat=1.f-FMath::SmoothStep(.012f,float(CoreSeconds),Age);
        const float Glow=1.f-FMath::SmoothStep(.025f,float(TrailSeconds),Age);
        return FVector2f(Glow*(.40f+.58f*Heat),Heat);
    };
    const FVector2f Tail=Light(FMath::Max(A.At,Now-TrailSeconds)), Tip=Light(FMath::Min(B.At,Now));
    const float Radius=Scale*(2.2f+1.8f*(Tail.X+Tip.X)*.5f);
    const FQuat Rotation=FRotationMatrix::MakeFromZ(Axis/Length).ToQuat();
    Lines.Put(FTransform(Rotation,(From+To)*.5-GetActorLocation(),FVector(Radius/50.,Radius/50.,Length/100.)),Tail,Tip);
}

void AAuroraBeamVisual::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!IsValid(GetOwner())&&!bReleased)Release();
    const double Now=AuroraBeamVisual::Clock(GetWorld());
    bool Live=false;
    for(auto& Pair:Strokes)
    {
        auto& S=Pair.Value;
        // Render between received positions in multiplayer, with no extrapolation past contact.
        const double DrawAt=Now-((GetNetMode()==NM_Client&&!S.bClosed)?.035:0.);
        int32 Old=0;
        while(Old+1<S.Knots.Num()&&S.Knots[Old+1].At<DrawAt-TrailSeconds)++Old;
        if(Old)S.Knots.RemoveAt(0,Old,EAllowShrinking::No);
        for(int32 I=1;I<S.Knots.Num();++I)DrawSegment(S.Knots[I-1],S.Knots[I],DrawAt,S.Scale);
        if(S.Knots.Num())DrawSegment(S.Knots.Last(),S.Tip,DrawAt,S.Scale);
        if(!S.bClosed&&S.Tip.At>=DrawAt-.10)
        {
            FVector Front=S.Tip.Point;
            for(int32 I=S.Knots.Num()-1;I>=0;--I)
                if(S.Knots[I].At<=DrawAt)
                {
                    const FKnot& Next=S.Knots.IsValidIndex(I+1)?S.Knots[I+1]:S.Tip;
                    const double T=Next.At-S.Knots[I].At;
                    if(T>0.)Front=FMath::Lerp(S.Knots[I].Point,Next.Point,FMath::Clamp((DrawAt-S.Knots[I].At)/T,0.,1.));
                    break;
                }
            const FVector2f HeadLight(.94f,1.f);
            Points.Put(FTransform(FQuat::Identity,Front-GetActorLocation(),FVector(.062*S.Scale)),HeadLight,HeadLight);
        }
        Live|=!S.bClosed||Now-S.Tip.At<TrailSeconds;
    }
    for(int32 I=Motes.Num()-1;I>=0;--I)
    {
        const FMote& P=Motes[I];
        const float Age=FMath::Max(0.,Now-P.Born);
        if(Age>=P.Life){Motes.RemoveAtSwap(I,1,EAllowShrinking::No);continue;}
        const float Remaining=1.f-Age/P.Life;
        const FVector Position=P.Origin+P.Velocity*((1.f-FMath::Exp(-3.2f*Age))/3.2f)+FVector(0,0,-32.f*Age*Age);
        const FVector2f Light(Remaining*Remaining,.2f+.6f*Remaining);
        Points.Put(FTransform(FQuat::Identity,Position-GetActorLocation(),FVector(P.Size*(.45f+.55f*Remaining)/50.f)),Light,Light);
    }
    Lines.Flush(Beams);Points.Flush(Sparks);
    if(bReleased&&!Live&&Motes.IsEmpty())Destroy();
}

void AAuroraBeamVisual::EndPlay(const EEndPlayReason::Type Reason)
{
    if(Load)Load->CancelHandle();
    Super::EndPlay(Reason);
}
