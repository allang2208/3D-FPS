#include "ForestVillageRegion.h"
#include "ForestVillageMap.h"
#include "ForestRootFit.h"
#include "ForestWoodDressing.h"
#include "ForestReferenceBoulders.h"
#include "ForestCourtyardShrubs.h"
#include "ForestNaniteAuthoring.h"
#include "Misc/SecureHash.h"
#include "LandscapeComponent.h"
#include "LandscapeLayerInfoObject.h"
#include "EngineUtils.h"
#include "ForestVillageRelief.h"
#include "Components/SceneComponent.h"
#include "LandscapeProxy.h"
#include "Misc/FileHelper.h"
#include "TemperateVillageSite.h"
#include "TemperateVillageGround.h"

namespace
{
constexpr int32 RegionSamples=ForestVillageMap::SideMeters+1;
// Within the reference footprint keep the exact 1 m knots, including along
// the two long sides of the platform. Away from it the terrain uses a 2 m grid.
bool FineGrid(int32 M,bool X,bool Hill)
{
    // Retain the original X knots on both west-forest pond shores. The new crest
    // and settlement lie inside that 1 m band; extend it north along their Y rows.
    return M>=-252 && M<(X?252:(Hill?612:398));
}
int32 NextKnot(int32 I, bool X,bool Hill)
{
    const int32 M=I+(X?ForestVillageMap::West:ForestVillageMap::South);
    return I+(FineGrid(M,X,Hill)?1:2);
}
int32 LowerKnot(double Grid, bool X,bool Hill)
{
    const int32 I=FMath::Clamp(FMath::FloorToInt(Grid),0,RegionSamples-2);
    const int32 M=I+(X?ForestVillageMap::West:ForestVillageMap::South);
    return FineGrid(M,X,Hill)?I:(I&~1);
}
}

AForestVillageRegion::AForestVillageRegion()
{
#if WITH_EDITOR
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=.12f;
#endif
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("RegionRoot"));
    Root->SetMobility(EComponentMobility::Static);
    SetRootComponent(Root);
}

bool AForestVillageRegion::HasGround() const { return HeightCm.Num()==RegionSamples*RegionSamples; }

int32 AForestVillageRegion::SettlementOffsetCm(int32 I,int32 J) const
{
    return HasSitedHill() ? ForestVillageRelief::SitedVertexOffset(SettlementOffsets,I,J)
                         : ForestVillageRelief::VertexOffset(I,J);
}

double AForestVillageRegion::DressingOffsetCm(double X,double Y) const
{
    if(!HasSitedHill()) return ForestVillageRelief::OffsetAt(X,Y);
    return ForestVillageRelief::SampleOffsets(SettlementOffsets,X-SettlementMinM.X*100.+ForestVillageRelief::MinX,
        Y-SettlementMinM.Y*100.+ForestVillageRelief::MinY);
}

bool AForestVillageRegion::InstallHillSite(const FString& Directory,FIntPoint MinM,double DatumCm)
{
#if WITH_EDITOR
    TArray<uint8> Bytes;
    constexpr int32 Count=ForestVillageRelief::Rows*ForestVillageRelief::Columns;
    if(!FFileHelper::LoadFileToArray(Bytes,*(Directory/TEXT("settlement.i16"))) || Bytes.Num()!=Count*sizeof(int16))
        return false;
    Modify();
    SettlementMinM=MinM;
    SettlementDatumCm=DatumCm;
    SettlementOffsets.SetNumUninitialized(Count);
    FMemory::Memcpy(SettlementOffsets.GetData(),Bytes.GetData(),Bytes.Num());
    WoodlandWater.Reset();
    return true;
#else
    return false;
#endif
}

FVector2f AForestVillageRegion::GetGatePaint(int32 Column,int32 Row) const
{
    constexpr int32 Width=119, Rows=9;
    if(GatePaint.Num()!=Width*Rows*2) return FVector2f::ZeroVector;
    const int32 Index=(FMath::Clamp(Row,0,Rows-1)*Width+FMath::Clamp(Column,0,Width-1))*2;
    return FVector2f(GatePaint[Index],GatePaint[Index+1])/255.f;
}

double AForestVillageRegion::GroundHeight(double X, double Y) const
{
    if(!HasGround()) return 0.;
    const double GX=FMath::Clamp(X*.01-ForestVillageMap::West,0.,double(RegionSamples-1));
    const double GY=FMath::Clamp(Y*.01-ForestVillageMap::South,0.,double(RegionSamples-1));
    const bool Hill=HasSitedHill();
    const int32 I=LowerKnot(GX,true,Hill), J=LowerKnot(GY,false,Hill);
    const int32 K=NextKnot(I,true,Hill), L=NextKnot(J,false,Hill);
    const double U=(GX-I)/(K-I), V=(GY-J)/(L-J);
    const double A=HeightCm[J*RegionSamples+I], D=HeightCm[L*RegionSamples+K];
    const double Base=U>=V ? A*(1.-U)+HeightCm[J*RegionSamples+K]*(U-V)+D*V :
                             A*(1.-V)+HeightCm[L*RegionSamples+I]*(V-U)+D*U;
    return Hill?Base:Base+ForestVillageRelief::OffsetAt(X,Y);
}

