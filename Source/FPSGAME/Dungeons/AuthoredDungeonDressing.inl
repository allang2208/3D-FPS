// Cosmetic dressing for the authored room coordinates (UE centimetres, reflected Y).
// Included by the generator; no UObject access, world queries or route RNG consumption.
namespace DungeonDressing
{
using FObject = TSharedPtr<FJsonObject>;
enum class EUse : uint8 { Service, Wet, Freight, Ruins, Quiet };
enum class EProp : uint8 { Barrel, Ladder, Rope, Bucket, Extinguisher, Lantern, Web1, Web2, Web3 };
struct FAsset { const TCHAR* Name; FVector Size; };
static const FAsset Assets[] = {
    {TEXT("OilBarrel"), {62.9,56.5,88}}, {TEXT("StepLadder"), {83.7,88,110}},
    {TEXT("Rope"), {45,42.8,12.9}}, {TEXT("Bucket"), {30.3,30.1,30}},
    {TEXT("Extinguisher"), {22.9,16.3,55}}, {TEXT("Lantern"), {22,28.6,32}},
    {TEXT("Cobweb_1"), {58.6,58.2,22}}, {TEXT("Cobweb_2"), {65.7,54.6,25.4}},
    {TEXT("Cobweb_3"), {64,57,18.3}}
};
struct FSocket { FVector Position; double Yaw; EUse Use = EUse::Service; };
struct FProfile
{
    TArray<FSocket> Floor, Web;
    TArray<FBox> KeepClear;
    int32 MinClusters = 1, MaxClusters = 4, MaxFloorProps = 16, MaxWebs = 2;
};

static FProfile Profile(const FString& Id)
{
    FProfile P;
    using enum EUse;
    if (Id == TEXT("Distribution"))
    {
        P.Floor = {{{-495,-160,0},0,Service},{{-490,-1020,0},0,Service},
            {{965,-590,0},180,Service},{{350,-1095,0},90,Service}};
        P.Web = {{{-580,-90,357},0},{{1015,-510,275},180},{{-580,-1110,357},0}};
        P.KeepClear = {FBox(FVector(-180,-1060,-5),FVector(180,-120,240)), FBox(FVector(-430,-1190,-5),FVector(-180,-780,240)),
            FBox(FVector(660,-990,-5),FVector(1020,-735,240))};
    }
    else if (Id == TEXT("Drainage"))
    {
        P.Floor = {{{-485,-240,0},0,Wet},{{-485,-1760,0},0,Wet},
            {{895,-1510,0},180,Wet},{{890,-150,0},180,Service},{{180,-1940,0},90,Wet}};
        P.Web = {{{-570,-110,422},0},{{1008,-1520,422},180},{{-570,-1950,312},0}};
        P.KeepClear = {FBox(FVector(40,-1450,-100),FVector(400,-590,240)), FBox(FVector(-20,-1190,-5),FVector(1025,-955,240)),
            FBox(FVector(-200,-1480,-5),FVector(30,-1300,180))};
    }
    else if (Id == TEXT("ShoredBreach"))
    {
        P.Floor = {{{100,570,0},0,Ruins},{{930,570,0},180,Ruins},
            {{1710,-1000,0},180,Ruins},{{120,-1125,0},90,Ruins}};
        P.Web = {{{16,675,377},0},{{1068,675,377},180},{{1810,-1200,377},90}};
        P.KeepClear = {FBox(FVector(0,-170,-5),FVector(1090,325,240)), FBox(FVector(1780,-910,-5),FVector(2270,-330,260))};
    }
    else if (Id == TEXT("VentilationLoop"))
    {
        P.Floor = {{{260,-105,0},-90,Service},{{1460,-105,0},-90,Service},
            {{1560,-1500,0},90,Service},{{140,-1370,0},0,Service},{{1660,-530,0},180,Service}};
        P.Web = {{{28,-250,312},0},{{1730,-240,402},180},{{240,-1572,402},90}};
        P.KeepClear = {FBox(FVector(520,-1270,-5),FVector(1270,-330,440)), FBox(FVector(20,-1120,-5),FVector(225,-900,180)),
            FBox(FVector(1320,-1330,-5),FVector(1800,-1070,230))};
    }
    else if (Id == TEXT("FreightTransfer"))
    {
        P.Floor = {{{500,-135,0},-90,Service},{{1300,-565,0},180,Freight},
            {{1670,-905,0},180,Freight},{{250,-1685,60},90,Freight},{{1440,-1700,60},90,Freight}};
        P.Web = {{{422,-100,422},0},{{1378,-670,422},180},{{85,-1770,422},90}};
        P.KeepClear = {FBox(FVector(690,-1410,-5),FVector(1100,0,260)), FBox(FVector(170,-1460,-5),FVector(530,-1200,290)),
            FBox(FVector(1270,-1460,-5),FVector(1630,-1200,290)), FBox(FVector(660,-1810,50),FVector(1270,-1480,320)),
            FBox(FVector(25,-1260,-5),FVector(230,-880,180)), FBox(FVector(1560,-1700,50),FVector(1780,-1520,240))};
    }
    else if (Id == TEXT("Treasure"))
    {
        P.MinClusters=1; P.MaxClusters=2; P.MaxFloorProps=7;
        P.Floor = {{{-430,-275,0},0,Quiet},{{430,-765,0},180,Quiet},{{-420,-870,0},90,Quiet}};
        P.Web = {{{-505,-110,337},0},{{505,-920,337},180},{{-440,-995,337},90}};
        P.KeepClear = {FBox(FVector(-240,-780,-5),FVector(240,0,240))};
    }
    else if (Id == TEXT("BossPumpHall"))
    {
        P.MinClusters=3; P.MaxClusters=5; P.MaxFloorProps=26; P.MaxWebs=3;
        P.Floor = {{{-1380,-250,0},0,Service},{{1380,-260,0},180,Service},
            {{-1380,-1180,0},0,Wet},{{1380,-1840,0},180,Wet},
            {{-1385,-915,360},0,Service},{{1385,-1080,360},180,Service},
            {{-1370,-2080,360},0,Service},{{1385,-2410,360},180,Service}};
        P.Web = {{{-1470,-100,827},0},{{1470,-2500,827},180},
            {{-1470,-2460,827},0},{{1470,-950,827},180}};
        P.KeepClear = {FBox(FVector(-735,-2260,-5),FVector(735,0,300)),
            FBox(FVector(-1150,-1390,-5),FVector(-700,-120,570)), FBox(FVector(700,-1560,-5),FVector(1150,-300,570)),
            FBox(FVector(-340,-2600,-5),FVector(340,-2260,560))};
    }
    // Connectors, route junctions and unknown future room types have no floor sockets.
    return P;
}

static FVector Vector(const FObject& O, const TCHAR* Key)
{
    const auto& A=O->GetArrayField(Key); return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());
}
static TArray<TSharedPtr<FJsonValue>> Array(const FVector& V)
{
    return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};
}
static FBox AssetBox(EProp Type, const FRotator& Rotation, double Scale)
{
    const FVector S=Assets[uint8(Type)].Size;
    return FBox(FVector(-S.X/2,-S.Y/2,0),FVector(S.X/2,S.Y/2,S.Z))
        .TransformBy(FTransform(Rotation,FVector::ZeroVector,FVector(Scale)));
}
static bool NearDoor(const FBox& B, const FObject& Door)
{
    const FVector D=Vector(Door,TEXT("position")), N=Vector(Door,TEXT("normal"));
    double Width=300,Height=280;
    Door->TryGetNumberField(TEXT("width"),Width); Door->TryGetNumberField(TEXT("height"),Height);
    if(B.Min.Z>D.Z+Height+40 || B.Max.Z<D.Z-20) return false;
    const FVector Tangent(-N.Y,N.X,0), C=B.GetCenter()-D,E=B.GetExtent();
    const double DepthExtent=FMath::Abs(N.X)*E.X+FMath::Abs(N.Y)*E.Y;
    const double SideExtent=FMath::Abs(Tangent.X)*E.X+FMath::Abs(Tangent.Y)*E.Y;
    return FMath::Abs(FVector::DotProduct(C,N))<360+DepthExtent
        && FMath::Abs(FVector::DotProduct(C,Tangent))<Width/2+70+SideExtent;
}
static bool Fits(const FBox& Box,const FObject& Module,const FProfile& P,const TArray<FBox>& Occupied,bool Web)
{
    bool InsideCell=false;
    for(const auto& V:Module->GetArrayField(TEXT("cells")))
    {
        const auto Cell=V->AsObject(); const FVector Min=Vector(Cell,TEXT("min")),Max=Vector(Cell,TEXT("max"));
        if(Box.Min.X>=Min.X+24 && Box.Max.X<=Max.X-24 && Box.Min.Y>=Min.Y+24 && Box.Max.Y<=Max.Y-24)
        {InsideCell=true;break;}
    }
    if(!InsideCell) return false; // broad phase only; actual support is queried during assembly
    for(const FBox& B:Occupied) if(B.ExpandBy(8).Intersect(Box)) return false;
    for(const FBox& B:P.KeepClear) if(B.Intersect(Box)) return false;
    for(const auto& V:Module->GetArrayField(TEXT("ports"))) if(NearDoor(Box,V->AsObject())) return false;
    const TArray<TSharedPtr<FJsonValue>>* Sides=nullptr;
    if(Module->TryGetArrayField(TEXT("side_sockets"),Sides))
        for(const auto& V:*Sides) if(NearDoor(Box,V->AsObject())) return false;
    if(!Web) for(const auto& V:Module->GetArrayField(TEXT("anchors")))
    {
        const auto A=V->AsObject(); const FVector Location=Vector(A,TEXT("position"));
        const FString Role=A->GetStringField(TEXT("role"));
        const double Radius=Role.Contains(TEXT("encounter"))?220:Role.Contains(TEXT("chest"))?210:150;
        if(FMath::Abs(Location.Z-Box.Min.Z)<140 && Box.ExpandBy(FVector(Radius,Radius,140)).IsInsideOrOn(Location)) return false;
    }
    return true;
}

