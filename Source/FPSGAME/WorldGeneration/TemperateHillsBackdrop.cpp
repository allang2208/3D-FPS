#include "TemperateHillsBackdrop.h"
#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "../FPSWeatherManager.h"
#include "Async/Async.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace TemperateBackdrop
{
constexpr int32 ColorSize=1024;
constexpr int32 RingRows=16;
struct FResult
{
    TArray<UE::Geometry::FDynamicMesh3> Meshes;
    TArray<FColor> Colors;
};

double Height(double X,double Y,double Half,int32 Seed,const TemperateRiver::FPlanPtr& River)
{
    const double Z=River?River->Height(X,Y,Seed):TemperateHillsSurface::Height(X,Y,Seed);
    const double Blend=FMath::SmoothStep(Half,150000.0,FMath::Max(FMath::Abs(X),FMath::Abs(Y)));
    // Distant low rolling ridges extend the biome, with no playable-world edits.
    return Z+Blend*(2200+TemperateHillsSurface::Noise(X*.0000035,Y*.0000035,Seed,1709)*4500);
}

double CoreTriangleHeight(double X,double Y,double Half,int32 Seed,const TemperateRiver::FPlanPtr& River)
{
    const double Step=Half*2/Grid;
    const double U=FMath::Clamp((X+Half)/Step,0.0,double(Grid)-1.e-6);
    const double V=FMath::Clamp((Y+Half)/Step,0.0,double(Grid)-1.e-6);
    const int32 IX=FMath::FloorToInt(U),IY=FMath::FloorToInt(V);
    const double A=U-IX,B=V-IY;
    auto H=[&](int32 DX,int32 DY){return Height(-Half+(IX+DX)*Step,-Half+(IY+DY)*Step,Half,Seed,River);};
    // Matches the diagonal used by both the proxy and streamed terrain.
    return A>=B?H(0,0)*(1-A)+H(1,0)*(A-B)+H(1,1)*B:
        H(0,0)*(1-B)+H(0,1)*(B-A)+H(1,1)*A;
}

TSharedPtr<FResult,ESPMode::ThreadSafe> Build(double Half,int32 Seed,TemperateRiver::FPlanPtr River)
{
    auto Result=MakeShared<FResult,ESPMode::ThreadSafe>();
    Result->Meshes.SetNum(3);
    auto Setup=[](UE::Geometry::FDynamicMesh3& M){M.EnableAttributes();};
    auto Vertex=[&](UE::Geometry::FDynamicMesh3& M,double X,double Y)
    {
        const double Z=Height(X,Y,Half,Seed,River);
        const FVector3f N=FVector3f(FVector(-(Height(X+100,Y,Half,Seed,River)-Height(X-100,Y,Half,Seed,River))/200,
            -(Height(X,Y+100,Half,Seed,River)-Height(X,Y-100,Half,Seed,River))/200,1).GetSafeNormal());
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
    Result->Colors.SetNumUninitialized(ColorSize*ColorSize);
    for(int32 Y=0;Y<ColorSize;++Y)for(int32 X=0;X<ColorSize;++X)
    {
        const double WX=((X+.5)/ColorSize*2-1)*OuterHalf,WY=((Y+.5)/ColorSize*2-1)*OuterHalf;
        const double Forest=FMath::SmoothStep(0.0,1.0,(TemperateHillsSurface::Noise(WX*.00014,WY*.00014,Seed,173)+.45)/1.05);
        const double Patch=TemperateHillsSurface::Noise(WX*.00035,WY*.00035,Seed,1711)*.5+.5;
        FLinearColor Color=FMath::Lerp(FLinearColor(.24f,.205f,.125f),FLinearColor(.105f,.135f,.09f),float(Forest*.8));
        Color=FMath::Lerp(Color,FLinearColor(.23f,.22f,.18f),float(Patch*.24));
        if(River&&FMath::Abs(WX)<Half&&FMath::Abs(WY)<Half)
        {
            const auto Bank=River->Sample(WX,WY);
            Color=FMath::Lerp(Color,FLinearColor(.075f,.12f,.10f),float(Bank.Wet*.8));
        }
        Result->Colors[Y*ColorSize+X]=Color.ToFColorSRGB();
    }
    return Result;
}
}

struct FTemperateBackdropState
{
    TFuture<TSharedPtr<TemperateBackdrop::FResult,ESPMode::ThreadSafe>> Job;
    TSharedPtr<TemperateBackdrop::FResult,ESPMode::ThreadSafe> Result;
    TArray<FColor> Coverage;
    TWeakObjectPtr<UExponentialHeightFogComponent> Fog;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    int32 Cells=0;
    int32 Submitted=0;
    bool Pending=true;
    bool CoverageDirty=true;
    double NextAtmosphere=0;
};

void ATemperateHillsWorld::TickBackdrop()
{
    if(!Assets||!Assets->BackdropMaterial.IsValid())return;
    if(!Backdrop)
    {
        Backdrop=MakeShared<FTemperateBackdropState>();auto& S=*Backdrop;
        S.Cells=FMath::RoundToInt(SizeMeters/64);S.Coverage.Init(FColor::Black,S.Cells*S.Cells);
        S.Job=Async(EAsyncExecution::ThreadPool,[Half=double(SizeMeters*50),WorldSeed=Seed,River=RiverPlan]()
            {return TemperateBackdrop::Build(Half,WorldSeed,River);});
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        {
            if(auto* F=It->FindComponentByClass<UExponentialHeightFogComponent>())
            {
                S.Fog=F;F->SetFogDensity(.014f);F->SetFogHeightFalloff(.08f);
                F->SetStartDistance(16000);F->SetFogMaxOpacity(.92f);
                // Local Normandy volumes also need this existing volumetric pass.
                F->SetVolumetricFog(true);
            }
            if(auto* Sky=It->FindComponentByClass<USkyAtmosphereComponent>())
            {Sky->SetMieScatteringScale(1.25f);Sky->SetAerialPespectiveViewDistanceScale(1.4f);}
            if(auto* Weather=Cast<AFPSWeatherManager>(*It))S.Weather=Weather;
        }
    }
    auto& S=*Backdrop;
    if(GetWorld()->GetTimeSeconds()>=S.NextAtmosphere)
    {
        S.NextAtmosphere=GetWorld()->GetTimeSeconds()+.25;
        if(auto* Fog=S.Fog.Get())
        {
            const auto* Weather=S.Weather.Get();const float Time=Weather?Weather->NormalizedDayTime:.4f;
            const float Sun=FMath::Sin((Time-.25f)*2*PI),Day=FMath::SmoothStep(-.12f,.35f,Sun);
            const FLinearColor Warm(.40f,.31f,.23f),Pale(.32f,.385f,.40f),Night(.003f,.0045f,.008f);
            const FLinearColor Sky=FMath::Lerp(Warm,Pale,FMath::SmoothStep(.0f,.4f,Sun));
            Fog->SetFogInscatteringColor(FMath::Lerp(Night,Sky,Day));
            Fog->SetDirectionalInscatteringColor(FMath::Lerp(Night,Sky*.55f,Day));
        }
    }
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
        auto* C=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(C);C->SetupAttachment(RootComponent);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);
        C->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);C->SetMaterial(0,BackdropMID);
        C->SetMesh(MoveTemp(S.Result->Meshes[S.Submitted++]));C->RegisterComponent();C->PrecachePSOs();BackdropMeshes.Add(C);
        if(S.Submitted==3){S.Result.Reset();UE_LOG(LogTemp,Display,TEXT("HILLS_BACKDROP ready meshes=3 triangles=25088 color=1024 seed=%d"),Seed);}
        return;
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

void ATemperateHillsWorld::EndBackdrop()
{
    for(const auto& Entry:BackdropMeshes)if(auto* C=Entry.Get()){RemoveInstanceComponent(C);C->DestroyComponent();}
    BackdropMeshes.Empty();BackdropMID=nullptr;BackdropColor=nullptr;BackdropCoverage=nullptr;
    Backdrop.Reset();
}
