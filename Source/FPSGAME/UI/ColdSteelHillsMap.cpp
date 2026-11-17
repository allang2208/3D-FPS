#include "ColdSteelHillsMap.h"
#include "ColdSteelHillsMapCheckCommandlet.h"
#include "../WorldGeneration/TemperateHillsGroundLayers.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Async/Async.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#if WITH_EDITOR
#include "ColdSteelMapReadback.h"
#include "AssetCompilingManager.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "ImageUtils.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#endif

namespace ColdSteelHillsMap
{
    using UE::Geometry::FDynamicMesh3;
    using TemperateHillsGround::FMapSource;
    constexpr int32 Cells = 256, Stride = Cells+1, ImageSize = 1024;
    constexpr double IntervalCm = 500.;

    struct FImage
    {
        FDynamicMesh3 Mesh;
        TArray<FColor> Overlay;
    };

    // Both world meshes use the SW--NE diagonal. In image space rows run south.
    FColor OverlayPixel(double Z, double CmPerPixel, bool Wet)
    {
        if (Wet) return FColor(61,113,133,217);
        if (CmPerPixel < UE_SMALL_NUMBER) return FColor::Transparent;
        const int32 Level = FMath::RoundToInt(Z/IntervalCm);
        const bool IndexLine = Level%5 == 0;
        const double DistancePx = FMath::Abs(Z-Level*IntervalCm)/CmPerPixel;
        const double Coverage = FMath::Clamp((IndexLine ? 1.35 : 1.)-DistancePx,0.,1.);
        return FColor(240,231,203,FMath::RoundToInt(Coverage*(IndexLine ? 215 : 150)));
    }

    struct FContourSample { double Height, Gradient; };

    FContourSample Interpolate(double A,double B,double C,double D,double U,double V,double PixelsPerCell)
    {
        const bool Upper = U+V<=1.;
        const double Du = Upper ? B-A : D-C, Dv = Upper ? C-A : D-B;
        const double Z = Upper ? A+U*Du+V*Dv : D+(U-1.)*Du+(V-1.)*Dv;
        return {Z,FMath::Sqrt(Du*Du+Dv*Dv)/PixelsPerCell};
    }

