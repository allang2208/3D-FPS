#include "TemperateHillsBackdrop.h"
#include "TemperateInteriorCanopy.h"
#include "TemperateHillsMap.h"
#include "TemperateQuarryYard.h"
#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "TemperateWoodlandFloor.h"
#include "Async/Async.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "RHI.h"

namespace TemperateBackdrop
{
constexpr int32 ColorSize=1024;
constexpr int32 RingRows=16;
struct FResult
{
    TArray<UE::Geometry::FDynamicMesh3> Meshes;
    TArray<FColor> Colors;
    // Far-field tree silhouettes, spawned as instanced statics once the worker
    // result arrives. Kept alongside the rings so one reset frees everything.
    TArray<TArray<FTransform>> CanopyByMesh;
};

struct FCanopyPalette
{
    TArray<int32> Woodland;
    TArray<int32> Alder;
};

double Height(double X,double Y,double Half,int32 Seed,const TemperateRiver::FPlanPtr& River,int32 Version,const FTemperateVillageSite& Village)
{
    const double Z=River?River->Height(X,Y,Seed):TemperateHillsSurface::Height(X,Y,Seed,Version);
    const double Blend=FMath::SmoothStep(Half,150000.0,FMath::Max(FMath::Abs(X),FMath::Abs(Y)));
    // Distant low rolling ridges extend the biome, with no playable-world edits.
    return Village.Grade(X,Y,Z,Seed)+Blend*(2200+TemperateHillsSurface::Noise(X*.0000035,Y*.0000035,Seed,1709)*4500);
}

double CoreTriangleHeight(double X,double Y,double Half,int32 Seed,const TemperateRiver::FPlanPtr& River,int32 Version,const FTemperateVillageSite& Village)
{
    const double Step=Half*2/Grid;
    const double U=FMath::Clamp((X+Half)/Step,0.0,double(Grid)-1.e-6);
    const double V=FMath::Clamp((Y+Half)/Step,0.0,double(Grid)-1.e-6);
    const int32 IX=FMath::FloorToInt(U),IY=FMath::FloorToInt(V);
    const double A=U-IX,B=V-IY;
    auto H=[&](int32 DX,int32 DY){return Height(-Half+(IX+DX)*Step,-Half+(IY+DY)*Step,Half,Seed,River,Version,Village);};
    // Matches the diagonal used by both the proxy and streamed terrain.
    return A>=B?H(0,0)*(1-A)+H(1,0)*(A-B)+H(1,1)*B:
        H(0,0)*(1-B)+H(0,1)*(B-A)+H(1,1)*A;
}

TSharedPtr<FResult,ESPMode::ThreadSafe> Build(double Half,int32 Seed,TemperateRiver::FPlanPtr River,
    const FCanopyPalette& Palette,int32 CanopyBudget,int32 Version,const FTemperateVillageSite& Village)
{
    auto Result=MakeShared<FResult,ESPMode::ThreadSafe>();
    Result->Meshes.SetNum(3);
    auto Setup=[](UE::Geometry::FDynamicMesh3& M){M.EnableAttributes();};
    auto Vertex=[&](UE::Geometry::FDynamicMesh3& M,double X,double Y)
    {
        const double Z=Height(X,Y,Half,Seed,River,Version,Village);
        const FVector3f N=FVector3f(FVector(-(Height(X+100,Y,Half,Seed,River,Version,Village)-Height(X-100,Y,Half,Seed,River,Version,Village))/200,
            -(Height(X,Y+100,Half,Seed,River,Version,Village)-Height(X,Y-100,Half,Seed,River,Version,Village))/200,1).GetSafeNormal());
        M.Attributes()->PrimaryNormals()->AppendElement(N);
        M.Attributes()->PrimaryUV()->AppendElement(FVector2f((X+OuterHalf)/(2*OuterHalf),(Y+OuterHalf)/(2*OuterHalf)));
        return M.AppendVertex(FVector3d(X,Y,Z));
    };
    auto Tri=[](UE::Geometry::FDynamicMesh3& M,int32 A,int32 B,int32 C)
    {
        const int32 ID=M.AppendTriangle(A,B,C);const UE::Geometry::FIndex3i Indices(A,B,C);
        M.Attributes()->PrimaryNormals()->SetTriangle(ID,Indices);M.Attributes()->PrimaryUV()->SetTriangle(ID,Indices);
    };
    auto& Core=Result->Meshes[0];Setup(Core);
    for(int32 Y=0;Y<=Grid;++Y)for(int32 X=0;X<=Grid;++X)Vertex(Core,-Half+X*(Half*2/Grid),-Half+Y*(Half*2/Grid));
    for(int32 Y=0;Y<Grid;++Y)for(int32 X=0;X<Grid;++X)
    {const int32 A=Y*(Grid+1)+X;Tri(Core,A,A+Grid+2,A+1);Tri(Core,A,A+Grid+1,A+Grid+2);}
    const double Rings[]={Half,153600.0,OuterHalf};
    constexpr int32 Perimeter=Grid*4;
    for(int32 Ring=0;Ring<2;++Ring)
    {
        auto& M=Result->Meshes[Ring+1];Setup(M);
        for(int32 Row=0;Row<=RingRows;++Row)
        {
            const double R=FMath::Lerp(Rings[Ring],Rings[Ring+1],double(Row)/RingRows);
            for(int32 I=0;I<Perimeter;++I)
            {
                const int32 Side=I/Grid;const double T=double(I%Grid)/Grid;
                Vertex(M,Side==0?-R+T*2*R:Side==1?R:Side==2?R-T*2*R:-R,
                    Side==0?-R:Side==1?-R+T*2*R:Side==2?R:R-T*2*R);
            }
        }
        for(int32 Row=0;Row<RingRows;++Row)for(int32 I=0;I<Perimeter;++I)
        {
            const int32 J=(I+1)%Perimeter,A=Row*Perimeter+I,B=Row*Perimeter+J;
            Tri(M,A,B,B+Perimeter);Tri(M,A,B+Perimeter,A+Perimeter);
        }
        if(Ring==1)for(int32 I=0;I<Perimeter;++I)
        {
            const FVector3d P=M.GetVertex(RingRows*Perimeter+I);
            M.AppendVertex(FVector3d(P.X,P.Y,-100000));
            M.Attributes()->PrimaryNormals()->AppendElement(FVector3f(FVector(-P.X,-P.Y,0).GetSafeNormal()));
            M.Attributes()->PrimaryUV()->AppendElement(FVector2f((P.X+OuterHalf)/(2*OuterHalf),(P.Y+OuterHalf)/(2*OuterHalf)));
        }
        if(Ring==1)for(int32 I=0;I<Perimeter;++I)
        {
            const int32 J=(I+1)%Perimeter,A=RingRows*Perimeter+I,B=RingRows*Perimeter+J;
            Tri(M,A,B+Perimeter,B);Tri(M,A,A+Perimeter,B+Perimeter);
        }
    }
    const auto Ecology=River?River->Ecology:TemperateEcology::FProfile{};
    Result->Colors.SetNumUninitialized(ColorSize*ColorSize);
    for(int32 Y=0;Y<ColorSize;++Y)for(int32 X=0;X<ColorSize;++X)
    {
        const double WX=((X+.5)/ColorSize*2-1)*OuterHalf,WY=((Y+.5)/ColorSize*2-1)*OuterHalf;
        const double Region=River?River->RainforestWeight(WX,WY):0.;
        const double Forest=TemperateForestHabitat::Canopy(WX,WY,Seed,Region,Ecology);
        const double Patch=TemperateHillsSurface::Noise(WX*.00035,WY*.00035,Seed,1711)*.5+.5;
        FLinearColor Color=FMath::Lerp(FLinearColor(.24f,.205f,.125f),FLinearColor(.105f,.135f,.09f),float(Forest*.8));
        Color=FMath::Lerp(Color,FLinearColor(.23f,.22f,.18f),float(Patch*.24));
        if(FMath::Abs(WX)<Half&&FMath::Abs(WY)<Half)
        {
            // Use the already-built proxy normals. No extra heightfield
            // evaluations for the distant colour texture.
            const double U=(WX+Half)*Grid/(2.*Half),V=(WY+Half)*Grid/(2.*Half);
            const int32 IX=FMath::Min(FMath::FloorToInt(U),Grid-1),IY=FMath::Min(FMath::FloorToInt(V),Grid-1);
            const int32 A=IY*(Grid+1)+IX;
            const auto* Normals=Core.Attributes()->PrimaryNormals();
            const FVector N=FMath::Lerp(
                FMath::Lerp(FVector(Normals->GetElement(A)),FVector(Normals->GetElement(A+1)),U-IX),
                FMath::Lerp(FVector(Normals->GetElement(A+Grid+1)),FVector(Normals->GetElement(A+Grid+2)),U-IX),
                V-IY).GetSafeNormal();
            const auto Bank=River?River->Sample(WX,WY):TemperateRiver::FSample();
            const double Dry=(River&&River->bVillageRainforest)?(1.-Region)*(1.-FMath::SmoothStep(0.,.02,Bank.Bank))*(1.-Bank.CliffWeight):0.;
            const double Deposit=Dry>0.?TemperateWoodlandFloor::DryDeposit(WX,WY,Seed,N,TemperateWoodlandFloor::Patch(WX,WY,Seed)):1.;
            const double GroundShade=Forest*FMath::Lerp(1.,Deposit,Dry);
            const auto Site=TemperateForestHabitat::Upland(N,GroundShade,TemperateForestHabitat::Moisture(WX,WY,Seed,Region,Ecology),Region,Ecology);
            const double Verge=TemperateForestHabitat::UplandSurfaceWeight(FMath::Abs(WY-TemperateHillsSurface::ValleyY(WX,Seed)),Bank.Bank,N.Z);
            const double Meadow=Verge*Site.Meadow, Stony=Verge*Site.Stony, Total=Meadow+Stony;
            const auto Grass=FMath::Lerp(FLinearColor(.116f,.067f,.023f),FLinearColor(.096f,.12f,.047f),float(Meadow));
            const auto Tone=FMath::Lerp(Grass,FLinearColor(.106f,.077f,.042f),float(Stony/FMath::Max(.0001,Total)));
            Color=FMath::Lerp(Color,Tone,float(.65*FMath::Min(1.,Total)));
            // Tiles outside the terrain streaming radius still belong to the
            // same forest. Carry the green floor into the playable proxy.
            if(River&&River->bVillageRainforest)
            {
                const FLinearColor Moss=FMath::Lerp(FLinearColor(.155f,.185f,.080f),FLinearColor(.095f,.122f,.048f),float(Forest*.7+Patch*.3));
                Color=FMath::Lerp(Color,Moss,float(FMath::SmoothStep(0.,.90,Region)*FMath::SmoothStep(.72,.88,N.Z)*(1.-FMath::SmoothStep(.12,.80,Bank.Bank))*(1.-Bank.CliffWeight)));
            }
            Color=FMath::Lerp(Color,FLinearColor(.075f,.12f,.10f),float(Bank.Wet*.8));
            if(River && Bank.CliffWeight>0.)
            {
                const auto Q=TemperateQuarry::Finish(River->WhiteCliffs.Local(WX,WY),N.Z,Patch);
                const auto Wall=FMath::Lerp(FLinearColor(.24f,.193f,.14f),FLinearColor(.34f,.326f,.28f),
                    float(FMath::Max(Q.Bed,Q.Talus)*(1.-Q.Wear)));
                Color=FMath::Lerp(Color,Wall,float(Bank.CliffWeight*(1.-Q.Turf)*.90));
            }
        }
        Result->Colors[Y*ColorSize+X]=Color.ToFColorSRGB();
    }
    // Canopy silhouettes on the backdrop rings only: the playable half already
    // carries instanced trees from PCG. The placement field is the same forest
    // noise that tints the ground, so dark forest patches and raised treelines
    // agree when viewed from a ridge. Pure math, worker-thread safe.
    Result->CanopyByMesh.SetNum(Palette.Woodland.Num()+Palette.Alder.Num());
    if(!Result->CanopyByMesh.IsEmpty()&&CanopyBudget>0)
    {
        using namespace TemperateHillsSurface;
        constexpr double Spacing=14000;
        const double Inner=Half+4000,Outer=OuterHalf*.55;
        struct FCopse { FVector2D Center; double Forest; uint32 SeedKey; };
        TArray<FCopse> Copses;
        for(int32 GY=FMath::FloorToInt(-Outer/Spacing);GY<=FMath::FloorToInt(Outer/Spacing);++GY)
        for(int32 GX=FMath::FloorToInt(-Outer/Spacing);GX<=FMath::FloorToInt(Outer/Spacing);++GX)
        {
            const uint32 K=TemperateHillsSurface::Key(GX,GY,uint32(Seed),1771);
            const double X=(GX+.2+TemperateHillsSurface::Unit(K+1)*.6)*Spacing;
            const double Y=(GY+.2+TemperateHillsSurface::Unit(K+2)*.6)*Spacing;
            const double M=FMath::Max(FMath::Abs(X),FMath::Abs(Y));
            if(M<Inner||M>Outer)continue;
            const double Region=River?River->RainforestWeight(X,Y):0.;
            const double Forest=TemperateForestHabitat::Canopy(X,Y,Seed,Region,Ecology);
            if(TemperateHillsSurface::Unit(K+3)>Forest*.55)continue;
            Copses.Add({FVector2D(X,Y),Forest,K});
        }
        // Use the actual ring triangles under the trees. Sampling the full
        // resolution hill here can float a whole copse over the coarse skyline.
        auto RingHeight=[&](const FVector2D& P)
        {
            const double R=FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y));
            const int32 Ring=R<Rings[1]?0:1;
            const auto& Shell=Result->Meshes[Ring+1];
            const bool Horizontal=FMath::Abs(P.Y)>=FMath::Abs(P.X);
            const int32 Side=Horizontal?(P.Y<0.?0:2):(P.X>0.?1:3);
            const double Tangent=Side==0?P.X:Side==1?P.Y:Side==2?-P.X:-P.Y;
            const int32 I=Side*Grid+FMath::Clamp(FMath::FloorToInt((Tangent/R+1.)*.5*Grid),0,Grid-1);
            const int32 J=(I+1)%Perimeter;
            const int32 Row=FMath::Clamp(FMath::FloorToInt((R-Rings[Ring])/(Rings[Ring+1]-Rings[Ring])*RingRows),0,RingRows-1);
            const int32 A=Row*Perimeter+I,B=Row*Perimeter+J;
            const FVector3d V=Shell.GetVertex(A),Diagonal=Shell.GetVertex(B+Perimeter)-V;
            const FVector2D D=FVector2D(Diagonal),Q=P-FVector2D(V);
            const FVector3d Across=Shell.GetVertex(B)-V;
            const double Cross=FVector2D::CrossProduct(D,Q);
            const FVector3d Edge=Cross*FVector2D::CrossProduct(D,FVector2D(Across))>=0.?Across:Shell.GetVertex(A+Perimeter)-V;
            const double Area=FVector2D::CrossProduct(D,FVector2D(Edge));
            return V.Z+(FVector2D::CrossProduct(Q,FVector2D(Edge))*Diagonal.Z+Cross*Edge.Z)/Area;
        };
        // Under a small asset budget, sample every compass direction fairly.
        Copses.Sort([](const FCopse& A,const FCopse& B){return A.SeedKey<B.SeedKey;});
        int32 Placed=0;
        for(const FCopse& Copse:Copses)
        {
            const uint32 K=Copse.SeedKey;
            const int32 Count=Unit(K+6)<.19?1:3+FMath::FloorToInt((3.+6.*Copse.Forest)*Unit(K+7));
            const FVector2D Center=Copse.Center;
            const FVector2D Rise(RingHeight(Center+FVector2D(800,0))-RingHeight(Center-FVector2D(800,0)),
                RingHeight(Center+FVector2D(0,800))-RingHeight(Center-FVector2D(0,800)));
            const double Yaw=Rise.SizeSquared()>FMath::Square(80.)?
                FMath::RadiansToDegrees(FMath::Atan2(Rise.X,-Rise.Y))+(Unit(K+8)-.5)*54.:360.*Unit(K+8);
            const double Moist=TemperateForestHabitat::Moisture(Center.X,Center.Y,Seed,0.,Ecology);
            const double AlderShare=FMath::SmoothStep(.42,.86,Moist)*(1.-FMath::SmoothStep(105.,330.,Rise.Size()));
            const bool bAlderStand=Unit(K+33)<AlderShare*.76;
            const double Spread=1350.+1800.*Unit(K+9);
            for(int32 I=0;I<Count&&Placed<CanopyBudget;++I)
            {
                const uint32 TreeKey=Mix(K^uint32(I+1)*0x9e3779b9U);
                const double T=I?2.*Unit(TreeKey+1)-1.:0.;
                const double Cross=I?(2.*Unit(TreeKey+2)-1.)*.48*(1.-.60*FMath::Abs(T)):0.;
                const FVector2D P=Copse.Center+FVector2D(T*Spread,Cross*Spread).GetRotated(Yaw);
                const double R=FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y));
                if(R<Inner||R>Outer)continue;
                const double S=(1.55+.55*Unit(K+4))*(1.-.34*FMath::Abs(T))*(.86+.30*Unit(TreeKey+3));
                const uint32 Form=Unit(TreeKey+5)<.78?K:TreeKey;
                const bool bAlder=!Palette.Alder.IsEmpty()&&(Palette.Woodland.IsEmpty()||
                    (R>Half+12500.&&bAlderStand&&Unit(TreeKey+11)<.82));
                const auto& Forms=bAlder?Palette.Alder:Palette.Woodland;
                const int32 Slot=Forms[Form%Forms.Num()];
                Result->CanopyByMesh[Slot].Emplace(FRotator(0,Unit(TreeKey+4)*360.,0),FVector(P,RingHeight(P)),FVector(S));
                ++Placed;
            }
            if(Placed>=CanopyBudget)break;
        }
    }
    return Result;
}
}