static FProfile Profile(const FObject& Module)
{
    FString Family=Module->GetStringField(TEXT("id"));Module->TryGetStringField(TEXT("family_id"),Family);
    FProfile P=Profile(Family);
    const TSharedPtr<FJsonObject>* Parameters=nullptr;
    if(Module->TryGetObjectField(TEXT("dressing_parameters"),Parameters))
    {
        double Rear=0,Bridge=0,Core=0;
        (*Parameters)->TryGetNumberField(TEXT("rear_delta_cm"),Rear);
        (*Parameters)->TryGetNumberField(TEXT("bridge_delta_cm"),Bridge);
        (*Parameters)->TryGetNumberField(TEXT("core_offset_cm"),Core);
        if(Family==TEXT("Drainage"))
        {
            for(auto& S:P.Floor)if(S.Position.Y<-1630)S.Position.Y-=Rear;
            for(auto& S:P.Web)if(S.Position.Y<-1630)S.Position.Y-=Rear;
            if(P.KeepClear.IsValidIndex(1))P.KeepClear[1]=P.KeepClear[1].ShiftBy(FVector(0,-Bridge,0));
        }
        else if(Family==TEXT("VentilationLoop")&&!P.KeepClear.IsEmpty())
            P.KeepClear[0]=P.KeepClear[0].ShiftBy(FVector(Core,0,0));
    }
    return P;
}