    TUniquePtr<FImage> Build(const FMapSource& Source, const TAtomic<bool>& Cancel)
    {
        auto Image = MakeUnique<FImage>();
        auto& Mesh = Image->Mesh;
        Mesh.EnableAttributes();
        auto& Attr = *Mesh.Attributes();
        Attr.SetNumUVLayers(3);
        Attr.EnablePrimaryColors();
        const double Step = Source.Bounds.GetSize().X/Cells;
        for (int32 Row=0; Row<Stride; ++Row)
        {
            if (Cancel.Load()) return nullptr;
            const double X = Source.Bounds.Max.X-Row*Step;
            for (int32 Col=0; Col<Stride; ++Col)
            {
                const double Y = Source.Bounds.Min.Y+Col*Step;
                Mesh.AppendVertex(FVector(X,Y,Source.Height(X,Y)));
            }
        }
        const auto Tri = [&](int32 A,int32 B,int32 C)
        {
            const int32 Id = Mesh.AppendTriangle(A,B,C);
            const UE::Geometry::FIndex3i Indices(A,B,C);
            Attr.PrimaryNormals()->SetTriangle(Id,Indices);
            Attr.PrimaryColors()->SetTriangle(Id,Indices);
            for (int32 UV=0; UV<3; ++UV) Attr.GetUVLayer(UV)->SetTriangle(Id,Indices);
        };
        for (int32 Row=0; Row<Stride; ++Row)
        {
            if (Cancel.Load()) return nullptr;
            for (int32 Col=0; Col<Stride; ++Col)
            {
                const int32 I = Row*Stride+Col;
                const FVector P = Mesh.GetVertex(I);
                const double W = Col ? Mesh.GetVertex(I-1).Z : Source.Height(P.X,P.Y-Step);
                const double E = Col<Cells ? Mesh.GetVertex(I+1).Z : Source.Height(P.X,P.Y+Step);
                const double N = Row ? Mesh.GetVertex(I-Stride).Z : Source.Height(P.X+Step,P.Y);
                const double S = Row<Cells ? Mesh.GetVertex(I+Stride).Z : Source.Height(P.X-Step,P.Y);
                const FVector Normal = FVector(S-N,W-E,2*Step).GetSafeNormal();
                const auto Bank = Source.River ? Source.River->Sample(P.X,P.Y) : TemperateRiver::FSample();
                auto Layers = TemperateHillsGround::Layers(P.X,P.Y,P.Z,Normal,Source.Seed,Bank,
                    Source.River?Source.River->RainforestWeight(P.X,P.Y):0.,
                    Source.River ? Source.River->Ecology : TemperateEcology::FProfile{});
                Layers.Habitat.Y = TemperateHillsGround::SurfaceMoisture((N+S+E+W)*.25,
                    P.Z,Step,Layers.Habitat.X,Source.Water,P.X,P.Y);
                Attr.PrimaryNormals()->AppendElement(FVector3f(Normal));
                Attr.PrimaryColors()->AppendElement(Layers.Color);
                Attr.GetUVLayer(0)->AppendElement(Layers.UV);
                Attr.GetUVLayer(1)->AppendElement(Layers.Habitat);
                Attr.GetUVLayer(2)->AppendElement(Layers.Upland);
                if (Row && Col)
                {
                    Tri(I-Stride-1,I-1,I-Stride);
                    Tri(I-Stride,I-1,I);
                }
            }
        }

        constexpr int32 PixelsPerCell = ImageSize/Cells;
        static_assert(ImageSize%Cells == 0);
        Image->Overlay.SetNumUninitialized(ImageSize*ImageSize);
        const double PixelStep = Step/PixelsPerCell;
        for (int32 Row=0; Row<ImageSize; ++Row)
        {
            if (Cancel.Load()) return nullptr;
            const double V = ((Row%PixelsPerCell)+.5)/PixelsPerCell;
            const double X = Source.Bounds.Max.X-(Row+.5)*PixelStep;
            for (int32 Col=0; Col<ImageSize; ++Col)
            {
                const double Y = Source.Bounds.Min.Y+(Col+.5)*PixelStep;
                const int32 I = (Row/PixelsPerCell)*Stride+Col/PixelsPerCell;
                const double U = ((Col%PixelsPerCell)+.5)/PixelsPerCell;
                const double A=Mesh.GetVertex(I).Z, B=Mesh.GetVertex(I+1).Z;
                const double C=Mesh.GetVertex(I+Stride).Z, D=Mesh.GetVertex(I+Stride+1).Z;
                const auto Sample = Interpolate(A,B,C,D,U,V,PixelsPerCell);
                const auto Bank = Source.River ? Source.River->Sample(X,Y) : TemperateRiver::FSample();
                const bool Wet = (Bank.Distance<Bank.HalfWidth && Source.Height(X,Y)<Bank.WaterZ) ||
                    (Source.Water && Source.Water->Sample(X,Y).Wet);
                Image->Overlay[Row*ImageSize+Col] = OverlayPixel(Sample.Height,Sample.Gradient,Wet);
            }
        }
        return Image;
    }
}

struct FColdSteelHillsMap::FJob
{
    TSharedRef<TAtomic<bool>,ESPMode::ThreadSafe> Cancel = MakeShared<TAtomic<bool>,ESPMode::ThreadSafe>(false);
    TFuture<TUniquePtr<ColdSteelHillsMap::FImage>> Image;
};

FColdSteelHillsMap::FColdSteelHillsMap(const ATemperateHillsWorld& Terrain) : Job(MakeUnique<FJob>())
{
    TemperateHillsGround::FMapSource Source;
    Terrain.CopyMapGround(Source);
    Job->Image = Async(EAsyncExecution::ThreadPool,[Source=MoveTemp(Source),Cancel=Job->Cancel]()
    {
        return ColdSteelHillsMap::Build(Source,*Cancel);
    });
}