FTransform AForestVillageRegion::FitFloorDecal(double X,double Y,double YawDegrees,double Scale) const
{
    // Fit over the projected footprint so a thin decal box follows the slope of the ground.
    const double Radius=FMath::Max(30.,65.*Scale);
    const FVector Normal=FVector(GroundHeight(X-Radius,Y)-GroundHeight(X+Radius,Y),
        GroundHeight(X,Y-Radius)-GroundHeight(X,Y+Radius),2.*Radius).GetSafeNormal();
    const FQuat Heading(FVector::UpVector,FMath::DegreesToRadians(YawDegrees));
    const FVector Centre(X,Y,GroundHeight(X,Y)+2.);
    double Depth=10.*Scale;
    // The template faces down by 90 degrees. Its local X is the decal box half-depth.
    // At convex knots fit this dimension separately, leaving the leaf/soil footprint intact.
    for (int32 J=-3;J<=3;++J)
        for (int32 I=-3;I<=3;++I)
        {
            if (I*I+J*J>13) continue;
            const FVector Offset=Heading.RotateVector(FVector(61.*Scale*I/3.,80.*Scale*J/3.,0.));
            const double DZ=GroundHeight(X+Offset.X,Y+Offset.Y)-Centre.Z;
            const double Error=FMath::Abs(Offset.X*Normal.X+Offset.Y*Normal.Y+DZ*Normal.Z);
            Depth=FMath::Max(Depth,(Error+1.)/.72);
        }
    return FTransform(FQuat::FindBetweenNormals(FVector::UpVector,Normal)*Heading,
        Centre,FVector(Depth/10.,Scale,Scale));
}

double AForestVillageRegion::MapRoadWeight(double X,double Y) const
{
    constexpr int32 Side=ForestVillageMap::SideMeters/2;
    if(MapRoadPaint.Num()!=Side*Side) return 0.;
    const int32 I=FMath::Clamp(FMath::FloorToInt((X*.01-ForestVillageMap::West)*.5),0,Side-1);
    const int32 J=FMath::Clamp(FMath::FloorToInt((Y*.01-ForestVillageMap::South)*.5),0,Side-1);
    return MapRoadPaint[J*Side+I]/255.;
}

