// Companion water impact shapes for bodies authored outside the footprint generator.
//
// The Clearwater water plane (Tools/Fluids/author_clearwater_water.py) is a flat square,
// so its outline does not need the saved-mesh readback that the generated table uses.
// It is derived from the mesh bounds instead, which keeps it correct if the plane is ever
// re-authored at a different size and avoids a third hardcoded copy of the extent.
#include "WaterImpactFootprints.h"
#include "Engine/StaticMesh.h"

namespace
{
    // One patch cached per mesh, because the subsystem holds the returned pointer for the
    // lifetime of the surface.
    const FWaterImpactFootprint* BuildPlanarFootprint(const UStaticMesh* Mesh)
    {
        static TMap<FString, FWaterImpactFootprint> Cache;
        const FString Path = Mesh->GetPathName();
        if (const FWaterImpactFootprint* Found = Cache.Find(Path)) return Found;

        // GetBounds() returns FBoxSphereBounds; the axis-aligned FBox is what carries the
        // extent and origin used here.
        const FBox Box = Mesh->GetBoundingBox();
        const FVector Extent = Box.GetExtent();
        const double HalfX = Extent.X;
        const double HalfY = Extent.Y;

        FWaterImpactFootprint Shape;
        Shape.MeshPath = Path;
        Shape.StrengthScale = 1.f;

        FWaterImpactPatch Patch;
        // The rest height in component space. The plane is authored at local Z = 0.
        Patch.Z = Box.GetCenter().Z;

        constexpr int32 Segments = 64;      // 16 per side: ~11 m spacing on a 180 m plane
        constexpr int32 PerSide = Segments / 4;
        Patch.Polygon.Reserve(Segments);
        for (int32 Side = 0; Side < 4; ++Side)
        {
            for (int32 Step = 0; Step < PerSide; ++Step)
            {
                const double T = double(Step) / double(PerSide);
                const double A = -1.0 + T * 2.0;
                switch (Side)
                {
                // Counter-clockwise from (-X,-Y), matching the generator's winding.
                case 0: Patch.Polygon.Add(FVector2D(A * HalfX, -HalfY)); break;
                case 1: Patch.Polygon.Add(FVector2D(HalfX, A * HalfY)); break;
                case 2: Patch.Polygon.Add(FVector2D(-A * HalfX, HalfY)); break;
                default: Patch.Polygon.Add(FVector2D(-HalfX, -A * HalfY)); break;
                }
            }
        }
        for (const FVector2D& P : Patch.Polygon) Patch.Bounds += P;
        Shape.Patches.Add(MoveTemp(Patch));

        return &Cache.Add(Path, MoveTemp(Shape));
    }
}

const FWaterImpactFootprint* FindComplementaryWaterFootprint(const UStaticMesh* Mesh)
{
    if (!Mesh) return nullptr;
    const FString Path = Mesh->GetPathName();
    // Authored by Tools/Fluids/author_clearwater_water.py.
    if (Path == TEXT("/Game/Clearwater/SM_ClearwaterPlane.SM_ClearwaterPlane"))
    {
        return BuildPlanarFootprint(Mesh);
    }
    return nullptr;
}
