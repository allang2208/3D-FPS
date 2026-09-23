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
    int32 MinClusters = 2, MaxClusters = 4, MaxFloorProps = 9, MaxWebs = 2;
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
        P.MinClusters=1; P.MaxClusters=2; P.MaxFloorProps=4;
        P.Floor = {{{-430,-275,0},0,Quiet},{{430,-765,0},180,Quiet},{{-420,-870,0},90,Quiet}};
        P.Web = {{{-505,-110,337},0},{{505,-920,337},180},{{-440,-995,337},90}};
        P.KeepClear = {FBox(FVector(-240,-780,-5),FVector(240,0,240))};
    }
    else if (Id == TEXT("BossPumpHall"))
    {
        P.MinClusters=4; P.MaxClusters=6; P.MaxFloorProps=14; P.MaxWebs=3;
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

static TArray<TSharedPtr<FJsonValue>> Build(const FObject& Module,int32 Seed,int32 ModuleIndex)
{
    const FProfile P=Profile(Module->GetStringField(TEXT("id")));
    TArray<TSharedPtr<FJsonValue>> Parts;
    if(P.Floor.IsEmpty()) return Parts;
    // Independent stream: dressing changes never alter branch, treasure or boss selection.
    FRandomStream Random(int32(uint32(Seed)^0x5D23A71Bu^(uint32(ModuleIndex)*0x9E3779B9u)));
    TArray<FBox> Occupied;
    int32 FloorCount=0,Ladders=0;
    auto Add=[&](EProp Type,const FVector& Position,const FRotator& Rotation,double Scale,bool Web,FVector WallNormal=FVector::ZeroVector)
    {
        if(!Web && FloorCount>=P.MaxFloorProps) return false;
        FBox Box=AssetBox(Type,Rotation,Scale).ShiftBy(Position);
        if(!Fits(Box,Module,P,Occupied,Web)) return false;
        auto Part=MakeShared<FJsonObject>();
        Part->SetStringField(TEXT("mesh"),FString(TEXT("/Game/Dungeons/ArtPass20260922/Meshes/SM_Prop_"))+Assets[uint8(Type)].Name);
        Part->SetArrayField(TEXT("position"),Array(Position)); Part->SetArrayField(TEXT("scale"),Array(FVector(Scale)));
        Part->SetNumberField(TEXT("yaw"),Rotation.Yaw);
        Part->SetNumberField(TEXT("pitch"),Rotation.Pitch); Part->SetNumberField(TEXT("roll"),Rotation.Roll);
        Part->SetArrayField(TEXT("materials"),TArray<TSharedPtr<FJsonValue>>());
        Part->SetBoolField(TEXT("collision"),false); Part->SetBoolField(TEXT("fluid"),false);
        Part->SetBoolField(TEXT("affects_navigation"),false); Part->SetBoolField(TEXT("dressing"),true);
        Part->SetBoolField(TEXT("dressing_wall"),Web);
        if(Web) Part->SetArrayField(TEXT("dressing_normal"),Array(WallNormal));
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
    for(int32 I:Slots)
    {
        if(Clusters>=Target) break;
        const auto& S=P.Floor[I]; const FRotator Facing(0,S.Yaw,0);
        const FVector Normal=Facing.Vector(),Tangent(-Normal.Y,Normal.X,0);
        FVector Center=S.Position+Tangent*Random.FRandRange(-14,14)+Normal*Random.FRandRange(-4,6);
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
        const double Yaw=Main==EProp::Barrel?Random.FRandRange(-180,180):S.Yaw-90+Random.FRandRange(-9,9);
        if(!Add(Main,Center,FRotator(0,Yaw,0),Random.FRandRange(.97,1.03),false)) continue;
        ++Clusters;
        const int32 Companions=S.Use==EUse::Quiet?Random.RandRange(0,1):Random.RandRange(0,2);
        for(int32 J=0;J<Companions;++J)
        {
            EProp Small=Random.FRand()<.55?EProp::Rope:EProp::Bucket;
            if(S.Use==EUse::Ruins || S.Use==EUse::Quiet) Small=Random.FRand()<.5?EProp::Lantern:EProp::Rope;
            if(S.Use==EUse::Freight && Main==EProp::Barrel && J==0 && Random.FRand()<.5) Small=EProp::Barrel;
            const FVector At=Center+Tangent*(J==0?1.0:-1.0)*Random.FRandRange(78,94)+Normal*Random.FRandRange(0,12);
            Add(Small,At,FRotator(0,Random.FRandRange(-180,180),0),Random.FRandRange(.96,1.04),false);
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
