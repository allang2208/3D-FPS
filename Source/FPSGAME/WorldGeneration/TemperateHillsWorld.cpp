#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Engine/GameInstance.h"
#include "PCGComponent.h"
#include "PCGGraph.h"
#include "PCGWorldActor.h"
#include "Subsystems/PCGSubsystem.h"
#include "RuntimeGen/SchedulingPolicies/PCGSchedulingPolicyDistanceAndDirection.h"
#include "Components/BoxComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"
#include "../FPSWeatherManager.h"

namespace TemperateHills
{
uint32 Mix(uint32 V) { V ^= V >> 16; V *= 0x7feb352dU; V ^= V >> 15; V *= 0x846ca68bU; return V ^ (V >> 16); }
uint32 Key(int32 X, int32 Y, uint32 Seed, uint32 Salt) { return Mix(Mix(uint32(X)*0x9e3779b9U) ^ Mix(uint32(Y)*0x85ebca6bU+0x1b873593U) ^ Mix(Seed+Salt)); }
uint64 CellId(int32 X,int32 Y) { return (uint64(uint32(X))<<32)|uint32(Y); }
double Unit(uint32 V) { return double(Mix(V) & 0x00ffffffU) / 16777216.0; }
double Smooth(double T) { T=FMath::Clamp(T,0.0,1.0); return T*T*(3-2*T); }
double ValleyY(double X, int32 Seed) { return 1900*FMath::Sin(X*.000065+Unit(Seed)*3)+850*FMath::Sin(X*.00014); }
struct FLayerRadii : FPCGRuntimeGenerationRadii
{
    explicit FLayerRadii(float Radius)
    {
        RadiusUnbounded.Default=Radius;
        Radius12800.Default=Radius;
        Radius6400.Default=Radius;
        Radius3200.Default=Radius;
        Radius1600.Default=Radius;
        CleanupRadiusScalar.Default=1.3f;
        ComputeHash();
    }
};
}

ATemperateHillsWorld::ATemperateHillsWorld()
{
    PrimaryActorTick.bCanEverTick=true;
    GenerationBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("WorldBounds"));
    RootComponent=GenerationBounds;
    GenerationBounds->SetBoxExtent(FVector(51200,51200,50000));
    GenerationBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GenerationBounds->SetCanEverAffectNavigation(false);
    for(int32 Layer=0;Layer<4;++Layer)
    {
        auto* C=CreateDefaultSubobject<UPCGComponent>(*FString::Printf(TEXT("PCGLayer%d"),Layer));
        C->GenerationTrigger=EPCGComponentGenerationTrigger::GenerateAtRuntime;
        C->bIsComponentPartitioned=true;
        C->bOverrideGenerationRadii=true;
        C->SetSchedulingPolicyClass(UPCGSchedulingPolicyDistanceAndDirection::StaticClass());
        PCGLayers.Add(C);
    }
}

void ATemperateHillsWorld::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
#if WITH_EDITOR
    if(GetWorld()&&!GetWorld()->IsGameWorld())
        if(auto* Sub=GetWorld()->GetSubsystem<UPCGSubsystem>())Sub->GetPCGWorldActor();
#endif
}