struct FTemperateBackdropState
{
    TemperateBackdrop::FInteriorCanopy Interior;
    TWeakObjectPtr<AActor> PresentationActor;
    TFuture<TSharedPtr<TemperateBackdrop::FResult,ESPMode::ThreadSafe>> Job;
    TSharedPtr<TemperateBackdrop::FResult,ESPMode::ThreadSafe> Result;
    TArray<FColor> Coverage;
    int32 Cells=0;
    int32 Submitted=0;
    int32 NextCanopyMesh=0;
    bool Pending=true;
    bool CoverageDirty=true;
};

void ATemperateHillsWorld::BeginSkyClouds()
{
    // The reserved volumetric cloud layer was retired with the UDS migration;
    // Ultra Dynamic Sky presents clouds for the hills world now.
}

void ATemperateHillsWorld::ActivateSkyClouds()
{
}

void ATemperateHillsWorld::TickBackdrop(bool bCanopyAssetsReady)
{
    if(!Assets||!Assets->BackdropMaterial.IsValid())return;
    if(!Backdrop)
    {
        Backdrop=MakeShared<FTemperateBackdropState>();auto& S=*Backdrop;
        S.Cells=FMath::RoundToInt(SizeMeters/64);S.Coverage.Init(FColor::Black,S.Cells*S.Cells);
        TemperateBackdrop::FCanopyPalette Palette;
        for(int32 I=0;I<Assets->BackdropTrees.Num();++I)
        {
            const bool bAlder=Assets->BackdropTrees[I].ToSoftObjectPath().GetAssetName().StartsWith(TEXT("SM_HillsAlderCrown_"));
            (bAlder?Palette.Alder:Palette.Woodland).Add(I);
        }
        const bool bInterior=!Palette.Alder.IsEmpty()&&Seed==TemperateHillsMap::Seed&&
            GeneratorVersion==TemperateHillsMap::GeneratorVersion&&SizeMeters==1024.f;
        const int32 InteriorBudget=bInterior?TemperateBackdrop::FInteriorCanopy::Sectors*
            TemperateBackdrop::FInteriorCanopy::CrownLimitPerSector(Assets->BackdropTreeBudget):0;
        S.Job=Async(EAsyncExecution::ThreadPool,[Half=double(SizeMeters*50),WorldSeed=Seed,River=RiverPlan,Village=VillageSite,
            Palette=MoveTemp(Palette),CanopyBudget=Assets->BackdropTreeBudget-InteriorBudget,Version=GeneratorVersion]()
            {return TemperateBackdrop::Build(Half,WorldSeed,River,Palette,CanopyBudget,Version,Village);});
        // UDS owns the atmosphere, including the hills' retained height-fog
        // actor. The backdrop builds terrain only; it must not recolor whichever
        // fog component happens to be last in a peer's actor iteration order.
    }
    auto& S=*Backdrop;
    if(S.Pending)
    {
        if(!S.Job.IsReady())return;
        S.Result=S.Job.Get();S.Pending=false;
        BackdropColor=UTexture2D::CreateTransient(TemperateBackdrop::ColorSize,TemperateBackdrop::ColorSize,PF_B8G8R8A8);
        BackdropColor->SRGB=true;BackdropColor->NeverStream=true;BackdropColor->Filter=TF_Bilinear;
        auto& Mip=BackdropColor->GetPlatformData()->Mips[0];void* Data=Mip.BulkData.Lock(LOCK_READ_WRITE);
        FMemory::Memcpy(Data,S.Result->Colors.GetData(),S.Result->Colors.Num()*sizeof(FColor));Mip.BulkData.Unlock();BackdropColor->UpdateResource();
        S.Result->Colors.Empty();
        BackdropCoverage=UTexture2D::CreateTransient(S.Cells,S.Cells,PF_B8G8R8A8);
        BackdropCoverage->SRGB=false;BackdropCoverage->NeverStream=true;BackdropCoverage->Filter=TF_Nearest;
        auto& MaskMip=BackdropCoverage->GetPlatformData()->Mips[0];void* Mask=MaskMip.BulkData.Lock(LOCK_READ_WRITE);
        FMemory::Memcpy(Mask,S.Coverage.GetData(),S.Coverage.Num()*sizeof(FColor));MaskMip.BulkData.Unlock();BackdropCoverage->UpdateResource();
        BackdropMID=UMaterialInstanceDynamic::Create(Assets->BackdropMaterial.Get(),this);
        BackdropMID->SetTextureParameterValue(TEXT("BackdropColor"),BackdropColor);
        BackdropMID->SetTextureParameterValue(TEXT("TerrainCoverage"),BackdropCoverage);
        BackdropMID->SetScalarParameterValue(TEXT("PlayableHalf"),SizeMeters*50);
        BackdropMID->SetScalarParameterValue(TEXT("BackdropHalf"),TemperateBackdrop::OuterHalf);
        S.CoverageDirty=false;return;
    }
    if(S.Submitted<3)
    {
        AActor* Presentation=S.PresentationActor.Get();
        if(!Presentation)
        {
            // PCG derives its source bounds from every primitive owned by the
            // hills actor. Keep the 5.12 km horizon outside that owner so its
            // arrival cannot expand the playable vegetation generation bounds.
            FActorSpawnParameters Params;
            Params.Owner=this;Params.OverrideLevel=GetLevel();Params.ObjectFlags|=RF_Transient;
            Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            Presentation=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),FTransform::Identity,Params);
            if(!Presentation)return;
            auto* Root=NewObject<USceneComponent>(Presentation);
            Presentation->AddInstanceComponent(Root);Presentation->SetRootComponent(Root);
            Root->SetMobility(EComponentMobility::Movable);
            Root->SetupAttachment(RootComponent);Root->RegisterComponent();
            S.PresentationActor=Presentation;
        }
        auto* C=NewObject<UDynamicMeshComponent>(Presentation);
        Presentation->AddInstanceComponent(C);C->SetupAttachment(Presentation->GetRootComponent());
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);
        C->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);C->SetMaterial(0,BackdropMID);
        C->SetMesh(MoveTemp(S.Result->Meshes[S.Submitted++]));C->RegisterComponent();C->PrecachePSOs();BackdropMeshes.Add(C);
        if(S.Submitted==3)UE_LOG(LogTemp,Display,TEXT("HILLS_BACKDROP ready meshes=3 triangles=25088 color=1024 seed=%d"),Seed);
        return;
    }
    if(S.Result&&bCanopyAssetsReady)
    {
        SpawnBackdropCanopy();
        if(S.NextCanopyMesh>=S.Result->CanopyByMesh.Num())S.Result.Reset();
    }
    else if(bReady&&bCanopyAssetsReady&&Seed==TemperateHillsMap::Seed&&
        GeneratorVersion==TemperateHillsMap::GeneratorVersion&&SizeMeters==1024.f&&
        !GUsingNullRHI&&GetNetMode()!=NM_DedicatedServer)
    {
        if(auto* Presentation=S.PresentationActor.Get())
            S.Interior.Tick(*this,*Presentation,[this](int32 X,int32 Y,FTemperatePlacement& Site)
            {
                if(!TreeCandidate(X,Y,Site))return false;
                FVector Root=Site.Transform.GetLocation();
                const double FarGround=TemperateBackdrop::CoreTriangleHeight(Root.X,Root.Y,
                    SizeMeters*50.,Seed,RiverPlan,GeneratorVersion,VillageSite);
                Root.Z=FMath::Min(Root.Z,FarGround-5.);
                Site.Transform.SetLocation(Root);
                return true;
            });
    }
    if(S.CoverageDirty)
    {
        const uint32 Bytes=S.Coverage.Num()*sizeof(FColor);
        auto* Pixels=new uint8[Bytes];FMemory::Memcpy(Pixels,S.Coverage.GetData(),Bytes);
        auto* Region=new FUpdateTextureRegion2D(0,0,0,0,S.Cells,S.Cells);
        BackdropCoverage->UpdateTextureRegions(0,1,Region,S.Cells*sizeof(FColor),sizeof(FColor),Pixels,
            [](uint8* Data,const FUpdateTextureRegion2D* R){delete[] Data;delete R;});
        S.CoverageDirty=false;
    }
}

