#pragma once
#include "CoreMinimal.h"

class UDynamicMeshComponent;
class UPrimitiveComponent;
class UStaticMesh;
struct FHitResult;

// Local height samples, arrival times and wetting limits are shared by the visible mesh and authority.
struct FVillageOilSpread
{
    static constexpr int32 Half=12,Side=Half*2+1;
    static constexpr float Step=500.f/(Half-1);
    float Radius=500.f;
    int32 MaxExtent() const { return FMath::Clamp(FMath::CeilToInt((Radius+Step*1.6f)/Step),3,Half); }
    struct FCell
    {
        FVector P=FVector::ZeroVector,N=FVector::UpVector;
        FVector2D Flow=FVector2D::ZeroVector;
        float Arrival=1000.f,Edge=-100.f,FilmMM=0.f;
        bool bGround=false;
        uint8 Links=0;
        int32 Support=INDEX_NONE;
    };
    TArray<FCell> Cells;
    int32 Built=-1;
    FVector2D Incoming=FVector2D(1,0);
    float Seed=0.f;
    uint16 SupportRevision=0;
    FBox WetBounds=FBox(ForceInit);
    void Grow(AActor& Field,FVector PourFrom,float Age,UDynamicMeshComponent* Mesh);
    bool AdvanceSurvey(AActor& Field,float Age,int32& Budget);
    bool RemoveLostSupports(float Age);
    void WriteMesh(UDynamicMeshComponent& Mesh) const;
    void PackSurface(TArray<uint8>& Packet) const;
    bool UnpackSurface(const TArray<uint8>& Packet);
    bool WetAt(FVector LocalFeet,float Age) const;
    int32 UpstreamOnWetFace(int32 Index) const;
private:
    bool Triangle(int32 A,int32 B,int32 C) const;
    struct FShoreTri { FCell V[3]; };
    TMap<int32,TArray<FShoreTri>> Shores;
    TMap<int32,FVector> EdgeCuts;
    void BuildShores(int Extent,TSet<int32>* Missing=nullptr);
    void UpdateBounds();
    struct FSupport
    {
        TWeakObjectPtr<UPrimitiveComponent> Component;
        FTransform Frame;
        int32 Instance=INDEX_NONE;
        bool Retired=false;
        TWeakObjectPtr<UStaticMesh> Mesh;
    };
    TArray<FSupport> Supports;
    TMap<int32,int32> ExtraLinkSupports;
    TMap<int32,int32> CutSupports;
    int32 TrackSupport(const FHitResult& Hit);
    int32 Target=-1,ColumnCursor=0,LinkCursor=0,CutCursor=0;
    TArray<int32> NeededCuts;
    bool bCutsPlanned=false;
    float EdgeDistance(FVector P) const;
    void Solve(float KeepWetUntil=-1.f);
    void SettleFilm();
};