void ATemperateHillsWorld::ResolveSession()
{
    bAudit=FParse::Param(FCommandLine::Get(),TEXT("HillsAudit"));
    bNullAudit=FParse::Param(FCommandLine::Get(),TEXT("nullrhi"));
    FString Label=TEXT("initial");
    FParse::Value(FCommandLine::Get(),TEXT("HillsLabel="),Label);
    AuditDir=FPaths::ProjectSavedDir()/TEXT("TemperateHills")/Label;
    Slot=bAudit?TEXT("TemperateHills_Audit"):TEXT("TemperateHills_World");
    int32 Requested=Seed;
    // Portal re-entry continues the existing world even when this process was
    // originally launched with a new-world or explicit-seed command-line flag.
    const bool ContinueWorld=GetWorld()->URL.HasOption(TEXT("HillsContinue"));
    const bool Explicit=!ContinueWorld&&FParse::Value(FCommandLine::Get(),TEXT("HillsSeed="),Requested);
    const bool NewWorld=!ContinueWorld&&FParse::Param(FCommandLine::Get(),TEXT("HillsNewWorld"));
    UTemperateHillsSave* Saved=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(Saved&&!NewWorld&&!Explicit&&Saved->Version!=1)
    {
        UE_LOG(LogTemp,Error,TEXT("HILLS_SESSION incompatible version=%d; original save retained"),Saved->Version);
        Slot.Reset();return;
    }
    if(Saved&&!NewWorld&&!Explicit){Seed=Saved->Seed;WorldId=Saved->WorldId;}
    else
    {
        Seed=Explicit?Requested:int32(TemperateHills::Mix(FGuid::NewGuid().A));
        WorldId=FGuid::NewGuid();
        auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::CreateSaveGameObject(UTemperateHillsSave::StaticClass()));
        Save->Seed=Seed;Save->WorldId=WorldId;
        if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0)){UE_LOG(LogTemp,Error,TEXT("HILLS_SESSION save failed"));Slot.Reset();}
    }
}

void ATemperateHillsWorld::BeginPlay()
{
    Super::BeginPlay();
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        Loading->UpdatePreparation(FText::FromString(TEXT("正在准备温带丘陵…")),0);
    StartSeconds=FPlatformTime::Seconds();
    if(GetNetMode()!=NM_Standalone){UE_LOG(LogTemp,Error,TEXT("HILLS_V1 supports standalone only"));return;}
    ResolveSession();
    if(Slot.IsEmpty()||!Assets||Assets->GroundMaterial.IsNull()||Assets->Trees.IsEmpty()||Assets->Graphs.Num()!=4)
    {
        UE_LOG(LogTemp,Error,TEXT("HILLS_ASSETS missing curated biome data"));
        if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
            Loading->FailPreparation(FText::FromString(TEXT("世界数据无法读取，请返回主场景后重试。")));
        return;
    }
    SizeMeters=FMath::Clamp(FMath::RoundToFloat(SizeMeters/128)*128,256.f,1024.f);
    GenerationBounds->SetBoxExtent(FVector(SizeMeters*50,SizeMeters*50,50000));
    BeginStreaming();
}

double ATemperateHillsWorld::Noise(double X,double Y,uint32 Salt) const
{
    const int32 IX=FMath::FloorToInt(X),IY=FMath::FloorToInt(Y);
    const double FX=TemperateHills::Smooth(X-IX),FY=TemperateHills::Smooth(Y-IY);
    auto V=[&](int32 A,int32 B){return TemperateHills::Unit(TemperateHills::Key(A,B,uint32(Seed),Salt))*2-1;};
    return FMath::Lerp(FMath::Lerp(V(IX,IY),V(IX+1,IY),FX),FMath::Lerp(V(IX,IY+1),V(IX+1,IY+1),FX),FY);
}

double ATemperateHillsWorld::PathDistance(double X,double Y) const {return FMath::Abs(Y-TemperateHills::ValleyY(X,Seed));}
double ATemperateHillsWorld::Height(double X,double Y) const
{return RiverPlan?RiverPlan->Height(X,Y,Seed):TemperateHillsSurface::Height(X,Y,Seed);}
FVector ATemperateHillsWorld::SurfaceNormal(double X,double Y) const
{return RiverPlan?RiverPlan->Normal(X,Y,Seed):TemperateHillsSurface::Normal(X,Y,Seed);}

double ATemperateHillsWorld::ForestWeight(double X,double Y) const
{return TemperateHills::Smooth((Noise(X*.00014,Y*.00014,173)+.45)/1.05);}
FVector ATemperateHillsWorld::GetStartLocation() const
{
    const double X=-SizeMeters*25+173;
    const double Y=TemperateHills::ValleyY(X,Seed);
    return FVector(X,Y,Height(X,Y)+106);
}

