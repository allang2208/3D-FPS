#include "HighVillageCollapse.h"
#include "VillageMasonry.h"
#include "VillageDefenseSection.h"
#include "VillageDefenseDebris.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"

namespace
{
    const FSoftObjectPath StoneDust(TEXT("/Game/EasyBuildingSystem/Effects/PS_Dust.PS_Dust"));
    const FSoftObjectPath GuideChip = VillageMasonry::Mesh(TEXT("SM_StoneChunkA"));
    FSoftObjectPath ShardPath(int32 Index)
    {
        const FString Name=FString::Printf(TEXT("SM_HighWallShard_%02d"),Index);
        return VillageMasonry::Mesh(Name);
    }
    constexpr int32 ShardCount=9;

    const TArray<FSoftObjectPath>& StairShardPaths()
    {
        // fracture_stairs.py writes the footing followed by the tread body of each bay.
        static const TArray<FSoftObjectPath> Paths=[]
        {
            TArray<FSoftObjectPath> Result;
            for(int32 Index=0;Index<18;++Index)
            {
                const FString Name=FString::Printf(TEXT("SM_StairShard_%02d"),Index);
                Result.Emplace(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/Fracture/")+Name+TEXT(".")+Name);
            }
            return Result;
        }();
        return Paths;
    }
}

AHighVillageCollapse::AHighVillageCollapse()
{
    PrimaryActorTick.bCanEverTick=true;
    SetReplicates(false);
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("CollapseOrigin"));
}

void AHighVillageCollapse::AddAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    Paths.AddUnique(StoneDust);
    Paths.AddUnique(GuideChip);
    for(int32 Index=0;Index<ShardCount;++Index)Paths.AddUnique(ShardPath(Index));
    for(const FSoftObjectPath& StairShard:StairShardPaths())Paths.AddUnique(StairShard);
}

AHighVillageCollapse* AHighVillageCollapse::Begin(AActor& Section)
{
    UWorld* World=Section.GetWorld();
    if(!World||World->GetNetMode()==NM_DedicatedServer)return nullptr;
    AHighVillageCollapse* Oldest=nullptr;
    int32 Count=0;
    for(TActorIterator<AHighVillageCollapse> It(World);It;++It)
    {
        ++Count;
        if(!Oldest||It->Age>Oldest->Age)Oldest=*It;
    }
    if(Count>=8 && Oldest)Oldest->Destroy();
    FActorSpawnParameters Args;
    Args.Owner=&Section;
    Args.ObjectFlags|=RF_Transient;
    Args.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Effect=World->SpawnActor<AHighVillageCollapse>(StaticClass(),Section.GetActorTransform(),Args);
    if(Effect)Effect->SetLifeSpan(9.f);
    return Effect;
}

void AHighVillageCollapse::Dust(FVector LocalPosition,float Scale)
{
    if(auto* System=Cast<UParticleSystem>(StoneDust.ResolveObject()))
        UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),System,GetActorTransform().TransformPosition(LocalPosition),
            FVector::UpVector.Rotation(),FVector(Scale),true,EPSCPoolMethod::AutoRelease);
}

void AHighVillageCollapse::AddFragment(UStaticMesh* Mesh,const FTransform& LocalPose,float ReleaseTime,
    const FVector& Velocity,const FVector& Spin)
{
    auto* Part=NewObject<UStaticMeshComponent>(this);
    AddInstanceComponent(Part);
    Part->SetupAttachment(RootComponent);
    Part->SetMobility(EComponentMobility::Movable);
    Part->SetStaticMesh(Mesh);
    Part->SetRelativeTransform(LocalPose);
    Part->SetCanEverAffectNavigation(false);
    Part->SetGenerateOverlapEvents(false);
    Part->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);
    Part->SetCollisionObjectType(ECC_PhysicsBody);
    Part->SetCollisionResponseToAllChannels(ECR_Ignore);
    Part->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
    Part->SetLinearDamping(.55f);
    Part->SetAngularDamping(.85f);
    Part->RegisterComponent();
    Rubble.Add(Part);
    ReleaseTimes.Add(ReleaseTime);
    LaunchSpeeds.Add(Velocity);
    AngularSpeeds.Add(Spin);
    FragmentScales.Add(Part->GetComponentScale());
}