bool AForestVillageRegion::BakeMapRoads(const FString& Directory)
{
#if WITH_EDITOR
    constexpr int32 Side=ForestVillageMap::SideMeters/2;
    TArray<uint8> Paint, Road;
    if(!FFileHelper::LoadFileToArray(Paint,*(Directory/TEXT("paint.rg8"))) ||
        Paint.Num()!=RegionSamples*RegionSamples*2) return false;
    Road.SetNumUninitialized(Side*Side);
    for(int32 J=0;J<Side;++J)
        for(int32 I=0;I<Side;++I)
            Road[J*Side+I]=Paint[2*((2*J+1)*RegionSamples+2*I+1)];
    auto* Layer=LoadObject<ULandscapeLayerInfoObject>(nullptr,
        TEXT("/Game/Example/Maps/NaniteExample_sharedassets/C_LayerInfo.C_LayerInfo"));
    if(!Layer) return false;
    int32 Count=0;
    for(TActorIterator<ALandscapeProxy> It(GetWorld());It;++It)
    {
        if(!It->GetLevel()->GetOutermost()->GetName().EndsWith(TEXT("/L_ForestPathForest"))) continue;
        for(ULandscapeComponent* Component:It->LandscapeComponents)
        {
            if(!Component) continue;
            const FBox Box=Component->Bounds.GetBox();
            const FBox2D Map=ForestVillageMap::Bounds();
            const auto First=(FVector2D(Box.Min)-Map.Min)/200.-FVector2D(.5);
            const auto Last=(FVector2D(Box.Max)-Map.Min)/200.-FVector2D(.5);
            TArray<uint8> LayerCache;
            for(int32 J=FMath::Max(0,FMath::CeilToInt(First.Y));J<=FMath::Min(Side-1,FMath::FloorToInt(Last.Y));++J)
                for(int32 I=FMath::Max(0,FMath::CeilToInt(First.X));I<=FMath::Min(Side-1,FMath::FloorToInt(Last.X));++I)
                {
                    const FVector2D XY=Map.Min+200.*FVector2D(I+.5,J+.5);
                    const float W=Component->GetLayerWeightAtLocation(FVector(XY,0.),Layer,&LayerCache);
                    Road[J*Side+I]=uint8(FMath::RoundToInt(255.f*FMath::Clamp(W,0.f,1.f)));
                    ++Count;
                }
        }
    }
    if(!Count) return false;
    Modify();
    MapRoadPaint=MoveTemp(Road);
    MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

bool AForestVillageRegion::ExportForestSurface(ALandscapeProxy* Landscape, const FString& Filename)
{
#if WITH_EDITOR
    if(!Landscape) return false;
    TArray<float> Z;
    Z.Reserve(505*505);
    for(int32 Y=-252;Y<=252;++Y)
        for(int32 X=-252;X<=252;++X)
        {
            const FVector P(FMath::Clamp(100.*X,-25199.99,25199.99),FMath::Clamp(100.*Y,-25199.99,25199.99),0.);
            const auto H=Landscape->GetHeightAtLocation(P);
            if(!H.IsSet()) return false;
            Z.Add(H.GetValue());
        }
    FTemperateVillageSite Site;
    Site.bPlaced=true; Site.bHilltop=true; Site.bSideLane=true;
    Site.PadHalfX=7000.; Site.PadHalfY=5500.; Site.Shoulder=400.;
    Site.Axis=FVector2D(0,-1);
    Site.Ground=FVector(-11300,32300,Z[504*505+144]);
    const auto Chapel=Site.ChapelLot();
    // Export the unmodified foundation datum. Authored village relief is composed
    // with it once, by the runtime mesh, the PCG projection and the offline generator.
    for(int32 Y=252;Y<=397;++Y)
        for(int32 X=-172;X<=-54;++X)
        {
            const double Pad=Chapel.Grade(100.*X,100.*Y,Site.Ground.Z)+TemperateVillageGround::Offset(Site,100.*X,100.*Y);
            Z.Add(FMath::Lerp(double(Z[504*505+X+252]),Pad,FMath::SmoothStep(252.,258.,double(Y))));
        }
    return FFileHelper::SaveArrayToFile(MakeArrayView(reinterpret_cast<const uint8*>(Z.GetData()),Z.Num()*int32(sizeof(float))),*Filename);
#else
    return false;
#endif
}

#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshCompiler.h"
#include "PhysicsEngine/BodySetup.h"
#include "Misc/PackageName.h"
#include "UObject/SavePackage.h"

namespace
{
bool ExistingCell(int32 X,int32 Y,FIntPoint Site)
{
    return (X>=-252 && X<252 && Y>=-252 && Y<252) ||
           (X>=Site.X && X<Site.X+ForestVillageRelief::Columns-1 &&
            Y>=Site.Y && Y<Site.Y+ForestVillageRelief::Rows-1);
}
template<typename T>
T* AddPlacedComponent(AActor& Owner,FName Name)
{
    auto* C=NewObject<T>(&Owner,Name,RF_Transactional);
    Owner.AddInstanceComponent(C);
    C->SetupAttachment(Owner.GetRootComponent());
    C->SetMobility(EComponentMobility::Static);
    return C;
}

struct FSurfaceSample
{
    const TArray<uint8>& Blend;
    UMaterialInterface* Core;
    UMaterialInterface* Fringe;
    UStaticMeshComponent* Ground;
};

bool BakeTile(AForestVillageRegion& Owner,const TArray<int16>& Heights,const TArray<uint8>& Paint,
              UMaterialInterface* Material,int32 TileX,int32 TileY,const FSurfaceSample* Sample=nullptr,
              const TArray<float>* Reference=nullptr)
{
    const int32 X0=TileX*128,Y0=TileY*128;
    const int32 WX=ForestVillageMap::West,WY=ForestVillageMap::South;
    UMaterialInterface* Packed=nullptr;
    if(Reference && !Sample && Material)
    {
        if(Material->GetPathName()==ForestNaniteAuthoring::PackedMaterial)Packed=Material;
        else if(Material->GetPathName()==TEXT("/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference.MI_ForestReference"))
        {
            Packed=LoadObject<UMaterialInterface>(nullptr,ForestNaniteAuthoring::PackedMaterial);
            if(!Packed)return false;
        }
    }
    FMeshDescription Desc;
    FStaticMeshAttributes Attr(Desc);
    Attr.Register();
    auto Positions=Attr.GetVertexPositions();
    auto Normals=Attr.GetVertexInstanceNormals();
    auto UVs=Attr.GetVertexInstanceUVs();UVs.SetNumChannels(Sample?6:5);
    const FPolygonGroupID Group=Desc.CreatePolygonGroup();
    Attr.GetPolygonGroupMaterialSlotNames()[Group]=TEXT("Ground");
    FPolygonGroupID Core,Fringe;
    if(Sample)
    {
        Core=Desc.CreatePolygonGroup(); Fringe=Desc.CreatePolygonGroup();
        Attr.GetPolygonGroupMaterialSlotNames()[Core]=TEXT("ForestSample");
        Attr.GetPolygonGroupMaterialSlotNames()[Fringe]=TEXT("ForestFringe");
    }
    TMap<int32,FVertexInstanceID> Vertices;
    auto Vertex=[&](int32 I,int32 J)
    {
        const int32 Id=J*RegionSamples+I;
        if(const auto* Old=Vertices.Find(Id)) return *Old;
        const FVertexID V=Desc.CreateVertex();
        const int32 MX=I+WX,MY=J+WY;
        const bool InStudy=FMath::Abs(MX)<=252 && FMath::Abs(MY)<=252;
        const float Z=Reference && InStudy?(*Reference)[(MY+252)*505+MX+252]:float(Heights[Id]);
        Positions[V]=FVector3f(100.f*(I-X0),100.f*(J-Y0),Z);
        const FVertexInstanceID VI=Desc.CreateVertexInstance(V);
        const int32 Left=FMath::Max(0,I-1),Right=FMath::Min(RegionSamples-1,I+1);
        const int32 Down=FMath::Max(0,J-1),Up=FMath::Min(RegionSamples-1,J+1);
        Normals[VI]=FVector3f(-(Heights[J*RegionSamples+Right]-Heights[J*RegionSamples+Left])/(100.f*(Right-Left)),
                              -(Heights[Up*RegionSamples+I]-Heights[Down*RegionSamples+I])/(100.f*(Up-Down)),1.f).GetSafeNormal();
        UVs.Set(VI,0,FVector2f(MX,MY));
        if(Reference)
        {
            // Match LandscapeVertexFactory's layer coordinates and original actor transform.
            UVs.Set(VI,0,FVector2f(MX+252,MY+252));
            UVs.Set(VI,1,FVector2f(MX+252,(Z-100.f)/10.f));
            UVs.Set(VI,2,FVector2f(MY+252,(Z-100.f)/10.f));
        }
        UVs.Set(VI,4,FVector2f(Paint[Id*2]/255.f,Paint[Id*2+1]/255.f));
        if(Packed)UVs.Set(VI,3,UVs.Get(VI,4));
        if(Sample)
        {
            UVs.Set(VI,3,FVector2f(Sample->Blend[Id]/255.f,0.f));
            UVs.Set(VI,5,FVector2f(float(I+WX),float(J+WY)));
        }
        Vertices.Add(Id,VI);
        return VI;
    };
    const bool Hill=Owner.HasSitedHill();
    for(int32 J=Y0;J<Y0+128;J=NextKnot(J,false,Hill))
        for(int32 I=X0;I<X0+128;I=NextKnot(I,true,Hill))
        {
            if(ExistingCell(WX+I,WY+J,Owner.GetSettlementMinM())) continue;
            const int32 K=NextKnot(I,true,Hill), L=NextKnot(J,false,Hill);
            const auto A=Vertex(I,J),B=Vertex(K,J),C=Vertex(I,L),D=Vertex(K,L);
            const FVertexInstanceID T0[]={A,D,B}, T1[]={A,C,D};
            FPolygonGroupID Face=Group;
            if(Sample)
            {
                const auto& W=Sample->Blend;
                const uint8 a=W[J*RegionSamples+I],b=W[J*RegionSamples+K],c=W[L*RegionSamples+I],d=W[L*RegionSamples+K];
                if(a==255 && b==255 && c==255 && d==255) Face=Core;
                else if(a||b||c||d) Face=Fringe;
            }
            Desc.CreateTriangle(Face,MakeArrayView(T0));
            Desc.CreateTriangle(Face,MakeArrayView(T1));
            if(Reference)
            {
                auto Seal=[&](FVertexInstanceID P,FVertexInstanceID Q,FVector3f Inward)
                {
                    // The Landscape's boundary morphs with LOD. Tuck a return below that edge.
                    auto Lower=[&](FVertexInstanceID Top)
                    {
                        const auto V=Desc.CreateVertex();
                        Positions[V]=Positions[Desc.GetVertexInstanceVertex(Top)]+Inward+FVector3f(0,0,-90);
                        const auto VI=Desc.CreateVertexInstance(V);
                        Normals[VI]=Normals[Top];
                        for(int32 Ch=0;Ch<5;++Ch) UVs.Set(VI,Ch,UVs.Get(Top,Ch));
                        return VI;
                    };
                    const auto U=Lower(P),V=Lower(Q);
                    const FVertexInstanceID S0[]={P,U,Q},S1[]={Q,U,V};
                    Desc.CreateTriangle(Face,MakeArrayView(S0));
                    Desc.CreateTriangle(Face,MakeArrayView(S1));
                };
                if(ExistingCell(WX+I-1,WY+J,Owner.GetSettlementMinM())) Seal(A,C,{-40,0,0});
                if(ExistingCell(WX+K,WY+J,Owner.GetSettlementMinM())) Seal(D,B,{40,0,0});
                if(ExistingCell(WX+I,WY+J-1,Owner.GetSettlementMinM())) Seal(B,A,{0,-40,0});
                if(ExistingCell(WX+I,WY+L,Owner.GetSettlementMinM())) Seal(C,D,{0,40,0});
            }
        }
    if(!Vertices.Num()) return true;
    const FString Name=FString::Printf(TEXT("SM_ForestGround_%02d_%02d"),TileX,TileY);
    const FString Path=FString(Reference?TEXT("/Game/ForestPathStudy/VillageRegion/Reference/Terrain/"):
        Sample?TEXT("/Game/ForestPathStudy/VillageRegion/SurfaceSample/Terrain/"):
        TEXT("/Game/ForestPathStudy/VillageRegion/Terrain/"))+Name;
    UPackage* Pkg=CreatePackage(*Path);
    Pkg->FullyLoad();
    auto* Mesh=FindObject<UStaticMesh>(Pkg,*Name);
    if(!Mesh) Mesh=NewObject<UStaticMesh>(Pkg,*Name,RF_Public|RF_Standalone);
    Mesh->Modify();
    Mesh->GetStaticMaterials().Reset();
    Mesh->GetStaticMaterials().Emplace(Packed?Packed:Material,TEXT("Ground"));
    if(Sample)
    {
        Mesh->GetStaticMaterials().Emplace(Sample->Core,TEXT("ForestSample"));
        Mesh->GetStaticMaterials().Emplace(Sample->Fringe,TEXT("ForestFringe"));
    }
    if(!Mesh->GetNumSourceModels()) Mesh->AddSourceModel();
    FStaticMeshSourceModel& Source=Mesh->GetSourceModel(0);
    Source.BuildSettings.bGenerateLightmapUVs=false;
    Source.BuildSettings.bRecomputeNormals=false;
    Source.BuildSettings.bRecomputeTangents=true;
    Source.BuildSettings.bUseFullPrecisionUVs=true;
    Mesh->CreateMeshDescription(0,MoveTemp(Desc));
    Mesh->CommitMeshDescription(0);
    Mesh->CreateBodySetup();
    Mesh->GetBodySetup()->CollisionTraceFlag=CTF_UseComplexAsSimple;
    if(Packed)ForestNaniteAuthoring::Configure(*Mesh,true);
    Mesh->Build(false);
    FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});
    FAssetRegistryModule::AssetCreated(Mesh);
    Pkg->MarkPackageDirty();
    FSavePackageArgs Args; Args.TopLevelFlags=RF_Public|RF_Standalone;
    if(!UPackage::SavePackage(Pkg,Mesh,*FPackageName::LongPackageNameToFilename(Path,FPackageName::GetAssetPackageExtension()),Args)) return false;
    if(Sample)
    {
        Sample->Ground->SetStaticMesh(Mesh);
        return true;
    }
    if(auto* Existing=FindObject<UStaticMeshComponent>(&Owner,*Name))
    {
        Existing->SetStaticMesh(Mesh);
        return true;
    }
    auto* Ground=AddPlacedComponent<UStaticMeshComponent>(Owner,*Name);
    Ground->SetRelativeLocation(FVector((WX+X0)*100.,(WY+Y0)*100.,0.));
    Ground->SetStaticMesh(Mesh);
    Ground->SetCollisionProfileName(TEXT("BlockAll"));
    Ground->ComponentTags.Add(TEXT("HillsGround"));
    Ground->RegisterComponent();
    return true;
}
}
#endif