FRotator ATemperateHillsWorld::GetStartRotation() const
{
    if(!RiverPlan||RiverPlan->Points.IsEmpty())return FRotator(0,18,0);
    const FVector2D Start(GetStartLocation());
    FVector2D Target=RiverPlan->Points[0].XY;double Best=DBL_MAX;
    for(const auto& Point:RiverPlan->Points)
    {
        const double D=FVector2D::DistSquared(Start,Point.XY);
        if(D<Best){Best=D;Target=Point.XY;}
    }
    return FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Target.Y-Start.Y,Target.X-Start.X)),0);
}

bool ATemperateHillsWorld::TreeCandidate(int32 GX,int32 GY,FTemperatePlacement& Out) const
{
    if(!Assets||Assets->Trees.IsEmpty())return false;
    const uint32 K=TemperateHills::Key(GX,GY,uint32(Seed),11);
    const double X=(GX+.5+(TemperateHills::Unit(K+1)-.5)*.56)*1200;
    const double Y=(GY+.5+(TemperateHills::Unit(K+2)-.5)*.56)*1200;
    const double Half=SizeMeters*50-1000;
    if(RiverPlan&&RiverPlan->Sample(X,Y).Bank>.02)return false;
    if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half||PathDistance(X,Y)<1150||
        FVector2D::Distance(FVector2D(X,Y),FVector2D(GetStartLocation()))<2200||SurfaceNormal(X,Y).Z<.87)return false;
    const double Forest=ForestWeight(X,Y);
    if(TemperateHills::Unit(K+3)>.045+Forest*.48)return false;
    const double Scale=.68+TemperateHills::Unit(K+5)*.4;
    Out.Transform=FTransform(FRotator(0,TemperateHills::Unit(K+4)*360,0),FVector(X,Y,Height(X,Y)-10),FVector(Scale));
    Out.Mesh=Assets->Trees[K%Assets->Trees.Num()].ToSoftObjectPath();Out.Key=K;Out.CandidateId=TemperateHills::CellId(GX,GY);
    return !Out.Mesh.IsNull();
}