void AHighVillageCollapse::Wall(AVillageDefenseSection& Section,const FVector& Direction,int32 Seed)
{
    auto* Effect=Begin(Section);
    if(!Effect)return;
    TArray<UStaticMesh*,TInlineAllocator<ShardCount>> Meshes;
    for(int32 Index=0;Index<ShardCount;++Index)
    {
        auto* Mesh=Cast<UStaticMesh>(ShardPath(Index).ResolveObject());
        if(!Mesh)
        {
            // An early hit on a streaming client still shows masonry breaking.
            const FVector Size=FVector(300,160,450)*Section.GetActorScale3D().GetAbs();
            const FTransform Pose(Section.GetActorRotation(),Section.GetActorLocation());
            AVillageDefenseDebris::Spawn(Section,Pose,Size,Direction,Seed,false);
            Effect->Dust(FVector(0,0,22),1.f);
            Effect->Destroy();
            return;
        }
        Meshes.Add(Mesh);
    }
    FRandomStream Noise(Seed);
    for(int32 Index=0;Index<ShardCount;++Index)
    {
        const int32 Row=Index/3;
        const float ReleaseTime=(2-Row)*.16f+Noise.FRandRange(.0f,.10f);
        const FVector Velocity=Direction*Noise.FRandRange(36.f,84.f)+Section.GetActorForwardVector()*Noise.FRandRange(-28.f,28.f)
            +FVector::UpVector*(Row==2?Noise.FRandRange(40.f,75.f):Noise.FRandRange(4.f,22.f));
        const FVector Spin(Noise.FRandRange(-62.f,62.f),Noise.FRandRange(-80.f,80.f),Noise.FRandRange(-28.f,28.f));
        Effect->AddFragment(Meshes[Index],FTransform::Identity,ReleaseTime,Velocity,Spin);
    }
    Effect->Dust(FVector(0,0,342),.55f);
}

void AHighVillageCollapse::Gate(AVillageDefenseSection& Section,const FVector& Direction,float StartHeight)
{
    auto* Effect=Begin(Section);
    if(!Effect)return;
    Effect->InitialLift=FMath::Max(0.f,StartHeight);
    Effect->TipSide=FVector::DotProduct(Direction,Section.GetActorRightVector())<0. ? -1.f : 1.f;
    auto* Copy=NewObject<UStaticMeshComponent>(Effect);
    Effect->AddInstanceComponent(Copy);
    Copy->SetupAttachment(Effect->RootComponent);
    Copy->SetMobility(EComponentMobility::Movable);
    Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Copy->SetCanEverAffectNavigation(false);
    Copy->SetGenerateOverlapEvents(false);
    Copy->RegisterComponent();
    Effect->Grille=Copy;
    Effect->AnimateGrille();
}

void AHighVillageCollapse::ReleaseGuideStones(const UStaticMesh& Mesh)
{
    // The iron runners tear stone out of the jambs before the gate hits the road.
    const double HalfSpan=Mesh.GetBoundingBox().GetExtent().X;
    auto* Stone=Cast<UStaticMesh>(GuideChip.ResolveObject());
    for(int32 Side:{-1,1})
    {
        const FVector Lip(Side*(HalfSpan-6.),TipSide*25.,333.);
        Dust(Lip,.42f);
        if(!Stone)continue;
        const FVector Size=Stone->GetBoundingBox().GetSize().ComponentMax(FVector(1.));
        for(int32 I=0;I<2;++I)
        {
            const FTransform Pose(FQuat::Identity,Lip+FVector(-Side*4.*I,0.,17.*I),FVector(13.+I*5.,11.,15.)/Size);
            const FVector Velocity=GetActorQuat().RotateVector(FVector(-Side*(51.+24.*I),TipSide*82.,26.));
            AddFragment(Stone,Pose,.04f+.07f*I,Velocity,FVector(49.*Side,83.,58.*I));
        }
    }
}