FColdSteelHillsMap::~FColdSteelHillsMap() { Job->Cancel->Store(true); }
bool FColdSteelHillsMap::IsReady() const { return Job->Image.IsReady(); }

static UTextureRenderTarget2D* CaptureHillsGround(ATemperateHillsWorld& Terrain, UMaterialInterface* Ground,
    UE::Geometry::FDynamicMesh3&& Mesh)
{
    using namespace ColdSteelHillsMap;
    UWorld* World = Terrain.GetWorld();
    if (!Ground || !World || !World->Scene || !FApp::CanEverRender()) return nullptr;
    const FBox Bounds(Mesh.GetBounds());
    auto* Proxy = NewObject<UDynamicMeshComponent>(&Terrain);
    Proxy->SetMobility(EComponentMobility::Movable);
    Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Proxy->SetCanEverAffectNavigation(false);
    Proxy->SetCastShadow(false);
    Proxy->SetVisibleInSceneCaptureOnly(true);
    Proxy->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    Proxy->SetMaterial(0,Ground);
    Proxy->SetMesh(MoveTemp(Mesh));
    Proxy->RegisterComponentWithWorld(World);

    auto* Photo = NewObject<UTextureRenderTarget2D>();
    Photo->InitCustomFormat(ImageSize,ImageSize,PF_B8G8R8A8,false);
    auto* Camera = NewObject<USceneCaptureComponent2D>(&Terrain);
    Camera->bCaptureEveryFrame = Camera->bCaptureOnMovement = false;
    Camera->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Camera->ShowOnlyComponent(Proxy);
    Camera->CaptureSource = SCS_BaseColor;
    Camera->ProjectionType = ECameraProjectionMode::Orthographic;
    Camera->OrthoWidth = Bounds.GetSize().Y;
    Camera->bAutoCalculateOrthoPlanes = Camera->bUpdateOrthoPlanes = false;
    Camera->bUseCustomProjectionMatrix = true;
    constexpr double Clearance = 10000.;
    const FVector Eye(Bounds.GetCenter().X,Bounds.GetCenter().Y,Bounds.Max.Z+Clearance);
    Camera->CustomProjectionMatrix = FReversedZOrthoMatrix(Bounds.GetExtent().Y,Bounds.GetExtent().X,
        1./(Eye.Z-Bounds.Min.Z+Clearance),0.);
    Camera->SetWorldLocationAndRotation(Eye,FRotator(-90.,0.,0.));
    Camera->TextureTarget = Photo;
    Camera->RegisterComponentWithWorld(World);
    Camera->CaptureScene();
    Camera->DestroyComponent();
    Proxy->DestroyComponent();
    return Photo;
}

bool FColdSteelHillsMap::Finish(ATemperateHillsWorld& Terrain,UTextureRenderTarget2D*& Photo,UTexture2D*& Lines)
{
    using namespace ColdSteelHillsMap;
    auto Image = Job->Image.Consume();
    if (!Image) return false;
    Photo = CaptureHillsGround(Terrain,Terrain.GetMapGroundMaterial(),MoveTemp(Image->Mesh));
    if (!Photo) return false;
    Lines = UTexture2D::CreateTransient(ImageSize,ImageSize,PF_B8G8R8A8,NAME_None,
        TConstArrayView64<uint8>(reinterpret_cast<const uint8*>(Image->Overlay.GetData()),Image->Overlay.Num()*sizeof(FColor)));
    return Lines!=nullptr;
}

int32 UColdSteelHillsMapCheckCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    using namespace ColdSteelHillsMap;
    // A flat terrace at an exact multiple must not fill with lines. A 20 m
    // planar rise across one coarse cell crosses four distinct 5 m levels.
    if (OverlayPixel(500.,0.,false).A != 0) return 1;
    for (int32 Level=0; Level<=4; ++Level)
    {
        const double U=Level*.25;
        const auto Sample=Interpolate(0,2000,0,2000,U,.375,32.);
        if (!FMath::IsNearlyEqual(Sample.Height,Level*500.) || OverlayPixel(Sample.Height,Sample.Gradient,false).A==0)
            return 2;
        if (Level<4 && OverlayPixel(Sample.Height+250.,Sample.Gradient,false).A!=0) return 3;
    }
    const auto Saddle=Interpolate(0,1000,1000,0,.5,.5,32.);
    if (Saddle.Height!=1000. || OverlayPixel(0.,1.,true)!=OverlayPixel(500.,1.,true)) return 4;

    const FString LevelPath=TEXT("/Game/GameMaps/L_TemperateHills_Initial");
    UWorld* World=UEditorLoadingAndSavingUtils::LoadMap(FPackageName::LongPackageNameToFilename(LevelPath,FPackageName::GetMapPackageExtension()));
    if (!World || !FApp::CanEverRender()) return 5;
    TActorIterator<ATemperateHillsWorld> It(World);
    if (!It || !It->Assets) return 6;
    ATemperateHillsWorld& Terrain=**It;
    auto* Material=Terrain.Assets->GroundMaterial.LoadSynchronous();
    if (!Material) return 7;
    // This in-memory fixture represents a fresh hills world. Never save the level.
    Terrain.GeneratorVersion=2;
    FMapSource Source;
    Terrain.CopyMapGround(Source);
    TemperateEcology::Get();
    if (!Terrain.Assets->RiverMaterial.IsNull())
        Source.River=TemperateRiver::Generate(Source.Seed,Source.Bounds.GetExtent().X,
            FVector2D(Terrain.GetStartLocation()),Terrain.Assets->RiverBankReliefCm,Source.Version);
    Source.Water=TemperateForestWater::Generate(Source.Seed,Source.Bounds.GetExtent().X,Source.River,Source.Edits,Source.Version);
    auto Image=Build(Source,TAtomic<bool>(false));
    FAssetCompilingManager::Get().FinishAllCompilation();
    Material->SetForceMipLevelsToBeResident(false,false,30.f);
    auto* Photo=CaptureHillsGround(Terrain,Material,MoveTemp(Image->Mesh));
    TArray<FColor> Pixels;
    if (!Photo || !ColdSteelMapReadback::ReadPhoto(Photo,Pixels)) return 8;
    int32 Chromatic=0,Black=0,Contours=0,Wet=0;
    for (int32 I=0; I<Pixels.Num(); ++I)
    {
        auto& P=Pixels[I];
        const int32 Hi=FMath::Max3(P.R,P.G,P.B),Lo=FMath::Min3(P.R,P.G,P.B);
        Chromatic+=Hi-Lo>=8;
        Black+=Hi<4;
        const FColor Ink=Image->Overlay[I];
        Wet+=Ink.B>Ink.R && Ink.A>0;
        Contours+=Ink.R>Ink.B && Ink.A>0;
        const float Alpha=Ink.A/255.f;
        P=FMath::Lerp(FLinearColor(P),FLinearColor(Ink),Alpha).ToFColorSRGB();
        P.A=255;
    }
    UE_LOG(LogTemp,Display,TEXT("Hills M-map seed=%d ground=%s chromatic=%d black=%d contour=%d water=%d pixels=%d"),
        Source.Seed,*Material->GetPathName(),Chromatic,Black,Contours,Wet,Pixels.Num());
    TArray64<uint8> Png;
    FImageUtils::PNGCompressImageArray(ImageSize,ImageSize,Pixels,Png);
    if (!FFileHelper::SaveArrayToFile(Png,*FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("ColdSteelHillsMapCheck.png")))) return 9;
    return Chromatic>Pixels.Num()/10 && Black<Pixels.Num()/100 && Contours>0 && Wet>0 ? 0 : 10;
#else
    return 1;
#endif
}
