#include "TemperateHillsWorld.h"
#include "EastRiverRoad.h"
#include "TemperateIronOutcrops.h"
#include "TemperateQuarryYard.h"
#include "Algo/Compare.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Net/UnrealNetwork.h" // M4: DOREPLIFETIME
#include "TemperateHillsSurface.h"
#include "TemperateHillsVisibility.h"
#include "TemperateForestHabitat.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Engine/GameInstance.h"
#include "PCGComponent.h"
#include "PCGManagedResource.h"
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
#include "Misc/ConfigCacheIni.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateVegetationPlacement.h"
#include "../UI/ColdSteelStatusModel.h"

#include "TemperateHillsMathPrivate.h"
namespace TemperateHills
{
struct FLayerRadii : FPCGRuntimeGenerationRadii
{
    FLayerRadii(float Radius,float CleanupRadius)
    {
        RadiusUnbounded.Default=Radius;
        Radius12800.Default=Radius;
        Radius6400.Default=Radius;
        Radius3200.Default=Radius;
        Radius1600.Default=Radius;
        CleanupRadiusScalar.Default=CleanupRadius/Radius;
        ComputeHash();
    }
};
}
bool ATemperateHillsWorld::TreeCandidate(int32 GX,int32 GY,FTemperatePlacement& Out) const
{
    if(IsForestVillage())return ForestTreeCandidate(GX,GY,Out);
    if(!Assets)return false;
    const uint32 K=TemperateHills::Key(GX,GY,uint32(Seed),11);
    const double X=(GX+.5+(TemperateHills::Unit(K+1)-.5)*.56)*1200;
    const double Y=(GY+.5+(TemperateHills::Unit(K+2)-.5)*.56)*1200;
    if(EastRiverRoad::Enabled(Seed,GeneratorVersion,VillageSite) &&
       (EastRiverRoad::IsExtraTree(GX)||EastRiverRoad::Owns(X,Y)))
    {
        if(!EastRiverRoad::Tree(*this,GX,GY,{X,Y},Out))return false;
        const auto* Mesh=Cast<USkeletalMesh>(Out.Mesh.ResolveObject());
        return Mesh&&FitVegetationPlacement(Out,Mesh->GetImportedBounds().GetBox(),ETemperatePlantKind::Tree);
    }
    const auto& Ecology=EcologyProfile();
    if(Assets->Trees.IsEmpty()||Ecology.Trees.Density<=0)return false;
    if(ChapelSite.Clears(X,Y,520.)||VillageSite.Clears(X,Y,520.)||VillageSite.InLandmarkView(X,Y))return false;
    const double Half=SizeMeters*50-1000;
    const auto Shore=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample{};
    if(Shore.Bank>.02)return false;
    if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half||PathDistance(X,Y)<1150||
        FVector2D::Distance(FVector2D(X,Y),FVector2D(GetStartLocation()))<2200)return false;
    const double Up=SurfaceNormal(X,Y).Z;
    double RimStand=0.;
    if(RiverPlan && RiverPlan->WhiteCliffs.Weight(X,Y)>.25)
    {
        const auto P=RiverPlan->WhiteCliffs.Local(X,Y);
        const auto Q=TemperateQuarry::Finish(P,Up,.5);
        if(Q.Turf<.7)return false;
        const auto S=TemperateQuarry::Section(P.Y);
        const double Depth=FMath::Max(S.West-P.X,P.X-S.East);
        const double Belt=FMath::SmoothStep(870.,1390.,Depth)*(1.-FMath::SmoothStep(2300.,3650.,Depth));
        const double Patch=.5+.5*FMath::Sin(P.Y/1070.+.58*FMath::Sin(P.X/770.));
        RimStand=Belt*FMath::Lerp(.28,.89,Patch)*FMath::SmoothStep(-3300.,-1700.,P.Y)*(1.-FMath::SmoothStep(4300.,6100.,P.Y));

    }
    const double SlopeWeight=Ecology.Trees.SlopeWeight(Up);
    if(SlopeWeight<=0)return false;
    const double Region=RainforestWeight(X,Y);
    const double Opening=Region>0?TemperateForestHabitat::RainforestOpening(X,Y,Seed,Ecology):0.;
    const auto Grove=TemperateForestGroves::Sample(X,Y,Seed);
    const double Forest=TemperateForestHabitat::CanopyFromGrove(X,Y,Seed,Region,Opening,Ecology,Grove.Cover);
    // Keep candidate positions and harvest IDs. Regional canopy scale stays
    // on the same standing-tree / stump / regrowth transform path. Species selection
    // now applies to both established points and the newer canopy infill.
    const double PreviousChance=.045+TemperateForestHabitat::LegacyCanopy(X,Y,Seed,Grove.Cover)*.48;
    const double Roll=TemperateHills::Unit(K+3);
    const double Stand=Roll>PreviousChance?
        TemperateHillsSurface::Noise5(X/3000.0,Y/3000.0,Seed,3143)*.5+.5:.5;
    const double LocalDensity=FMath::Lerp(1.0,Ecology.Rainforest.TreeDensityMultiplier*(1.0-.55*Opening),Region);
    const double Chance=Ecology.Trees.Density*LocalDensity*SlopeWeight*FMath::Max3(PreviousChance,.02+Forest*(.56+.22*Stand),RimStand);
    if(Roll>FMath::Min(1.0,Chance))return false;
    const double BaseScale=Roll<=PreviousChance?.68+TemperateHills::Unit(K+5)*.4:
        (.58+TemperateHills::Unit(K+5)*.28)*(.92+.16*Stand);
    const double Scale=BaseScale*FMath::Lerp(1.0,Ecology.Rainforest.TreeScaleMultiplier,Region);
    Out.Transform=FTransform(FRotator(0,TemperateHills::Unit(K+4)*360,0),FVector(X,Y,Height(X,Y)-10),FVector(Scale));
    // Palette slots stay stable: black poplar 0..3, beech A/B then C/D.
    // Beech is the primary species across ALL surviving tree points, not only
    // infill. The shared ecology profile controls the stand-level mixture.
    const int32 PoplarCount=FMath::Min(4,Assets->Trees.Num());
    int32 MeshIndex=int32(K%PoplarCount);
    const int32 BeechCount=Assets->Trees.Num()-PoplarCount;
    if(BeechCount>0)
    {
        const uint32 Cohort=TemperateForestHabitat::Cohort(X,Y,Seed,K,3149,Ecology);
        // Poplar favours the open, level shoulder behind wet banks. Closed stands
        // retain their broad beech crowns. Only the species changes at a given cell.
        const double BankShoulder=1.-FMath::SmoothStep(2200.,6800.,Shore.Distance-Shore.HalfWidth);
        const double Light=1.-FMath::SmoothStep(.22,.80,Forest);
        const double DampShoulder=FMath::Max(BankShoulder,Region*.7)*FMath::SmoothStep(.88,.99,Up);
        const double Habitat=.25*TemperateHills::Unit(Cohort+47)+Light*.23+DampShoulder*.52;
        const double PoplarShare=FMath::Lerp(Ecology.PoplarShareMin,Ecology.PoplarShareMax,Habitat);
        if(TemperateHills::Unit(K+23)>=PoplarShare)
        {
            // 70% mature forms in open stands, rising to 95% under a closed
            // canopy. Neighbours share a dominant form with occasional variation.
            const uint32 Form=TemperateHills::Unit(K+19)<.78?Cohort:TemperateHills::Mix(K+83);
            const bool Mature=TemperateHills::Unit(K+17)<.70+.25*FMath::SmoothStep(.18,.80,Forest);
            MeshIndex=PoplarCount+(BeechCount>=4?
                (Mature?int32(Form%2):2+int32(Form%(BeechCount-2))):int32(Form%BeechCount));
        }
    }
    Out.Mesh=Assets->Trees[MeshIndex].ToSoftObjectPath();Out.Key=K;Out.CandidateId=TemperateHills::CellId(GX,GY);
    const USkeletalMesh* Mesh=Assets->Trees[MeshIndex].Get();
    return Mesh&&FitVegetationPlacement(Out,Mesh->GetImportedBounds().GetBox(),ETemperatePlantKind::Tree);
}