static TArray<TSharedPtr<FJsonValue>> Build(const FObject& Module,int32 Seed,int32 ModuleIndex)
{
    const FProfile P=Profile(Module);
    TArray<TSharedPtr<FJsonValue>> Parts;
    if(P.Floor.IsEmpty()) return Parts;
    // Independent stream: dressing changes never alter branch, treasure or boss selection.
    FRandomStream Random(int32(uint32(Seed)^0x5D23A71Bu^(uint32(ModuleIndex)*0x9E3779B9u)));
    TArray<FBox> Occupied;
    int32 FloorCount=0,Ladders=0;
    int32 Cluster=INDEX_NONE;
    bool Primary=false;
    int32 ParentItem=INDEX_NONE;
    FVector ParentPosition=FVector::ZeroVector;
    FString Arrangement=TEXT("floor");
    const TArray<FBox> NoProvisionalOccupancy;
    auto Add=[&](EProp Type,const FVector& Position,const FRotator& Rotation,double Scale,bool Web,FVector WallNormal=FVector::ZeroVector)
    {
        if(!Web && FloorCount>=P.MaxFloorProps) return false;
        const FBox Rotated=AssetBox(Type,Rotation,Scale);
        // A sideways barrel/bucket rests on its transformed bottom, not its original pivot.
        // Preserve the authored support height separately for the later real floor query.
        const FVector Pivot=Position+FVector(0,0,Web?0:-Rotated.Min.Z);
        FBox Box=Rotated.ShiftBy(Pivot);
        // Floor candidates may share a footprint: actual mesh envelopes and support
        // relationships decide separation/stacking during assembly, not expanded AABBs.
        if(!Fits(Box,Module,P,Web?Occupied:NoProvisionalOccupancy,Web)) return false;
        auto Part=MakeShared<FJsonObject>();
        Part->SetStringField(TEXT("mesh"),FString(TEXT("/Game/Dungeons/ArtPass20260922/Meshes/SM_Prop_"))+Assets[uint8(Type)].Name);
        Part->SetArrayField(TEXT("position"),Array(Pivot)); Part->SetArrayField(TEXT("scale"),Array(FVector(Scale)));
        Part->SetNumberField(TEXT("yaw"),Rotation.Yaw);
        Part->SetNumberField(TEXT("pitch"),Rotation.Pitch); Part->SetNumberField(TEXT("roll"),Rotation.Roll);
        Part->SetArrayField(TEXT("materials"),TArray<TSharedPtr<FJsonValue>>());
        Part->SetBoolField(TEXT("collision"),false); Part->SetBoolField(TEXT("fluid"),false);
        Part->SetBoolField(TEXT("affects_navigation"),false); Part->SetBoolField(TEXT("dressing"),true);
        Part->SetBoolField(TEXT("dressing_wall"),Web);
        if(Web) Part->SetArrayField(TEXT("dressing_normal"),Array(WallNormal));
        else
        {
            Part->SetNumberField(TEXT("dressing_base_z"),Position.Z);
            Part->SetNumberField(TEXT("dressing_cluster"),Cluster);
            Part->SetBoolField(TEXT("dressing_primary"),Primary);
            Part->SetNumberField(TEXT("dressing_item"),FloorCount);
            Part->SetNumberField(TEXT("dressing_type"),int32(Type));
            Part->SetNumberField(TEXT("dressing_parent"),ParentItem);
            Part->SetArrayField(TEXT("dressing_parent_position"),Array(ParentPosition));
            Part->SetStringField(TEXT("dressing_arrangement"),Arrangement);
            Part->SetNumberField(TEXT("dressing_seed"),int32(Random.GetUnsignedInt()));
        }
        Part->SetBoolField(TEXT("cast_shadow"),!Web);
        Parts.Add(MakeShared<FJsonValueObject>(Part)); Occupied.Add(Box);
        if(!Web) {++FloorCount; if(Type==EProp::Ladder) ++Ladders;}
        return true;
    };
    TArray<int32> Slots;
    for(int32 I=0;I<P.Floor.Num();++I) Slots.Add(I);
    for(int32 I=Slots.Num()-1;I>0;--I) Slots.Swap(I,Random.RandRange(0,I));
    const int32 Target=Random.RandRange(P.MinClusters,P.MaxClusters);
    int32 Clusters=0;
    TArray<FVector> Centers;
    auto Pose=[&](EProp Type,const FSocket& S)
    {
        const bool Round=Type==EProp::Barrel||Type==EProp::Bucket||Type==EProp::Rope;
        FRotator R(0,Round?Random.FRandRange(-180,180):S.Yaw-90+Random.FRandRange(-28,28),0);
        const bool Disordered=S.Use==EUse::Freight||S.Use==EUse::Ruins||S.Use==EUse::Wet;
        const bool CanFall=Type==EProp::Barrel||Type==EProp::Bucket||Type==EProp::Extinguisher||Type==EProp::Lantern;
        if(CanFall&&Random.FRand()<(Disordered?.55f:.35f))
        {
            // Horizontal long axis, with independent axial spin. Mesh contact is solved
            // later from the real geometry; every fallen barrel need not show one side.
            R=(FQuat(FVector::UpVector,FMath::DegreesToRadians(R.Yaw))
                *FQuat(FVector::ForwardVector,PI*.5)
                *FQuat(FVector::UpVector,Random.FRandRange(-PI,PI))).Rotator();
        }
        return R;
    };
    for(int32 I:Slots)
    {
        if(Clusters>=Target) break;
        const auto& S=P.Floor[I]; const FRotator Facing(0,S.Yaw,0);
        const FVector Normal=Facing.Vector(),Tangent(-Normal.Y,Normal.X,0);
        EProp Main=EProp::Bucket;
        const int32 Choice=Random.RandRange(0,99);
        switch(S.Use)
        {
        case EUse::Service: Main=Choice<38?EProp::Ladder:Choice<72?EProp::Extinguisher:EProp::Barrel;break;
        case EUse::Wet: Main=Choice<60?EProp::Bucket:EProp::Barrel;break;
        case EUse::Freight: Main=Choice<75?EProp::Barrel:EProp::Rope;break;
        case EUse::Ruins: Main=Choice<40?EProp::Ladder:Choice<75?EProp::Rope:EProp::Lantern;break;
        case EUse::Quiet: Main=Choice<65?EProp::Lantern:EProp::Rope;break;
        }
        if(Main==EProp::Ladder && Ladders>=1) Main=EProp::Bucket;
        Cluster=I;Primary=true;ParentItem=INDEX_NONE;Arrangement=TEXT("floor");
        const FRotator MainPose=Pose(Main,S);
        const double MainScale=Random.FRandRange(.96,1.04);
        FVector Center;bool Placed=false;
        // Separate the piles, not every item. A shared spill direction and uneven density
        // below break the old constant-radius necklace around the main prop.
        for(int32 Attempt=0;Attempt<10&&!Placed;++Attempt)
        {
            Center=S.Position+Tangent*Random.FRandRange(-120,120)+Normal*Random.FRandRange(-8,65);
            bool Separated=true;
            for(const FVector& Other:Centers) if(FMath::Abs(Other.Z-Center.Z)<140 && FVector::DistSquared2D(Other,Center)<FMath::Square(210.0))
                {Separated=false;break;}
            Placed=Separated&&Add(Main,Center,MainPose,MainScale,false);
        }
        if(!Placed) continue;
        Centers.Add(Center);
        ++Clusters;
        Primary=false;
        ParentItem=FloorCount-1;
        ParentPosition=Vector(Parts.Last()->AsObject(),TEXT("position"));
        const double MainRadius=AssetBox(Main,MainPose,MainScale).GetExtent().Size2D();
        const bool Dense=Random.FRand()<.72f;
        const int32 Companions=S.Use==EUse::Quiet?Random.RandRange(1,3):Dense?Random.RandRange(3,6):Random.RandRange(0,2);
        const double SpillAngle=Random.FRandRange(-PI,PI);
        for(int32 J=0;J<Companions;++J)
        {
            const float Pick=Random.FRand();
            EProp Small=Pick<.35?EProp::Rope:Pick<.67?EProp::Bucket:Pick<.86?EProp::Extinguisher:EProp::Lantern;
            if(S.Use==EUse::Ruins || S.Use==EUse::Quiet) Small=Random.FRand()<.5?EProp::Lantern:EProp::Rope;
            if(S.Use==EUse::Freight && Main==EProp::Barrel && J<2 && Random.FRand()<.65) Small=EProp::Barrel;
            const FRotator SmallPose=Pose(Small,S);const double Scale=Random.FRandRange(.94,1.06);
            const double SmallRadius=AssetBox(Small,SmallPose,Scale).GetExtent().Size2D();
            const bool Outlier=J==Companions-1&&Random.FRand()<.3f;
            const float Relation=Random.FRand();
            Arrangement=(Main==EProp::Barrel||Main==EProp::Rope)&&Small!=EProp::Barrel&&Relation<.38f?TEXT("stack")
                :Main==EProp::Barrel&&Small!=EProp::Rope&&Relation<.7f?TEXT("lean"):TEXT("heap");
            for(int32 Attempt=0;Attempt<12;++Attempt)
            {
                const double Angle=SpillAngle+Random.FRandRange(-1.9,1.9);
                const double Radius=(MainRadius+SmallRadius)*Random.FRandRange(.42,Outlier?2.1:1.15);
                const FVector At=Center+Tangent*(FMath::Cos(Angle)*Radius)+Normal*(FMath::Sin(Angle)*Radius*Random.FRandRange(.55,1.1));
                if(Add(Small,At,SmallPose,Scale,false)) break;
            }
        }
    }
    Slots.Reset(); for(int32 I=0;I<P.Web.Num();++I) Slots.Add(I);
    for(int32 I=Slots.Num()-1;I>0;--I) Slots.Swap(I,Random.RandRange(0,I));
    const int32 WebTarget=Random.RandRange(1,P.MaxWebs);
    int32 WebCount=0;
    for(int32 I:Slots)
    {
        if(WebCount>=WebTarget) break;
        const auto& S=P.Web[I]; const double Scale=Random.FRandRange(.9,1.2);
        const EProp Type=EProp(int32(EProp::Web1)+Random.RandRange(0,2));
        // Imported webs lie mainly in XY. Turn onto the wall and align their real
        // rotated bounding box to the wall/ceiling, rather than rotating about a guessed centre.
        const FRotator Rotation(90,S.Yaw,Random.FRandRange(-6,6));
        const FBox B=AssetBox(Type,Rotation,Scale);
        const FVector N=FRotator(0,S.Yaw,0).Vector(),E=B.GetExtent();
        const double Depth=FMath::Abs(N.X)*E.X+FMath::Abs(N.Y)*E.Y;
        const FVector At=S.Position+N*(Depth+3)-FVector(0,0,E.Z)-B.GetCenter();
        if(Add(Type,At,Rotation,Scale,true,N)) ++WebCount;
    }
    return Parts;
}
}