void AHighVillageCollapse::Stairs(AActor& Section,const FVector& Direction,int32 Seed)
{
    auto* Effect=Begin(Section);
    if(!Effect)return;
    Effect->bStairs=true;
    const TArray<FSoftObjectPath>& Paths=StairShardPaths();
    if(!Paths.ContainsByPredicate([](const FSoftObjectPath& Path){return Path.ResolveObject()==nullptr;}))
    {
        Effect->ReleaseStairBays(Direction,Seed);
        return;
    }

    // A newly connected client can see a breach before the village preload completes.
    // Keep the intact silhouette while loading the matching stones, even if the source is removed.
    static const FSoftObjectPath Intact(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SM_WallAccessStairs.SM_WallAccessStairs"));
    if(auto* Mesh=Cast<UStaticMesh>(Intact.ResolveObject()))
    {
        auto* Copy=NewObject<UStaticMeshComponent>(Effect);
        Effect->AddInstanceComponent(Copy);
        Copy->SetupAttachment(Effect->RootComponent);
        Copy->SetMobility(EComponentMobility::Movable);
        Copy->SetStaticMesh(Mesh);
        Copy->SetCanEverAffectNavigation(false);
        Copy->SetGenerateOverlapEvents(false);
        Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Copy->RegisterComponent();
        Effect->WaitingStair=Copy;
    }
    TArray<FSoftObjectPath> Needed=Paths;
    Needed.Add(StoneDust);
    UAssetManager::GetStreamableManager().RequestAsyncLoad(Needed,
        FStreamableDelegate::CreateWeakLambda(Effect,[Effect,Direction,Seed](){Effect->ReleaseStairBays(Direction,Seed);}));
}

void AHighVillageCollapse::ReleaseStairBays(const FVector& Direction,int32 Seed)
{
    const TArray<FSoftObjectPath>& Paths=StairShardPaths();
    TArray<UStaticMesh*,TInlineAllocator<18>> Meshes;
    TArray<FVector,TInlineAllocator<18>> Centers;
    for(const FSoftObjectPath& Path:Paths)
    {
        auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject());
        const UStaticMeshSocket* Origin=Mesh ? Mesh->FindSocket(TEXT("StairOrigin")) : nullptr;
        if(!Origin){Destroy();return;}
        Meshes.Add(Mesh);
        Centers.Add(-Origin->RelativeLocation);
    }
    if(WaitingStair){WaitingStair->DestroyComponent();WaitingStair=nullptr;}
    Age=0.f;
    SetLifeSpan(9.f);
    FRandomStream Noise(Seed);
    FVector Push=GetActorTransform().InverseTransformVectorNoScale(Direction).GetSafeNormal2D();
    if(Push.IsNearlyZero())
    {
        const float Angle=Noise.FRandRange(-PI,PI);
        Push=FVector(FMath::Cos(Angle),FMath::Sin(Angle),0.);
    }
    // Infer the incoming face from the attack direction, then fail the nearest footing first.
    const FVector AttackSide(-160.*Push.X,-280.*Push.Y,0.);
    int32 First=0;
    for(int32 I=2;I<Centers.Num();I+=2)
        if(FVector::DistSquared2D(Centers[I],AttackSide)<FVector::DistSquared2D(Centers[First],AttackSide))First=I;
    const FVector Strike=Centers[First];
    Dust(FVector(Strike.X,Strike.Y,FMath::Max(12.,Strike.Z)),.65f);
    for(int32 I=0;I<Meshes.Num();++I)
    {
        const bool Upper=(I%2)!=0;
        const FVector Base=Centers[I-(I%2)];
        const FVector Spread=(Base-Strike).GetSafeNormal2D();
        const float Delay=FVector::Dist2D(Base,Strike)/690.f + (Upper?.13f:0.f) + Noise.FRandRange(0.f,.055f);
        const float Kick=Upper ? Noise.FRandRange(28.f,65.f) : Noise.FRandRange(105.f,172.f);
        FVector LocalVelocity=Push*Kick+Spread*Noise.FRandRange(31.f,100.f);
        LocalVelocity.X+=FMath::Sign(Base.X)*Noise.FRandRange(28.f,72.f);
        LocalVelocity.Z=Upper ? Noise.FRandRange(-44.f,-12.f) : Noise.FRandRange(18.f,45.f);
        const FVector LocalSpin(Noise.FRandRange(-42.f,42.f),FMath::Sign(Base.X)*Noise.FRandRange(45.f,93.f),
            Noise.FRandRange(-25.f,25.f));
        AddFragment(Meshes[I],FTransform(Centers[I]),Delay,
            GetActorQuat().RotateVector(LocalVelocity),GetActorQuat().RotateVector(LocalSpin));
    }
}

