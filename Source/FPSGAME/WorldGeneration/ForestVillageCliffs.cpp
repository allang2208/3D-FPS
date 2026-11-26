#include "ForestVillageRegion.h"
#include "ForestVillageMap.h"
#include "Engine/StaticMesh.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#if WITH_EDITOR
#include "Landscape.h"
#include "LandscapeDataAccess.h"
#include "LandscapeEdit.h"
#include "LandscapeEditLayer.h"
#include "LandscapeInfo.h"
#endif

bool AForestVillageRegion::InstallCliffExposure(const FString& Directory,UStaticMesh* Ledge,UStaticMesh* Shelf)
{
#if WITH_EDITOR
    constexpr int32 Side=ForestVillageMap::SideMeters+1;
    struct FSite {float X,Y,Heading,Scale;int32 Flags;};
    static_assert(sizeof(FSite)==20);
    TArray<uint8> Mask,Bytes;
    if (!Ledge || !Shelf || !FFileHelper::LoadFileToArray(Mask,*(Directory/TEXT("cliff-mask.u8"))) || Mask.Num()!=Side*Side ||
        !FFileHelper::LoadFileToArray(Bytes,*(Directory/TEXT("ledge-sites.bin"))) || Bytes.Num()%sizeof(FSite)) return false;
    TArray<FTransform> Hill,Road,HillShelves,RoadShelves;
    for (int32 I=0;I<Bytes.Num();I+=sizeof(FSite))
    {
        FSite P;FMemory::Memcpy(&P,Bytes.GetData()+I,sizeof(P));
        const double R=60.*P.Scale;
        const FVector N=FVector(GroundHeight(P.X-R,P.Y)-GroundHeight(P.X+R,P.Y),
            GroundHeight(P.X,P.Y-R)-GroundHeight(P.X,P.Y+R),2.*R).GetSafeNormal();
        const FVector Strike=FVector::CrossProduct(FVector::UpVector,N).GetSafeNormal();
        const FVector Heading=FQuat(N,FMath::DegreesToRadians(double(P.Heading))).RotateVector(Strike);
        const bool Bare=(P.Flags&2)!=0,IsRoad=(P.Flags&1)!=0;
        const FQuat Rotation=FRotationMatrix::MakeFromZX(N,Heading).ToQuat();
        const FVector Centre(P.X,P.Y,GroundHeight(P.X,P.Y));
        const FVector Half=(Bare?Shelf:Ledge)->GetBoundingBox().GetExtent()*P.Scale;
        double Sink=Bare?10.+6.*P.Scale:5.+5.*P.Scale;
        // The open rim must meet the rock even where the surface bends across the scan.
        for (int32 J=0;J<12;++J)
        {
            const double Angle=J*(2.*PI/12.);
            const FVector Edge=Centre+Rotation.RotateVector(FVector(.92*Half.X*FMath::Cos(Angle),.92*Half.Y*FMath::Sin(Angle),0.));
            Sink=FMath::Max(Sink,(Edge.Z-GroundHeight(Edge.X,Edge.Y))*N.Z+3.);
        }
        auto& Set=Bare?(IsRoad?RoadShelves:HillShelves):(IsRoad?Road:Hill);
        Set.Emplace(Rotation,Centre-N*Sink,FVector(P.Scale));
    }
    Modify();CliffExposureMask=MoveTemp(Mask);CliffLedgeMesh=Ledge;
    CliffHillLedges=MoveTemp(Hill);CliffRoadLedges=MoveTemp(Road);
    CliffShelfMesh=Shelf;CliffHillShelves=MoveTemp(HillShelves);CliffRoadShelves=MoveTemp(RoadShelves);MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

bool AForestVillageRegion::InstallCliffTalus(const FString& SitesFile,UStaticMesh* Fine,UStaticMesh* Fragment)
{
#if WITH_EDITOR
    // Disk records have no SIMD padding: four floats followed by one uint32.
    constexpr int32 Stride=20;
    TArray<uint8> Bytes;
    if (!Fine || !Fragment || !FFileHelper::LoadFileToArray(Bytes,*SitesFile) || Bytes.Num()%Stride!=0) return false;
    FString SelectedTheme;
    const FString Identity=FPaths::GetPath(SitesFile)/TEXT("theme.id");
    if (FPaths::FileExists(Identity))
    {
        if (!FFileHelper::LoadFileToString(SelectedTheme,*Identity)) return false;
        SelectedTheme.TrimStartAndEndInline();
        if (SelectedTheme!=TEXT("HillsLandscape") && SelectedTheme!=TEXT("RoadLandscape")) return false;
    }
    TArray<FForestTalusVariant> Groups;Groups.SetNum(2);
    Groups[0].Mesh=Fine;Groups[1].Mesh=Fragment;
    for (int32 Offset=0;Offset<Bytes.Num();Offset+=Stride)
    {
        FVector4f Site;
        uint32 Flags;
        FMemory::Memcpy(&Site,Bytes.GetData()+Offset,16);
        FMemory::Memcpy(&Flags,Bytes.GetData()+Offset+16,4);
        if (Flags>3 || Site.ContainsNaN() || Site.W<=0) return false;
        if (!SelectedTheme.IsEmpty() && bool(Flags&1)!=(SelectedTheme==TEXT("RoadLandscape"))) return false;
        auto& Group=Groups[Flags>>1];
        ((Flags&1)?Group.Road:Group.Hills).Add(Site);
    }
    if (!SelectedTheme.IsEmpty() && !TalusVariants.IsEmpty())
    {
        if (TalusVariants.Num()!=Groups.Num()) return false;
        for (int32 I=0;I<Groups.Num();++I)
        {
            if (Groups[I].Mesh!=TalusVariants[I].Mesh) return false;
            if (SelectedTheme==TEXT("RoadLandscape")) Groups[I].Hills=TalusVariants[I].Hills;
            else Groups[I].Road=TalusVariants[I].Road;
        }
    }
    Modify();TalusVariants=MoveTemp(Groups);MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

#if WITH_EDITOR
void AForestVillageRegion::FitTalusSites(const TArray<FVector4f>& Sites,UStaticMesh* Mesh,TArray<FTransform>& Out) const
{
    const FBox Box=Mesh->GetBoundingBox();
    const FVector Foot(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
    Out.Reserve(Sites.Num());
    for (const FVector4f& P:Sites)
    {
        const double R=FMath::Clamp(Box.GetExtent().GetMax()*P.W,5.,25.);
        const FVector N=FVector(GroundHeight(P.X-R,P.Y)-GroundHeight(P.X+R,P.Y),
            GroundHeight(P.X,P.Y-R)-GroundHeight(P.X,P.Y+R),2.*R).GetSafeNormal();
        const FQuat Rot=FQuat(N,FMath::DegreesToRadians(double(P.Z)))*FQuat::FindBetweenNormals(FVector::UpVector,N);
        const double Sink=FMath::Clamp(Box.GetSize().Z*P.W*.17,.5,3.5);
        const FVector Anchor=FVector(P.X,P.Y,GroundHeight(P.X,P.Y))-N*Sink;
        Out.Emplace(Rot,Anchor-Rot.RotateVector(Foot*P.W),FVector(P.W));
    }
}
#endif

bool AForestVillageRegion::WriteCliffLandscapeLayer(ALandscape* Landscape,const FString& DeltaFile)
{
#if WITH_EDITOR
    constexpr int32 Side=505;
    TArray<uint8> Raw;
    if (!Landscape || !FFileHelper::LoadFileToArray(Raw,*DeltaFile) || Raw.Num()!=Side*Side*int32(sizeof(int16))) return false;
    ULandscapeInfo* Info=Landscape->GetLandscapeInfo();
    int32 X0,Y0,X1,Y1;
    if (!Info || !Info->GetLandscapeExtent(X0,Y0,X1,Y1) || X1-X0+1!=Side || Y1-Y0+1!=Side) return false;
    const FName Name(TEXT("Forest cliff relief"));
    auto* Layer=Landscape->GetEditLayer(Name);
    if (!Layer) Layer=Landscape->GetEditLayer(Landscape->CreateLayer(Name,ULandscapeEditLayer::StaticClass()));
    if (!Layer) return false;
    const FTransform T=Landscape->LandscapeActorToWorld();
    TArray<uint16> Samples;Samples.SetNumUninitialized(Side*Side);
    for (int32 J=0;J<Side;++J)
        for (int32 I=0;I<Side;++I)
        {
            const FVector W=T.TransformPosition(FVector(X0+I,Y0+J,0.));
            const int32 X=FMath::RoundToInt(W.X*.01)+252,Y=FMath::RoundToInt(W.Y*.01)+252;
            if (X<0 || X>=Side || Y<0 || Y>=Side) return false;
            int16 Delta;FMemory::Memcpy(&Delta,Raw.GetData()+sizeof(int16)*(Y*Side+X),sizeof(int16));
            Samples[J*Side+I]=LandscapeDataAccess::GetTexHeight(Delta/T.GetScale3D().Z);
        }
    {
        FHeightmapAccessor<false> Writer(Info);
        Writer.SetEditLayer(Layer->GetGuid());
        Writer.SetData(X0,Y0,X1,Y1,Samples.GetData());
    }
    Landscape->ForceLayersFullUpdate();
    Landscape->MarkPackageDirty();
    if(Landscape->IsNaniteEnabled() && Landscape->GetOutermost()->GetName()==TEXT("/Game/ForestPathStudy/VillageRegion/Reference/TrailLandscape/L_ForestPathForest"))
        return BuildReferenceLandscapeNanite(Landscape);
    return true;
#else
    return false;
#endif
}