FVector2f AForestVillageRegion::ReferencePaintAt(int32 I,int32 J) const
{
    const int32 Index=2*(J*ForestVillageRelief::Columns+I);
    return SettlementPaint.IsValidIndex(Index+1)?FVector2f(SettlementPaint[Index],SettlementPaint[Index+1])/255.f:FVector2f::ZeroVector;
}

bool AForestVillageRegion::BakeReferenceSurface(const FString& Directory,UMaterialInterface* Material)
{
#if WITH_EDITOR
    TArray<uint8> Raw,Paint,Study;
    constexpr int32 Cells=RegionSamples*RegionSamples;
    if(!Material || !FFileHelper::LoadFileToArray(Raw,*(Directory/TEXT("region.i16"))) || Raw.Num()!=Cells*2 ||
        !FFileHelper::LoadFileToArray(Paint,*(Directory/TEXT("paint.rg8"))) || Paint.Num()!=Cells*2 ||
        !FFileHelper::LoadFileToArray(Study,*(Directory/TEXT("reference.f32"))) || Study.Num()<505*505*4) return false;
    TArray<float> Border;
    Border.SetNumUninitialized(505*505);
    FMemory::Memcpy(Border.GetData(),Study.GetData(),Border.Num()*sizeof(float));
    Modify();
    HeightCm.SetNumUninitialized(Cells);
    FMemory::Memcpy(HeightCm.GetData(),Raw.GetData(),Raw.Num());
    for(int32 Y=0;Y<8;++Y) for(int32 X=0;X<8;++X)
        if(!BakeTile(*this,HeightCm,Paint,Material,X,Y,nullptr,&Border)) return false;
    ReferenceSurface=Material;
    SettlementPaint.Reset();
    for(int32 J=0;J<ForestVillageRelief::Rows;++J)
        SettlementPaint.Append(Paint.GetData()+2*((SettlementMinM.Y+J-ForestVillageMap::South)*RegionSamples+
            SettlementMinM.X-ForestVillageMap::West),2*ForestVillageRelief::Columns);
    return BakeMapRoads(Directory);
#else
    return false;
#endif
}

