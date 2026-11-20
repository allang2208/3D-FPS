bool ATemperateHillsWorld::TreeCandidate(int32 GX,int32 GY,FTemperatePlacement& Out) const
{
    if(!Assets||Assets->Trees.IsEmpty())return false;
    const auto& Ecology=EcologyProfile();
    if(Ecology.Trees.Density<=0)return false;
    const uint32 K=TemperateHills::Key(GX,GY,uint32(Seed),11);
    const double X=(GX+.5+(TemperateHills::Unit(K+1)-.5)*.56)*1200;
    const double Y=(GY+.5+(TemperateHills::Unit(K+2)-.5)*.56)*1200;
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