bool ATemperateHillsWorld::IsBackdropReady() const
{return (Assets&&Assets->BackdropMaterial.IsNull())||(Backdrop&&Backdrop->Submitted==3);}

void ATemperateHillsWorld::SetBackdropCellVisible(FIntPoint Cell,bool Visible)
{
    if(!Backdrop)return;auto& S=*Backdrop;
    if(Cell.X<0||Cell.Y<0||Cell.X>=S.Cells||Cell.Y>=S.Cells)return;
    const int32 I=Cell.Y*S.Cells+Cell.X;const FColor Value=Visible?FColor::White:FColor::Black;
    if(S.Coverage[I]!=Value){S.Coverage[I]=Value;S.CoverageDirty=true;}
}

void ATemperateHillsWorld::SpawnBackdropCanopy()
{
    if(!Backdrop||!Backdrop->Result||!Assets)return;
    AActor* Presentation=Backdrop->PresentationActor.Get();
    if(!Presentation)return;
    auto& S=*Backdrop;
    auto& Groups=S.Result->CanopyByMesh;
    // Register a single occupied HISM per tick, keeping the per-frame
    // component registration cost independent of the number of crown forms.
    while(S.NextCanopyMesh<Groups.Num())
    {
        const int32 MeshIndex=S.NextCanopyMesh++;
        UStaticMesh* Mesh=Assets->BackdropTrees.IsValidIndex(MeshIndex)?Assets->BackdropTrees[MeshIndex].Get():nullptr;
        TArray<FTransform>& Group=Groups[MeshIndex];
        if(!Mesh||Group.IsEmpty())continue;
        Group.RemoveAllSwap([this](const FTransform& Transform)
        {
            const FVector At=Transform.GetLocation();
            return ChapelSite.Clears(At.X,At.Y,550.)||VillageSite.Clears(At.X,At.Y,550.);
        });
        if(Group.IsEmpty())continue;
        // The authored alder impostor rotates around the original trunk pivot.
        // Geometric crowns seat on the lower rest bounds, excluding wind padding.
        const double Root=Mesh->GetName().StartsWith(TEXT("SM_HillsAlderCrown_"))?0.:
            Mesh->GetBoundingBox().Min.Z+Mesh->GetNegativeBoundsExtension().Z;
        for(FTransform& Transform:Group)
            Transform.AddToTranslation(FVector(0,0,-(Root+12.)*Transform.GetScale3D().Z));
        auto* C=NewObject<UHierarchicalInstancedStaticMeshComponent>(Presentation);
        Presentation->AddInstanceComponent(C);C->SetupAttachment(Presentation->GetRootComponent());
        C->SetMobility(EComponentMobility::Movable);
        C->SetStaticMesh(Mesh);
        C->SetCastShadow(false);C->SetCanEverAffectNavigation(false);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->bAffectDistanceFieldLighting=false;C->bVisibleInRayTracing=false;
        C->AddInstances(Group,false);
        C->RegisterComponent();C->PrecachePSOs();
        BackdropCanopy.Add(C);
        break;
    }
    if(S.NextCanopyMesh==Groups.Num()&&!BackdropCanopy.IsEmpty())
    {
        int32 Instances=0;
        for(const auto& Group:Groups)Instances+=Group.Num();
        UE_LOG(LogTemp,Display,TEXT("HILLS_BACKDROP canopy=%d components=%d seed=%d"),Instances,BackdropCanopy.Num(),Seed);
    }
}

void ATemperateHillsWorld::EndBackdrop()
{
    EndDayNightSky();
    if(HillsClouds){RemoveInstanceComponent(HillsClouds);HillsClouds->DestroyComponent();HillsClouds=nullptr;}
    for(const auto& Entry:BackdropCanopy)if(auto* C=Entry.Get()){C->GetOwner()->RemoveInstanceComponent(C);C->DestroyComponent();}
    BackdropCanopy.Empty();
    for(const auto& Entry:BackdropMeshes)if(auto* C=Entry.Get()){C->GetOwner()->RemoveInstanceComponent(C);C->DestroyComponent();}
    BackdropMeshes.Empty();BackdropMID=nullptr;BackdropColor=nullptr;BackdropCoverage=nullptr;
    if(Backdrop)if(AActor* Presentation=Backdrop->PresentationActor.Get())Presentation->Destroy();
    Backdrop.Reset();
}