bool AForestVillageRegion::ApplySurfaceSample(const FString& Directory,UMaterialInterface* Surface,
    UMaterialInterface* Transition,UMaterialInterface* Gate)
{
#if WITH_EDITOR
    TArray<uint8> Raw,Paint,Blend,Apron;
    constexpr int32 Cells=RegionSamples*RegionSamples;
    if(!HasGround() || !Surface || !Transition || !Gate ||
       !FFileHelper::LoadFileToArray(Raw,*(Directory/TEXT("region.i16"))) || Raw.Num()!=2*Cells ||
       !FFileHelper::LoadFileToArray(Paint,*(Directory/TEXT("paint.rg8"))) || Paint.Num()!=2*Cells ||
       !FFileHelper::LoadFileToArray(Blend,*(Directory/TEXT("sample.r8"))) || Blend.Num()!=Cells ||
       !FFileHelper::LoadFileToArray(Apron,*(Directory/TEXT("apron.rg8"))) || Apron.Num()!=119*9*2) return false;
    auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/MI_EastRiverRoad.MI_EastRiverRoad"));
    if(!Base) return false;
    Modify();
    FMemory::Memcpy(HeightCm.GetData(),Raw.GetData(),Raw.Num());
    for(int32 Y=0;Y<8;++Y) for(int32 X=0;X<8;++X)
    {
        const int32 I=X*128,J=Y*128;
        bool Touched=false;
        for(int32 Row=J;Row<=J+128 && !Touched;++Row)
            for(int32 Col=I;Col<=I+128;++Col) if(Blend[Row*RegionSamples+Col]) { Touched=true; break; }
        if(!Touched) continue;
        const FName Name(*FString::Printf(TEXT("SM_ForestGround_%02d_%02d"),X,Y));
        auto* Ground=FindObject<UStaticMeshComponent>(this,*Name.ToString());
        if(!Ground) return false;
        const FSurfaceSample Sample{Blend,Surface,Transition,Ground};
        if(!BakeTile(*this,HeightCm,Paint,Base,X,Y,&Sample)) return false;
    }
    GateSurface=Gate;
    GatePaint=MoveTemp(Apron);
    if(!BakeMapRoads(Directory)) return false;
    MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

bool AForestVillageRegion::BakeGround(const FString& Directory)
{
#if WITH_EDITOR
    TArray<uint8> Raw,Paint;
    if(!FFileHelper::LoadFileToArray(Raw,*(Directory/TEXT("region.i16"))) || Raw.Num()!=RegionSamples*RegionSamples*2 ||
       !FFileHelper::LoadFileToArray(Paint,*(Directory/TEXT("paint.rg8"))) || Paint.Num()!=RegionSamples*RegionSamples*2) return false;
    auto* Mat=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/MI_EastRiverRoad.MI_EastRiverRoad"));
    if(!Mat) return false;
    HeightCm.SetNumUninitialized(RegionSamples*RegionSamples);
    FMemory::Memcpy(HeightCm.GetData(),Raw.GetData(),Raw.Num());
    for(int32 Y=0;Y<8;++Y)
        for(int32 X=0;X<8;++X)
            if(!BakeTile(*this,HeightCm,Paint,Mat,X,Y)) return false;
    return true;
#else
    return false;
#endif
}

#if WITH_EDITOR
UMaterialInterface* AForestVillageRegion::HillsGrassMaterial(UStaticMesh* Mesh)
{
    FString Role=Mesh->GetName();
    Role.RemoveFromStart(TEXT("SM_RainforestGrass"));
    const FString Name=TEXT("MI_HillsGrass")+Role;
    const FString Path=TEXT("/Game/ForestPathStudy/VillageRegion/GrassCover/")+Name+TEXT(".")+Name;
    return LoadObject<UMaterialInterface>(nullptr,*Path);
}

bool BakeForestRegionPCG(AForestVillageRegion& Owner,const TArray<TArray<FTransform>>& Hills,const TArray<TArray<FTransform>>& Road,FName OnlyTheme,
    UStaticMesh* const* Meshes,UInstancedStaticMeshComponent* const* Templates,int32 FirstTalus);
#endif

bool AForestVillageRegion::ReplacesStudyTree(const FVector& Pos) const
{
    const auto* Site=HarvestTreeSite({FMath::FloorToInt32(Pos.X/1200.),FMath::FloorToInt32(Pos.Y/1200.)});
    return Site && FMath::Square(Pos.X-Site->X)+FMath::Square(Pos.Y-Site->Y)<4.;
}

bool AForestVillageRegion::BakeVegetation(const FString& PointsFile,const TArray<UInstancedStaticMeshComponent*>& StudyMeshes,FName OnlyTheme)
{
#if WITH_EDITOR
    const FString IdentityFile=FPaths::GetPath(PointsFile)/TEXT("theme.id");
    if(!OnlyTheme.IsNone() || FPaths::FileExists(IdentityFile))
    {
        FString Key;
        if(!FFileHelper::LoadFileToString(Key,*IdentityFile))return false;
        const FName SavedTheme(*Key.TrimStartAndEnd());
        if((SavedTheme!=TEXT("RoadLandscape") && SavedTheme!=TEXT("HillsLandscape")) ||
           (!OnlyTheme.IsNone() && OnlyTheme!=SavedTheme))return false;
        OnlyTheme=SavedTheme;
    }
    const bool OnlyRoad=OnlyTheme==TEXT("RoadLandscape");
    const FString SitesFile=FPaths::GetPath(PointsFile)/TEXT("harvest-trees.f32");
    if(!OnlyRoad && FPaths::FileExists(SitesFile))
    {
        TArray<uint8> Bytes;
        if(!FFileHelper::LoadFileToArray(Bytes,*SitesFile) || Bytes.Num()%sizeof(FVector3f))return false;
        Modify();
        HarvestTreeSites.Reset();
        for(int32 I=0;I<Bytes.Num();I+=sizeof(FVector3f))
        {
            FVector3f P;
            FMemory::Memcpy(&P,Bytes.GetData()+I,sizeof(P));
            const double RootZ=ForestRootFit::Seat({P.X,P.Y},38.,0.,[this](double X,double Y){return GroundHeight(X,Y);});
            HarvestTreeSites.Add({FMath::FloorToInt32(P.X/1200.),FMath::FloorToInt32(P.Y/1200.)},
                FVector4f(P.X,P.Y,RootZ,P.Z));
        }
    }
    const FString ReplacedFile=FPaths::GetPath(PointsFile)/TEXT("study-granite.i32");
    if(!OnlyRoad && FPaths::FileExists(ReplacedFile))
    {
        TArray<uint8> Bytes;
        if(!FFileHelper::LoadFileToArray(Bytes,*ReplacedFile) || Bytes.Num()%sizeof(FIntPoint))return false;
        Modify();
        ReplacedStudyRocks.Reset();
        for(int32 I=0;I<Bytes.Num();I+=sizeof(FIntPoint))
        {
            FIntPoint Pt; FMemory::Memcpy(&Pt,Bytes.GetData()+I,sizeof(Pt)); ReplacedStudyRocks.Add(Pt);
        }
    }
    TArray<FString> ReferencePaths;
    const FString Palette=FPaths::GetPath(PointsFile)/TEXT("reference-meshes.txt");
    const bool bReference=FFileHelper::LoadFileToStringArray(ReferencePaths,*Palette) && !ReferencePaths.IsEmpty();
    const int32 Count=bReference?16+ReferencePaths.Num():15;
    const TCHAR* Names[]={TEXT("SM_EuropeanHornbeam_Forest_04"),TEXT("SM_EuropeanHornbeam_Forest_05"),
        TEXT("SM_CommonHazel_Forest_01"),TEXT("SM_CommonHazel_Forest_02")};
    TArray<UStaticMesh*> Meshes; Meshes.Init(nullptr,Count);
    UInstancedStaticMeshComponent* Templates[4]={};
    for(auto* Source:StudyMeshes)
        if(Source && Source->GetStaticMesh())
            for(int32 I=0;I<4;++I)
                if(Source->GetStaticMesh()->GetFName()==Names[I])
                { Meshes[I]=Source->GetStaticMesh(); Templates[I]=Source; }
    const TCHAR* Scans[]={TEXT("xjiifd1"),TEXT("xjijdiz"),TEXT("relu7"),TEXT("rioqm")};
    for(int32 I=0;I<4;++I)
    {
        const FString Stem=FString::Printf(TEXT("%s_tier_%d"),Scans[I],I<2?1:3);
        Meshes[I+4]=LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Game/ForestPathStudy/Scans/%s/%s/StaticMeshes/%s.%s"),Scans[I],*Stem,*Stem,*Stem));
    }
    Meshes[8]=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/ForestPathStudy/Scans/rbcuh/rbcuh_tier_1/StaticMeshes/SM_rbcuh_VarA.SM_rbcuh_VarA"));
    Meshes[9]=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/ForestPathStudy/Scans/rbpir/rbpiR_tier_1/StaticMeshes/SM_rbpiR_VarB.SM_rbpiR_VarB"));
    const TCHAR* GrassNames[]={TEXT("Low"),TEXT("Spreading"),TEXT("Tall")};
    for(int32 I=0;I<3;++I)
    {
        const FString Name=FString(TEXT("SM_RainforestGrass"))+GrassNames[I];
        const FString Path=TEXT("/Game/WorldGeneration/TemperateHills/WetForest/CarpetGrass/")+Name+TEXT(".")+Name;
        Meshes[12+I]=LoadObject<UStaticMesh>(nullptr,*Path);
    }
    TArray<FString> RetiredPaths;
    FFileHelper::LoadFileToStringArray(RetiredPaths,*(FPaths::ProjectConfigDir()/TEXT("ForestVillageRetiredWood.txt")));
    TBitArray<> RetiredSlots(false,Count);
    TBitArray<> GraniteSlots(false,Count);
    for(int32 I=0;I<ReferencePaths.Num();++I)
    {
        if(RetiredPaths.Contains(ReferencePaths[I]))
        {
            RetiredSlots[16+I]=true;
            continue;
        }
        Meshes[16+I]=LoadObject<UStaticMesh>(nullptr,*ReferencePaths[I]);
        GraniteSlots[16+I]=ReferencePaths[I].StartsWith(TEXT("/Game/ForestPathStudy/VillageRegion/Granite/"));
    }
    for(int32 I=0;I<Count;++I)
        if(I!=10 && I!=11 && I!=15 && !RetiredSlots[I] && !Meshes[I]) { UE_LOG(LogTemp,Error,TEXT("Forest region palette missing slot %d"),I); return false; }
    struct FPoint {float X,Y,Yaw,Size; int32 Slot;};
    static_assert(sizeof(FPoint)==20);
    TArray<uint8> Bytes;
    if(!FFileHelper::LoadFileToArray(Bytes,*PointsFile) || (OnlyTheme.IsNone() && Bytes.IsEmpty()) || Bytes.Num()%sizeof(FPoint)) return false;
    FVector2D Roots[4];
    for(int32 I=0;I<4;++I) Roots[I]=ForestRootFit::Measure(Meshes[I]);
    TArray<ForestWoodDressing::FSupport> Wood;
    Wood.SetNum(Count);
    for(int32 I=0;I<Count;++I)
    {
        Wood[I]=ForestWoodDressing::Measure(Meshes[I]);
        if(Wood[I].Type!=ForestWoodDressing::EKind::None && Wood[I].Feet.IsEmpty())
        {
            UE_LOG(LogTemp,Error,TEXT("No ground support geometry for %s"),*Meshes[I]->GetPathName());
            return false;
        }
    }
    TArray<TArray<FTransform>> Hills,Road;
    Hills.SetNum(Count); Road.SetNum(Count);
    TArray<uint8> Bits;
    const FString MaskFile=FPaths::ChangeExtension(PointsFile,TEXT("roadbits"));
    if(OnlyTheme.IsNone() && FPaths::FileExists(MaskFile))
    {
        FSHAHash Digest;
        FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num(),Digest.Hash);
        if(!FFileHelper::LoadFileToArray(Bits,*MaskFile) || Bits.Num()!=sizeof(Digest.Hash)+(Bytes.Num()/sizeof(FPoint)+7)/8 ||
           FMemory::Memcmp(Bits.GetData(),Digest.Hash,sizeof(Digest.Hash))!=0)
        {
            UE_LOG(LogTemp,Error,TEXT("Forest theme ownership is stale for %s. Rebuild the partition from the current centre lines."),*PointsFile);
            return false;
        }
    }
    for(int32 Offset=0;Offset<Bytes.Num();Offset+=sizeof(FPoint))
    {
        FPoint P; FMemory::Memcpy(&P,Bytes.GetData()+Offset,sizeof(P));
        if(!Hills.IsValidIndex(P.Slot) || P.Slot==15)return false;
        if(RetiredSlots[P.Slot])continue;
        const int32 Index=Offset/sizeof(FPoint);
        // Historical inputs have no ownership file. Keep all their points, using the painted road as a fallback.
        const bool BankSedge=Meshes[P.Slot] && Meshes[P.Slot]->GetFName()==TEXT("SM_RiverDense_grass_04_03_mesh");
        if(OnlyRoad && BankSedge)
        {
            UE_LOG(LogTemp,Error,TEXT("Pond bank sedge belongs to the hills theme."));
            return false;
        }
        const bool OnRoad=OnlyRoad || (!BankSedge && OnlyTheme.IsNone() && (Bits.Num() ?
            (Bits[sizeof(FSHAHash::Hash)+Index/8]&(1u<<(Index%8)))!=0 : MapRoadWeight(P.X,P.Y)>.5));
        auto& Transforms=OnRoad?Road:Hills;
        if(P.Slot==10 || P.Slot==11)
        {
            Transforms[P.Slot].Add(FitFloorDecal(P.X,P.Y,P.Yaw,P.Size));
            continue;
        }
        if(Wood[P.Slot].Type!=ForestWoodDressing::EKind::None)
        {
            FTransform Pose;
            double Scale=P.Size;
            if(!bReference)
            {
                const FVector Extent=Meshes[P.Slot]->GetBoundingBox().GetSize();
                Scale/=FMath::Max(1.,FMath::Max(Extent.X,Extent.Y));
            }
            if(ForestWoodDressing::Fit(*this,Wood[P.Slot],FVector2D(P.X,P.Y),P.Yaw,Scale,Pose))
                Transforms[P.Slot].Add(Pose);
            continue;
        }
        const FBox Box=Meshes[P.Slot]->GetBoundingBox();
        if(P.Slot>=12 && P.Slot<=14)
        {
            if (CliffExposureMask.Num()==RegionSamples*RegionSamples)
            {
                const int32 I=FMath::Clamp(FMath::RoundToInt(P.X*.01)-ForestVillageMap::West,0,RegionSamples-1);
                const int32 J=FMath::Clamp(FMath::RoundToInt(P.Y*.01)-ForestVillageMap::South,0,RegionSamples-1);
                const uint8 Rock=CliffExposureMask[J*RegionSamples+I];
                const uint32 Seed=HashCombineFast(GetTypeHash(P.X),GetTypeHash(P.Y));
                if (Rock>80 && (Seed % 175u)<uint32(Rock-80)) continue;
            }
            const FVector RestMin=Box.Min+Meshes[P.Slot]->GetNegativeBoundsExtension();
            const FVector RestMax=Box.Max-Meshes[P.Slot]->GetPositiveBoundsExtension();
            const double Scale=P.Size/FMath::Max(1.,RestMax.Z-RestMin.Z);
            const FVector Normal=FVector(GroundHeight(P.X-50,P.Y)-GroundHeight(P.X+50,P.Y),
                GroundHeight(P.X,P.Y-50)-GroundHeight(P.X,P.Y+50),100.).GetSafeNormal();
            const FVector Up=FMath::Lerp(FVector::UpVector,Normal,.55).GetSafeNormal();
            const FQuat Rotation=FQuat(Up,FMath::DegreesToRadians(double(P.Yaw)))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            const FVector Root(P.X,P.Y,GroundHeight(P.X,P.Y)-.8);
            Transforms[P.Slot].Emplace(Rotation,Root-Up*RestMin.Z*Scale,FVector(Scale));
            continue;
        }
        const auto Size=Box.GetSize();
        const bool Floor=(P.Slot>=4 && P.Slot<8) || P.Slot>=16;
        const double Scale=bReference?P.Size:Floor?P.Size/FMath::Max(Size.X,Size.Y):P.Slot>=2 && P.Slot<4?P.Size/Size.Z:P.Size;
        const FVector Up=Floor?FVector(GroundHeight(P.X-50,P.Y)-GroundHeight(P.X+50,P.Y),
            GroundHeight(P.X,P.Y-50)-GroundHeight(P.X,P.Y+50),100.).GetSafeNormal():FVector::UpVector;
        const FQuat Rotation=FQuat(Up,FMath::DegreesToRadians(double(P.Yaw)))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
        FVector Pos(P.X,P.Y,GroundHeight(P.X,P.Y));
        if(GraniteSlots[P.Slot])
            Pos-=Rotation.RotateVector(FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z)*Scale)+Up*FMath::Clamp(Size.Z*Scale*.08,1.,20.);
        else if(Floor && P.Slot>=16) Pos-=Up*.8; // Source scan pivots are placed at the sampled surface.
        else if(Floor) Pos-=Rotation.RotateVector(FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z)*Scale)+Up*(P.Slot<6?2.:.8);
        else if(P.Slot<4)
            Pos.Z=ForestRootFit::Seat(FVector2D(Pos),Roots[P.Slot].X*Scale,Roots[P.Slot].Y*Scale,
                [this](double X,double Y){return GroundHeight(X,Y);});
        else Pos.Z-=.5;
        Transforms[P.Slot].Emplace(Rotation,Pos,FVector(Scale));
    }
    if(!OnlyRoad && !WoodlandPools.IsEmpty())
    {
        if(Hills.Num()<16)Hills.SetNum(16);
        for(const auto& Pool:WoodlandPools)
            Hills[15].Add(FTransform(FVector(FVector2D(Pool.OriginM)*100.,0.)));
    }
    if(bReference && !ForestReferenceBoulders::Place(*this,Meshes,Hills,Road))return false;
    if (CliffLedgeMesh && bReference)
    {
        Meshes.Add(CliffLedgeMesh.Get());
        Hills.SetNum(Meshes.Num()); Road.SetNum(Meshes.Num());
        if (!OnlyRoad) Hills.Last()=CliffHillLedges;
        if (OnlyRoad || OnlyTheme.IsNone()) Road.Last()=CliffRoadLedges;
    }
    if (CliffShelfMesh && bReference)
    {
        Meshes.Add(CliffShelfMesh.Get());
        Hills.SetNum(Meshes.Num()); Road.SetNum(Meshes.Num());
        if (!OnlyRoad) Hills.Last()=CliffHillShelves;
        if (OnlyRoad || OnlyTheme.IsNone()) Road.Last()=CliffRoadShelves;
    }
    const int32 FirstTalus=Meshes.Num();
    if (bReference)
        for (const auto& Group:TalusVariants)
        {
            if (!Group.Mesh) return false;
            Meshes.Add(Group.Mesh.Get());
            Hills.AddDefaulted(); Road.AddDefaulted();
            if (!OnlyRoad) FitTalusSites(Group.Hills,Group.Mesh.Get(),Hills.Last());
            if (OnlyRoad || OnlyTheme.IsNone()) FitTalusSites(Group.Road,Group.Mesh.Get(),Road.Last());
        }
    if(bReference && !OnlyRoad && !ForestCourtyardShrubs::Place(*this,StudyMeshes,CliffExposureMask,HarvestTreeSites,Meshes,Hills,Road))return false;
    if(!BakeForestRegionPCG(*this,Hills,Road,OnlyTheme,Meshes.GetData(),Templates,FirstTalus))return false;
    MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