FString ATemperateHillsWorld::RockOreDefinition(uint32 Key, const FVector2D& At) const
{
    // Single source of truth for a rock candidate's mineral; the resolve side
    // (rewards) and the render side (vein variant mesh) must call it with the
    // same candidate position or what the player sees and digs would drift.
    //
    // Ore follows exposed gravel and seeded mineral pockets, with a bonus only
    // inside the actual river corridor. Candidate coordinates and IDs stay fixed.
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};
    const FVector N=SurfaceNormal(At.X,At.Y);
    const double Slope=Smooth((1.0-N.Z)*3.2);
    const double WX=At.X+Noise(At.X*.0004,At.Y*.0004,1411)*650;   // ground material's
    const double WY=At.Y+Noise(At.X*.0004,At.Y*.0004,1417)*650;   // dry-gravel patch field
    const double Patch=Noise(WX*.0000405,WY*.0000405,1459)*.5+.5;
    const double Gravel=Smooth((.58-Patch)/.40);
    const double PocketField=.65*(Noise(At.X/14000.0,At.Y/14000.0,3311)*.5+.5)
        +.35*(Noise(At.X/4200.0,At.Y/4200.0,3319)*.5+.5);
    const double Pocket=FMath::SmoothStep(.30,.72,PocketField);
    double Weight=(.025+.35*Slope+.50*Gravel)*(.30+.95*Pocket);
    // Deep, level woodland is litter-covered; exposed stony ground can still
    // host mineral outcrops under the canopy.
    Weight*=1.0-.55*ForestWeight(At.X,At.Y)*(1.0-Slope)*(1.0-.85*Gravel);
    if(RiverPlan)
    {
        const auto R=RiverPlan->Sample(At.X,At.Y);
        // Bank is ZERO outside the corridor. The old Bank<.5 condition added a
        // river bonus across dry land, producing unrelated isolated ore blocks.
        if(R.Bank>.02&&R.Distance<R.HalfWidth+750)
        {
            const double Exposure=(R.Wet>.3||R.Distance<R.HalfWidth)?1.0:
                1.0-FMath::SmoothStep(R.HalfWidth,R.HalfWidth+750.0,R.Distance);
            Weight+=.40*Exposure*(.45+.55*Pocket);
        }
    }
    const uint32 Roll=Key%1000;
    if(Roll>=uint32(FMath::Clamp(Weight,0.0,1.0)*1000))return FString();
    const uint32 Pick=(Key/1000)%100;
    return Pick<25?TEXT("iron_ore"):Pick<37?TEXT("copper_ore"):Pick<41?TEXT("silver_ore"):Pick<43?TEXT("gold_ore"):TEXT("");
}