void ATemperateHillsWorld::GetPlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||Layer<0||Layer>3)return;
    if(Layer==3){GetGrassPlacements(Bounds,Out);return;}
    const double Spacing=Layer==0?1200:(Layer==1?2400:650);
    const double Half=SizeMeters*50;
    const double MinX=FMath::Max(-Half,Bounds.Min.X),MinY=FMath::Max(-Half,Bounds.Min.Y);
    const double MaxX=FMath::Min(Half,Bounds.Max.X),MaxY=FMath::Min(Half,Bounds.Max.Y);
    if(MinX>=MaxX||MinY>=MaxY)return;
    TMap<FIntPoint,FTemperatePlacement> TreeCache;
    TSet<FIntPoint> EmptyTreeCells;
    for(int32 GY=FMath::FloorToInt(MinY/Spacing)-1;GY<=FMath::FloorToInt(MaxY/Spacing)+1;++GY)
    for(int32 GX=FMath::FloorToInt(MinX/Spacing)-1;GX<=FMath::FloorToInt(MaxX/Spacing)+1;++GX)
    {
        FTemperatePlacement P;
        if(Layer==0){if(!TreeCandidate(GX,GY,P))continue;}
        else
        {
            const uint32 K=TemperateHills::Key(GX,GY,uint32(Seed),101+Layer);
            const double X=(GX+.5+(TemperateHills::Unit(K+1)-.5)*.8)*Spacing;
            const double Y=(GY+.5+(TemperateHills::Unit(K+2)-.5)*.8)*Spacing;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY||FMath::Abs(X)>Half-500||FMath::Abs(Y)>Half-500)continue;
            // Keep ordinary slope stones and vegetation out of the carved river corridor.
            if(RiverPlan&&RiverPlan->Sample(X,Y).Bank>(Layer==3?.08:.02))continue;
            const FVector N=SurfaceNormal(X,Y);
            if(N.Z<(Layer==1?.72:.83)||PathDistance(X,Y)<(Layer==3?240:700))continue;
            if(Layer<3&&FVector2D::Distance(FVector2D(X,Y),FVector2D(GetStartLocation()))<1600)continue;
            const double Forest=ForestWeight(X,Y);
            const double Probability=Layer==1?(.12+(1-N.Z)*1.6):(Layer==2?.05+Forest*.28:.77-Forest*.23);
            if(TemperateHills::Unit(K+3)>Probability)continue;
            bool TrunkOverlap=false;
            for(int32 TY=FMath::FloorToInt(Y/1200)-1;TY<=FMath::FloorToInt(Y/1200)+1&&!TrunkOverlap;++TY)
            for(int32 TX=FMath::FloorToInt(X/1200)-1;TX<=FMath::FloorToInt(X/1200)+1;++TX)
            {
                const FIntPoint Cell(TX,TY);
                if(EmptyTreeCells.Contains(Cell))continue;
                FTemperatePlacement* T=TreeCache.Find(Cell);
                if(!T){FTemperatePlacement Candidate;if(!TreeCandidate(TX,TY,Candidate)){EmptyTreeCells.Add(Cell);continue;}T=&TreeCache.Add(Cell,MoveTemp(Candidate));}
                if(FVector2D::Distance(FVector2D(X,Y),FVector2D(T->Transform.GetLocation()))<(Layer==1?500:100)){TrunkOverlap=true;break;}
            }
            if(TrunkOverlap)continue;
            const TArray<TSoftObjectPtr<UStaticMesh>>& List=Layer==1?Assets->Rocks:(Layer==2?Assets->Shrubs:Assets->Grass);
            if(List.IsEmpty())continue;
            const double Scale=Layer==1?.7+TemperateHills::Unit(K+5)*1.4:(Layer==2?.65+TemperateHills::Unit(K+5)*.5:.65+TemperateHills::Unit(K+5)*.6);
            const FQuat Rotation=FQuat(N,TemperateHills::Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-(Layer==1?35:3)),FVector(Scale));
            P.Mesh=List[K%List.Num()].ToSoftObjectPath();P.Key=K;P.CandidateId=TemperateHills::CellId(GX,GY);
        }
        const FVector Pos=P.Transform.GetLocation();
        // Half-open ownership ensures no duplicates when HiGen cells share an edge.
        if(Pos.X>=MinX&&Pos.X<MaxX&&Pos.Y>=MinY&&Pos.Y<MaxY)Out.Add(P);
    }
    // River stones reuse the existing 64 m PCG rock layer, radius and collision
    // lifecycle. Candidate keys occupy a separate ID namespace from slope stones.
    if(Layer==1&&RiverPlan&&!Assets->RiverRocks.IsEmpty())
    {
        constexpr double RiverSpacing=750;
        for(int32 GY=FMath::FloorToInt(MinY/RiverSpacing)-1;GY<=FMath::FloorToInt(MaxY/RiverSpacing);++GY)
        for(int32 GX=FMath::FloorToInt(MinX/RiverSpacing)-1;GX<=FMath::FloorToInt(MaxX/RiverSpacing);++GX)
        {
            const uint32 K=TemperateHills::Key(GX,GY,Seed,809);
            const double X=(GX+.2+TemperateHills::Unit(K+1)*.6)*RiverSpacing;
            const double Y=(GY+.2+TemperateHills::Unit(K+2)*.6)*RiverSpacing;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY||FMath::Abs(X)>Half-400||FMath::Abs(Y)>Half-400)continue;
            const auto River=RiverPlan->Sample(X,Y);
            if(River.Bank<.65||River.Distance>River.HalfWidth+550||River.Distance<River.HalfWidth*.3)continue;
            if(TemperateHills::Unit(K+3)>(River.Wet>.7?.22:.48))continue;
            const FVector N=SurfaceNormal(X,Y);if(N.Z<.90)continue;
            const double Scale=.45+TemperateHills::Unit(K+5)*.60;
            const FQuat Rotation=FQuat(N,TemperateHills::Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            FTemperatePlacement P;
            const auto& Rock=Assets->RiverRocks[K%Assets->RiverRocks.Num()];
            const double Base=Rock.IsValid()?Rock.Get()->GetBoundingBox().Min.Z:0;
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-(Base+18)*Scale),FVector(Scale));
            P.Mesh=Rock.ToSoftObjectPath();P.Key=K;
            P.CandidateId=TemperateHills::CellId(GX,GY)^0x4000000000000000ULL;
            Out.Add(P);
        }
    }
}

