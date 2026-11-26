#include "ForestNaniteAuthoring.h"
#include "ForestVillageRegion.h"
#if WITH_EDITOR
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "Materials/MaterialInterface.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshCompiler.h"
#include "LandscapeProxy.h"
#include "LandscapeSubsystem.h"
#include "LandscapeEditTypes.h"
#include "LandscapeNaniteComponent.h"
#include "Engine/World.h"

void ForestNaniteAuthoring::Configure(UStaticMesh& Mesh,bool bTerrain)
{
    auto Settings=Mesh.GetNaniteSettings();
    Settings.bEnabled=true;
    // Simple-only props use the windmill's decorative fallback. Walkable triangle meshes
    // also supply collision, so their fallback must preserve the authored surface.
    const UBodySetup* Body=Mesh.GetBodySetup();
    const bool SimpleProp=!bTerrain && Body && Body->CollisionTraceFlag==CTF_UseSimpleAsComplex;
    const FMeshDescription* Source=SimpleProp?Mesh.GetMeshDescription(0):nullptr;
    const bool Reduce=Source && Source->Triangles().Num()>=8000;
    Settings.FallbackTarget=ENaniteFallbackTarget::PercentTriangles;
    Settings.FallbackPercentTriangles=Reduce?FMath::Min(.35f,Settings.FallbackPercentTriangles):1.f;
    Settings.FallbackRelativeError=Reduce?1.f:0.f;
    if(bTerrain)Settings.PositionPrecision=2; // All neighbouring tiles share a 0.25 cm quantization grid.
    Mesh.SetNaniteSettings(Settings);
}
#endif

bool AForestVillageRegion::BuildSceneryNaniteMesh(UStaticMesh* Mesh,UMaterialInterface* PackedTerrainMaterial)
{
#if WITH_EDITOR
    if(!Mesh || !Mesh->GetNumSourceModels() || !Mesh->GetMeshDescription(0))return false;
    for(const FStaticMaterial& Slot:Mesh->GetStaticMaterials())
    {
        const UMaterialInterface* Mat=Slot.MaterialInterface.Get();
        if(!Mat || Mat->GetBlendMode()!=BLEND_Opaque || Mat->GetShadingModels().HasShadingModel(MSM_SingleLayerWater))
            return false;
    }
    if(!PackedTerrainMaterial && FStaticMeshConstAttributes(*Mesh->GetMeshDescription(0)).GetVertexInstanceUVs().GetNumChannels()>4)
        return false;
    Mesh->Modify();
    if(PackedTerrainMaterial)
    {
        if(!Mesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/ForestPathStudy/VillageRegion/Reference/Terrain/SM_ForestGround_")) ||
           Mesh->GetStaticMaterials().Num()!=1 || PackedTerrainMaterial->GetPathName()!=ForestNaniteAuthoring::PackedMaterial)return false;
        const auto* Original=Mesh->GetMaterial(0);
        if(!Original || (Original!=PackedTerrainMaterial && Original->GetPathName()!=TEXT("/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference.MI_ForestReference")))return false;
        Mesh->ModifyMeshDescription(0);
        FMeshDescription* Source=Mesh->GetMeshDescription(0);
        auto UV=FStaticMeshAttributes(*Source).GetVertexInstanceUVs();
        if(UV.GetNumChannels()!=5)return false;
        for(FVertexInstanceID V:Source->VertexInstances().GetElementIDs())
            if(!UV.Get(V,3).IsNearlyZero() && !UV.Get(V,3).Equals(UV.Get(V,4)))return false;
        for(FVertexInstanceID V:Source->VertexInstances().GetElementIDs())UV.Set(V,3,UV.Get(V,4));
        Mesh->CommitMeshDescription(0);
        Mesh->GetStaticMaterials()[0].MaterialInterface=PackedTerrainMaterial;
    }
    ForestNaniteAuthoring::Configure(*Mesh,PackedTerrainMaterial!=nullptr);
    Mesh->Build(false);
    FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});
    Mesh->MarkPackageDirty();
    return Mesh->HasValidNaniteData();
#else
    return false;
#endif
}

bool AForestVillageRegion::BuildReferenceLandscapeNanite(ALandscapeProxy* Landscape)
{
#if WITH_EDITOR
    if(!Landscape || Landscape->GetOutermost()->GetName()!=TEXT("/Game/ForestPathStudy/VillageRegion/Reference/TrailLandscape/L_ForestPathForest"))return false;
    auto* Subsystem=Landscape->GetWorld()->GetSubsystem<ULandscapeSubsystem>();
    if(!Subsystem || !Landscape->IsNaniteEnabled())return false;
    Landscape->Modify();
    Subsystem->BuildNanite(UE::Landscape::EBuildFlags::None,MakeArrayView(&Landscape,1));
    TInlineComponentArray<ULandscapeNaniteComponent*> Components(Landscape);
    if(Components.IsEmpty() || !Landscape->IsNaniteMeshUpToDate())return false;
    for(const auto* Component:Components)
    {
        const UStaticMesh* Mesh=Component->GetStaticMesh();
        if(!Mesh || !Mesh->HasValidNaniteData())return false;
    }
    Landscape->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
