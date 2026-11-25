#include "ForestVillageRelief.h"
#include "ForestVillageRegion.h"

#include "Components/DecalComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Actor.h"

namespace ForestVillageRelief
{
namespace
{
#include "ForestVillageReliefData.inl"
#include "ForestVillageStreetRelief.inl"

// Matches the A-D-B and A-C-D faces used for rendering and physics.
template<typename ReadVertex>
double SampleTriangles(double X, double Y, ReadVertex Read)
{
    const double GX = (X-MinX)/Step, GY = (Y-MinY)/Step;
    if (GX < 0. || GY < 0. || GX > Columns-1 || GY > Rows-1) return 0.;
    const int32 I = FMath::Min(int32(GX), Columns-2), J = FMath::Min(int32(GY), Rows-2);
    const double U = GX-I, V = GY-J;
    const double A = Read(I,J), D = Read(I+1,J+1);
    return U >= V ? (1.-U)*A + (U-V)*Read(I+1,J) + V*D :
                    (1.-V)*A + (V-U)*Read(I,J+1) + U*D;
}

bool FollowsGround(const UStaticMesh& Mesh)
{
    const FString Name = Mesh.GetName();
    for (const TCHAR* Prefix : GroundDressingPrefixes)
        if (Name.StartsWith(Prefix, ESearchCase::CaseSensitive)) return true;
    return false;
}
}

int32 VertexOffset(int32 Column, int32 Row)
{
    return ReliefCm[Row][Column];
}

double OffsetAt(double X, double Y)
{
    return SampleTriangles(X,Y,VertexOffset);
}

double SurfaceAt(TConstArrayView<float> Surface, double X, double Y)
{
    if (Surface.Num() != Columns*Rows) return 0.;
    return SampleTriangles(X,Y,[Surface](int32 I, int32 J) { return Surface[J*Columns+I]; });
}

int32 SitedVertexOffset(TConstArrayView<int16> Offsets,int32 I,int32 J)
{
    return Offsets[J*Columns+I] + StreetAndYardCm[J][I];
}

double SampleOffsets(TConstArrayView<int16> Offsets,double X,double Y)
{
    return SampleTriangles(X,Y,[Offsets](int32 I,int32 J) { return SitedVertexOffset(Offsets,I,J); });
}

void FitLevelDressing(ULevel& Level,const AForestVillageRegion& Region)
{
    // Only the streamed copy changes. OnLevelShown can fire twice for one level instance.
    static const FName Fitted(TEXT("ForestVillage.ReliefFitted"));
    for (AActor* Actor : Level.Actors)
    {
        if (!IsValid(Actor)) continue;
        if (Region.VillageStableEntryWear)
        {
            for (auto* Decal:TInlineComponentArray<UDecalComponent*>(Actor))
            {
                const auto* Material=Decal->GetDecalMaterial();
                if (Material && Material->GetPathName()==TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/GroundDetailR4/M_StableYardSoil.M_StableYardSoil"))
                    Decal->SetDecalMaterial(Region.VillageStableEntryWear);
            }
        }
        if(Region.VillageLoessDetail)
            for(auto* Part:TInlineComponentArray<UStaticMeshComponent*>(Actor))
            {
                const UStaticMesh* Mesh=Part->GetStaticMesh();
                if(!Mesh || Mesh->GetFName()!=TEXT("SM_MillEarthShoulder"))continue;
                for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
                {
                    auto* Existing=Part->GetMaterial(Slot);
                    if(Existing && Existing->GetFName()==TEXT("MI_MillEarth"))Part->SetMaterial(Slot,Region.VillageLoessDetail);
                }
            }
        TInlineComponentArray<UInstancedStaticMeshComponent*> Groups(Actor);
        for (auto* Group : Groups)
        {
            const UStaticMesh* Mesh = Group->GetStaticMesh();
            if (!Mesh || Group->ComponentHasTag(Fitted) || !FollowsGround(*Mesh)) continue;
            bool Changed = false;
            for (int32 I = 0; I < Group->GetInstanceCount(); ++I)
            {
                FTransform T;
                if (!Group->GetInstanceTransform(I,T,true)) continue;
                const FVector P = T.GetLocation();
                const double DZ = Region.DressingOffsetCm(P.X,P.Y);
                if (DZ != 0.)
                {
                    T.AddToTranslation(FVector(0.,0.,DZ));
                    Changed |= Group->UpdateInstanceTransform(I,T,true,false,true);
                }
            }
            if (Changed) Group->MarkRenderStateDirty();
            Group->ComponentTags.Add(Fitted);
        }
    }
}
}