uint32 ATemperateHillsWorld::LayoutHash(int32 Layer) const
{
    // Sample a fixed central region; independent of current viewer/PCG scheduling.
    TArray<FTemperatePlacement> Points;GetPlacements(Layer,FBox(FVector(-12800,-12800,-50000),FVector(12800,12800,50000)),Points);
    uint32 H=uint32(Seed);
    for(const auto& P:Points){const FVector V=P.Transform.GetLocation();H=TemperateHills::Mix(H^P.Key^uint32(FMath::RoundToInt(V.Z)));}
    return H;
}

void ATemperateHillsWorld::ActivateVegetationLayer(int32 Layer)
{
    // Grass is invisible by 50 m, with a 10 m generation lead and 78 m cleanup.
    const float Radii[]={18000,12000,8000,6000};
    auto* C=PCGLayers[Layer].Get();C->Seed=Seed;
    C->GenerationRadii=TemperateHills::FLayerRadii(Radii[Layer]);
    C->SetGraph(Assets->Graphs[Layer].Get());
    if(auto* Sub=GetWorld()->GetSubsystem<UPCGSubsystem>())
    {
        Sub->RegisterOrUpdateExecutionSource(C);
        Sub->RefreshRuntimeGenExecutionSource(C,EPCGChangeType::GenerationGrid);
    }
}

void ATemperateHillsWorld::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    TickStreaming();
    if(!bReady)return;
    for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It)
    {
        if(GroundMID)GroundMID->SetScalarParameterValue(TEXT("Wetness"),It->GetSurfaceWetness());
        break;
    }
    if(bAudit)
    {
        if(GetWorld()->GetTimeSeconds()>26&&!bNullAudit)FrameSamples.Add(FMath::Max(.0,double(DeltaSeconds))*1000);
        RunAudit();
    }
}