FSoftObjectPath ATemperateHillsWorld::OreRockVariantMesh(uint32 Key, const FVector2D& At) const
{
    const FString Ore=RockOreDefinition(Key,At);
    return ProductionOreRocks::Mesh(Ore,ProductionOreRocks::Shape(Key));
}

void ATemperateHillsWorld::GetBasePlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeRegrowth) const
{
    const int32 First=Out.Num();
    if(Layer==0)
    {
        GatherBasePlacements(Layer,Bounds,Out,IncludeRegrowth);
    }
    else EastRiverRoad::ForLegacyBounds(*this,Bounds,[&](const FBox& Outside)
    {
        GatherBasePlacements(Layer,Outside,Out,IncludeRegrowth);
        if(Layer==1)TemperateIronOutcrops::Gather(*this,Outside,Out);
    });
    const double Margin=Layer==1?600.:(Layer==2||Layer==4?115.:25.);
    const FVector Extent=Bounds.GetExtent();
    const double Reach=FMath::Max(Extent.X,Extent.Y)+Margin;
    if(!ChapelSite.Near(Bounds.GetCenter().X,Bounds.GetCenter().Y,Reach) &&
       !VillageSite.Near(Bounds.GetCenter().X,Bounds.GetCenter().Y,Reach))return;
    for(int32 I=Out.Num()-1;I>=First;--I)
    {
        const FVector P=Out[I].Transform.GetLocation();
        if(Layer==0&&EastRiverRoad::Enabled(Seed,GeneratorVersion,VillageSite)&&EastRiverRoad::Owns(P.X,P.Y))continue;
        if(ChapelSite.Clears(P.X,P.Y,Margin)||VillageSite.Clears(P.X,P.Y,Margin))Out.RemoveAtSwap(I,1,EAllowShrinking::No);
    }
}