void AHighVillageCollapse::AnimateGrille()
{
    const float DropTime=FMath::Sqrt(2.f*InitialLift/980.f);
    const float T=FMath::Max(0.f,Age-.10f);
    // Even a fully lowered grille tears outward from its guides and pivots about its foot.
    const float FallTime=FMath::Max(.76f,DropTime+.35f);
    if (!Grille->GetStaticMesh())
    {
        // The breach RPC can arrive while the section is still streaming its grille.
        // Join the ongoing fall at its current time and let a repair cancel it normally.
        const auto* Section=Cast<AVillageDefenseSection>(GetOwner());
        UStaticMesh* Mesh=Section ? Section->GetMasonry()->GetStaticMesh() : nullptr;
        if (!Mesh) return;
        Grille->SetStaticMesh(Mesh);
        if (T<=0.f) ReleaseGuideStones(*Mesh);
        bGroundImpact=T>FallTime;
    }
    const float Bottom=FMath::Max(0.f,InitialLift-490.f*T*T);
    const float Phase=FMath::Clamp(T/FallTime,0.f,1.f);
    const float Tip=87.f*Phase*Phase;
    const float Settling=FMath::Max(0.f,T-FallTime);
    const float Bounce=Settling>0.f ? 6.f*FMath::Exp(-5.f*Settling)*FMath::Abs(FMath::Sin(12.f*Settling)) : 0.f;
    const FQuat Roll(FVector::ForwardVector,FMath::DegreesToRadians(-TipSide*(Tip-Bounce)));
    const FQuat Yaw(FVector::UpVector,FMath::DegreesToRadians(2.5f*TipSide*Phase));
    const float Slide=58.f*FMath::SmoothStep(0.f,.42f,Age)+21.f*Phase;
    const float Burial=95.f*FMath::SmoothStep(6.8f,8.9f,Age);
    Grille->SetRelativeLocationAndRotation(FVector(0,Slide*TipSide,Bottom+8.f*Phase-Burial),Yaw*Roll);
    if(!bGroundImpact && T>=FallTime)
    {
        bGroundImpact=true;
        const double Height=Grille->GetStaticMesh()->GetBoundingBox().GetSize().Z;
        Dust(FVector(0,TipSide*(Slide+Height*.55),12),1.15f);
        Dust(FVector(-170,TipSide*(Slide+Height*.82),12),.65f);
        Dust(FVector(170,TipSide*(Slide+Height*.82),12),.65f);
    }
}

void AHighVillageCollapse::Tick(float Delta)
{
    Super::Tick(Delta);
    const auto* Section=Cast<AVillageDefenseSection>(GetOwner());
    if(IsValid(Section))
    {
        if(Section->GetHealth()<=0.f)bSawBreach=true;
        else if(bSawBreach){Destroy();return;}
    }
    else if(!bStairs){Destroy();return;}
    Age+=Delta;
    if(Grille)AnimateGrille();
    for(int32 I=0;I<Rubble.Num();++I)
    {
        auto* Part=Rubble[I].Get();
        if(ReleaseTimes[I]>=0.f && Age>=ReleaseTimes[I])
        {
            Part->SetSimulatePhysics(true);
            Part->SetPhysicsLinearVelocity(LaunchSpeeds[I]);
            Part->SetPhysicsAngularVelocityInDegrees(AngularSpeeds[I]);
            ReleaseTimes[I]=-1.f;
        }
        if(Age>=7.f)
        {
            if(Part->IsSimulatingPhysics()){Part->SetSimulatePhysics(false);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);}
            Part->SetWorldScale3D(FragmentScales[I]*FMath::Max(.001f,1.f-FMath::SmoothStep(7.f,8.9f,Age)));
        }
    }
    if(bStairs && !bGroundImpact && !Rubble.IsEmpty() && Age>=1.05f)
    {
        bGroundImpact=true;
        // Stones from each flight and the high landing meet the ground at their displaced positions.
        for(int32 I:{5,11,17})
        {
            FVector Floor=GetActorTransform().InverseTransformPosition(Rubble[I]->GetComponentLocation());
            Floor.Z=12.;
            Dust(Floor,.62f);
        }
    }
    else if(!bStairs && !Grille && !bGroundImpact && Age>=.72f)
    {
        bGroundImpact=true;
        Dust(FVector(-73,25,15),.85f);
        Dust(FVector(85,-25,12),.85f);
    }
}