void ATemperateHillsWorld::AuditCheck(bool Pass,const TCHAR* Message)
{
    bAuditPassed&=Pass;
    UE_LOG(LogTemp,Display,TEXT("HILLS_CHECK %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Message);
}

void ATemperateHillsWorld::RunAudit()
{
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now<AuditNext)return;
    auto* PC=UGameplayStatics::GetPlayerController(this,0);
    auto* Pawn=UGameplayStatics::GetPlayerCharacter(this,0);
    if(!PC||!Pawn){AuditCheck(false,TEXT("pawn ready"));FPlatformMisc::RequestExitWithStatus(false,1);return;}
    auto Capture=[&](const TCHAR* Name){if(!bNullAudit)FScreenshotRequest::RequestScreenshot(AuditDir/(FString(Name)+TEXT(".png")),false,false);};
    if(AuditStage==0)
    {
        IFileManager::Get().MakeDirectory(*AuditDir,true);
        AuditCheck(Terrain.Num()==FMath::Square(FMath::RoundToInt(SizeMeters/128)),TEXT("all terrain chunks built"));
        AuditCheck(Pawn->GetCharacterMovement()->IsMovingOnGround(),TEXT("player stands on generated collision"));
        bool Hits=true;double Min=DBL_MAX,Max=-DBL_MAX;double Error=0;
        FCollisionQueryParams GroundQuery;GroundQuery.AddIgnoredComponent(Trunks.Get());
        // Rocks are valid obstacles above the terrain, so exclude other actors from the terrain-height check.
        for(TActorIterator<AActor> It(GetWorld());It;++It)if(*It!=this)GroundQuery.AddIgnoredActor(*It);
        for(int32 Y=-4;Y<=4;++Y)for(int32 X=-4;X<=4;++X)
        {
            const double WX=X*10000,WY=Y*10000,Z=Height(WX,WY);Min=FMath::Min(Min,Z);Max=FMath::Max(Max,Z);
            FHitResult Hit;
            const bool Got=GetWorld()->LineTraceSingleByChannel(Hit,FVector(WX,WY,Z+500),FVector(WX,WY,Z-500),ECC_Pawn,GroundQuery);
            Hits&=Got;if(Got)Error=FMath::Max(Error,FMath::Abs(Hit.ImpactPoint.Z-Z));
        }
        AuditCheck(Hits&&Error<15,TEXT("81 terrain traces match height function within 15cm"));
        AuditCheck(Max-Min>1800,TEXT("terrain has more than 18m measured elevation change"));
        AuditCheck(Trunks&&Trunks->GetInstanceCount()>50,TEXT("existing Black Poplar candidates have trunk collision"));
        TArray<FTemperatePlacement> Left,Right,Whole;
        GetPlacements(0,FBox(FVector(-12800,-12800,-50000),FVector(0,12800,50000)),Left);
        GetPlacements(0,FBox(FVector(0,-12800,-50000),FVector(12800,12800,50000)),Right);
        GetPlacements(0,FBox(FVector(-12800,-12800,-50000),FVector(12800,12800,50000)),Whole);
        bool TrunkBlocks=false;
        for(const auto& Tree:Whole)
        {
            const FVector P=Tree.Transform.GetLocation();
            if(SurfaceNormal(P.X,P.Y).Z<.96)continue;
            FHitResult Block;FCollisionQueryParams Q;Q.AddIgnoredActor(Pawn);
            GetWorld()->SweepSingleByChannel(Block,P+FVector(-220,0,200),P+FVector(220,0,200),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(36,90),Q);
            TrunkBlocks=Block.GetComponent()==Trunks.Get();break;
        }
        AuditCheck(TrunkBlocks,TEXT("player-sized capsule is blocked by a generated tree trunk"));
        TSet<uint64> Keys;for(const auto& P:Left)Keys.Add(P.CandidateId);for(const auto& P:Right)Keys.Add(P.CandidateId);
        AuditCheck(Keys.Num()==Whole.Num()&&Keys.Num()==Left.Num()+Right.Num(),TEXT("adjacent cell ownership is complete and duplicate-free"));
        auto* Saved=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
        AuditCheck(Saved&&Saved->Seed==Seed&&Saved->WorldId==WorldId,TEXT("world seed/id save readback"));
        FString Layout=FString::Printf(TEXT("{\"seed\":%d,\"treeHash\":%u,\"rockHash\":%u,\"shrubHash\":%u,\"grassHash\":%u,\"heightMinM\":%.3f,\"heightMaxM\":%.3f,\"traceMaxErrorCm\":%.3f}"),Seed,LayoutHash(0),LayoutHash(1),LayoutHash(2),LayoutHash(3),Min/100,Max/100,Error);
        FFileHelper::SaveStringToFile(Layout,*(AuditDir/TEXT("layout.json")));
        PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);
        PC->SetControlRotation(FRotator(6,18,0));
        Capture(TEXT("01-player-meadow"));
        AuditStage=1;AuditNext=Now+(bNullAudit?1:8);return;
    }
    if(AuditStage==1)
    {
        int32 Trees=0,Static=0;
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        {
            TInlineComponentArray<UInstancedSkinnedMeshComponent*> Skinned(*It);for(auto* C:Skinned)Trees+=C->GetInstanceCount();
            TInlineComponentArray<UInstancedStaticMeshComponent*> ISMs(*It);for(auto* C:ISMs)if(C!=Trunks)Static+=C->GetInstanceCount();
        }
        AuditCheck(Trees>20,TEXT("PCG native skinned tree instances generated"));
        AuditCheck(Static>100,TEXT("PCG static ground-cover instances generated"));
        UE_LOG(LogTemp,Display,TEXT("HILLS_INSTANCES trees=%d ground_cover=%d fog=%d"),Trees,Static,ValleyFog.Num());
        if(!AuditCamera)AuditCamera=GetWorld()->SpawnActor<ACameraActor>();
        const FVector Eye=GetStartLocation()+FVector(-6000,-6000,8000),Target=FVector(1000,2000,Height(1000,2000));
        AuditCamera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());AuditCamera->GetCameraComponent()->SetFieldOfView(67);PC->SetViewTarget(AuditCamera);
        AuditStage=2;AuditNext=Now+(bNullAudit?1:12);return;
    }
    if(AuditStage==2){Capture(TEXT("02-hills-overview"));AuditStage=3;AuditNext=Now+(bNullAudit?1:3);return;}
    if(AuditStage==3)
    {
        TArray<FTemperatePlacement> Trees;GetPlacements(0,FBox(FVector(-30000,-15000,-50000),FVector(0,15000,50000)),Trees);
        if(!Trees.IsEmpty())
        {
            const FVector T=Trees[Trees.Num()/2].Transform.GetLocation();
            const FVector Eye(T.X-2100,T.Y-1200,Height(T.X-2100,T.Y-1200)+200);
            AuditCamera->SetActorLocationAndRotation(Eye,(T+FVector(0,0,1100)-Eye).Rotation());AuditCamera->GetCameraComponent()->SetFieldOfView(70);
            // Exercise streaming at the new camera location as well as the actual pawn source.
            Pawn->SetActorLocation(FVector(T.X-2100,T.Y-1200,Height(T.X-2100,T.Y-1200)+106));
        }
        AuditStage=4;AuditNext=Now+(bNullAudit?1:12);return;
    }
    if(AuditStage==4){Capture(TEXT("03-black-poplar"));AuditStage=5;AuditNext=Now+(bNullAudit?1:3);return;}
    if(AuditStage==5)
    {
        const double X=0,Y=TemperateHills::ValleyY(0,Seed);
        const FVector Eye(X-4800,Y-2500,Height(X-4800,Y-2500)+240);
        AuditCamera->SetActorLocationAndRotation(Eye,(FVector(X+3500,Y,Height(X+3500,Y)+140)-Eye).Rotation());
        AuditCamera->GetCameraComponent()->SetFieldOfView(76);
        Pawn->SetActorLocation(FVector(Eye.X,Eye.Y,Height(Eye.X,Eye.Y)+106));
        AuditStage=6;AuditNext=Now+(bNullAudit?1:12);return;
    }
    if(AuditStage==6){Capture(TEXT("04-valley-fog"));AuditStage=7;AuditNext=Now+(bNullAudit?1:3);return;}
    if(AuditStage==7)
    {
        FrameSamples.Sort();double Median=0,P95=0;
        if(!FrameSamples.IsEmpty()){Median=FrameSamples[FrameSamples.Num()/2];P95=FrameSamples[FMath::Min(FrameSamples.Num()-1,FMath::FloorToInt(FrameSamples.Num()*.95))];}
        UE_LOG(LogTemp,Display,TEXT("HILLS_AUDIT_COMPLETE pass=%d seed=%d frame_median_ms=%.3f frame_p95_ms=%.3f samples=%d mode=%s"),bAuditPassed,Seed,Median,P95,FrameSamples.Num(),bNullAudit?TEXT("NullRHI"):TEXT("StandaloneEditorRuntime"));
        FPlatformMisc::RequestExitWithStatus(false,bAuditPassed?0:1);AuditStage=8;
    }
}

void ATemperateHillsWorld::EndPlay(const EEndPlayReason::Type Reason)
{
    bReady=false;
    EndStreaming();
    Super::EndPlay(Reason);
}

void ATemperateHillsGameMode::RestartPlayer(AController* NewPlayer)
{
    if(!IsValid(NewPlayer)||NewPlayer->GetPawn())return;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->bSurfaceReady){RestartPlayerAtTransform(NewPlayer,FTransform(It->GetStartRotation(),It->GetStartLocation()));return;}
    FTimerHandle Retry;
    GetWorldTimerManager().SetTimer(Retry,FTimerDelegate::CreateWeakLambda(this,[this,Weak=TWeakObjectPtr<AController>(NewPlayer)](){if(Weak.IsValid())RestartPlayer(Weak.Get());}),.15f,false);
}