void ATemperateHillsWorld::GatherBasePlacements(int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool IncludeRegrowth) const
{
    if(!Assets||Layer<0||Layer>4)return;
    if(Layer==4){GetForestUnderstoryPlacements(Bounds,Out);return;}
    if(Layer==3){GetGrassPlacements(Bounds,Out);GetGroundDebrisPlacements(Bounds,Out);GetRiverPlantPlacements(Bounds,Out);GetRiverPebblePlacements(Bounds,Out);return;}
    if(Layer==2)GetRiverShrubPlacements(Bounds,Out);
    const auto& Ecology=EcologyProfile();
    if(Layer==2&&Ecology.Shrubs.Density<=0)return;
    if(Layer==0 && IncludeRegrowth)GetRegrowingTrees(Bounds,Out);
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
        if(Layer==0)
        {
            for(const auto Address:EastRiverRoad::TreeKeys(*this,GX,GY))
            {
                if(!TreeCandidate(Address.X,Address.Y,P)||IsProductionDepleted(0,P.CandidateId))continue;
                const FVector At=P.Transform.GetLocation();
                if(At.X>=MinX&&At.X<MaxX&&At.Y>=MinY&&At.Y<MaxY)Out.Add(P);
            }
            continue;
        }
        else
        {
            const uint32 K=TemperateHills::Key(GX,GY,uint32(Seed),101+Layer);
            const double X=(GX+.5+(TemperateHills::Unit(K+1)-.5)*.8)*Spacing;
            const double Y=(GY+.5+(TemperateHills::Unit(K+2)-.5)*.8)*Spacing;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY||FMath::Abs(X)>Half-500||FMath::Abs(Y)>Half-500)continue;
            // Keep ordinary slope stones and vegetation out of the carved river corridor.
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>(Layer==3?.08:.02))continue;
            const FVector N=SurfaceNormal(X,Y);
            if(N.Z<(Layer==1?.72:Ecology.Shrubs.MinNormalZ)||PathDistance(X,Y)<(Layer==3?240:700))continue;
            if(Layer<3&&FVector2D::Distance(FVector2D(X,Y),FVector2D(GetStartLocation()))<1600)continue;
            const double Forest=ForestWeight(X,Y);
            const double LegacyShrubWeight=Assets->ForestShrubs.IsEmpty()?1.0:(1.0-.85*Forest);
            TemperateForestHabitat::FUnderstory Site;
            double Probability=.12+(1-N.Z)*1.6;
            if(Layer==2)
            {
                const double Region=RainforestWeight(X,Y);
                Site=TemperateForestHabitat::Understory(X,Y,Seed,Forest,Region,N, EcologyProfile());
                const double Fringe=FMath::SmoothStep(700.0,1650.0,PathDistance(X,Y))
                    *Ecology.Shrubs.SlopeWeight(N.Z)
                    *(1.0-FMath::SmoothStep(.001,.02,Bank.Bank))
                    *FMath::SmoothStep(1600.0,2500.0,FVector2D::Distance(FVector2D(X,Y),FVector2D(GetStartLocation())));
                const double LocalDensity=FMath::Lerp(1.0,Ecology.Rainforest.ShrubDensityMultiplier,Region);
                Probability=Ecology.Shrubs.Density*LocalDensity*LegacyShrubWeight*(.015*Forest+.48*Site.Shrub)*Fringe;
            }
            if(TemperateHills::Unit(K+3)>Probability)continue;
            bool TrunkOverlap=false;
            // Plant layers apply their model-sized trunk/core rules together.
            // Retain the old early trunk gate only for rock candidates.
            if(Layer==1)
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
            // Slope stones span small collectible boulders up to unmineable cliff
            // masses: the pickaxe gate rejects instance radius > 500 cm, and the
            // old 0.7 floor kept every slope stone above it (nothing was minable).
            const uint32 Form=Layer==2?TemperateForestHabitat::Cohort(X,Y,Seed,K,3259, EcologyProfile()):K;
            const auto& ChosenMesh=List[(Layer==2&&TemperateHills::Unit(K+19)>.72?K:Form)%List.Num()];
            double Scale=Layer==1?.30+TemperateHills::Unit(K+5)*1.70:.65+TemperateHills::Unit(K+5)*.5;
            double Sink=Layer==1?35:3;
            // Taller hazel cores soften down to lower shrubs at their margins.
            // A cohort links nearby forms while keeping individual variation.
            if(Layer==2)
            {
                const UStaticMesh* Mesh=ChosenMesh.Get();if(!Mesh)continue;
                const FBox Box=Mesh->GetBoundingBox();
                const double Vigor=.55*TemperateHills::Unit(Form+7)+.45*TemperateHills::Unit(K+5);
                Scale=(70+80*Vigor+90*Site.Shrub)/FMath::Max(1.0,Box.GetSize().Z);
                Sink=Box.Min.Z*Scale+3;
            }
            const FVector Up=Layer==1?N:FMath::Lerp(FVector::UpVector,N,.22).GetSafeNormal();
            const FQuat Rotation=FQuat(Up,TemperateHills::Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-Sink),FVector(Scale));
            P.Mesh=ChosenMesh.ToSoftObjectPath();P.Key=K;P.CandidateId=TemperateHills::CellId(GX,GY);
            // Ore has its own physical size range and four seeded source shapes.
            if(Layer==1)
                if(const FSoftObjectPath Vein=OreRockVariantMesh(K,FVector2D(X,Y));Vein.IsValid())
                {
                    const auto* Mesh=Cast<UStaticMesh>(Vein.ResolveObject());if(!Mesh)continue;
                    P.Mesh=Vein;
                    P.Transform=ProductionOreRocks::Placement(*Mesh,K,FVector(X,Y,Height(X,Y)),N);
                }
        }
        const FVector Pos=P.Transform.GetLocation();
        // Rock depletion is applied AFTER deterministic occupancy selection.
        // A depleted winner must not expose a previously rejected neighbour.
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
            // Bed stones stay mostly under the 500 cm mineable-radius gate so the
            // corridor is where collectible river ore actually comes from.
            const double Scale=.30+TemperateHills::Unit(K+5)*.45;
            const FQuat Rotation=FQuat(N,TemperateHills::Unit(K+4)*2*PI)*FQuat(FQuat::FindBetweenNormals(FVector::UpVector,N));
            FTemperatePlacement P;
            const auto& Rock=Assets->RiverRocks[K%Assets->RiverRocks.Num()];
            const double Base=Rock.IsValid()?Rock.Get()->GetBoundingBox().Min.Z:0;
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-(Base+18)*Scale),FVector(Scale));
            P.Mesh=Rock.ToSoftObjectPath();P.Key=K;
            if(const FSoftObjectPath Vein=OreRockVariantMesh(K,FVector2D(X,Y));Vein.IsValid())
            {
                const auto* Mesh=Cast<UStaticMesh>(Vein.ResolveObject());if(!Mesh)continue;
                P.Mesh=Vein;
                P.Transform=ProductionOreRocks::Placement(*Mesh,K,FVector(X,Y,Height(X,Y)),N,true);
            }
            P.CandidateId=TemperateHills::CellId(GX,GY)^0x4000000000000000ULL;
            Out.Add(P);
        }
    }
    // Forest-floor deadwood and hillside cliffs reuse the same rock layer and
    // bounds contract; each keeps its own candidate namespace (TemperateHillsDressing.cpp).
    if(Layer==1)
    {
        GetForestFloorPlacements(Bounds,Out);
        GetCliffPlacements(Bounds,Out);
        GetVisualAnchorPlacements(Bounds,Out);
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
    auto* C=PCGLayers[Layer].Get();C->Seed=Seed;
    SetVegetationGenerationRadius(Layer,1600.f);
    C->SetGraph(Assets->Graphs[Layer].Get());
    if(auto* Policy=Cast<UPCGSchedulingPolicyDistanceAndDirection>(C->GetRuntimeGenSchedulingPolicy()))
    {
        // Direction is a tie-breaker, not a reason for distant cells in front
        // to outrank missing nearby cells behind a moving/turning player.
        Policy->bUseDistance=true;Policy->bUseDirection=true;
        Policy->DirectionWeight=TemperateHillsVisibility::DirectionWeight;
        Policy->bUseFrustumCulling=false;
        Policy->NetworkMode=Layer==1?EPCGSchedulingPolicyNetworkMode::All:EPCGSchedulingPolicyNetworkMode::Client;
    }
    if(auto* Sub=GetWorld()->GetSubsystem<UPCGSubsystem>())
    {
        Sub->RegisterOrUpdateExecutionSource(C);
        Sub->RefreshRuntimeGenExecutionSource(C,EPCGChangeType::GenerationGrid);
    }
}

void ATemperateHillsWorld::SetVegetationGenerationRadius(int32 Layer,float Radius)
{
    auto* C=PCGLayers[Layer].Get();
    const float Maximum=TemperateHillsVisibility::Layers[Layer].GenerateRadius;
    Radius=FMath::Min(Radius,Maximum);
    if(C->GenerationRadii.GetGenerationRadiusFromGrid(EPCGHiGenGrid::Grid16)==Radius)return;
    // Generation advances from near to far. Cleanup always keeps the original
    // outer radius, so reprioritizing cannot remove an already visible tree.
    // The radii hash triggers the native scheduler's cell rescan; refreshing the
    // graph here would destroy/rebuild existing cells and cause visible flashing.
    C->GenerationRadii=TemperateHills::FLayerRadii(Radius,Maximum*TemperateHillsVisibility::CleanupScale);
}

