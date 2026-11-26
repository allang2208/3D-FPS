#include "TemperateHillsChapel.h"
#include "ChapelNavigationGeometry.h"
#include "VillageMasonry.h"
#include "ChapelCourtyardDressing.h"
#include "VillagePlantingDisplay.h"
#include "TemperateVillagePerimeter.h"
#include "ChapelShrine.h"
#include "../NPC/ChapelNun.h"
#include "../Dungeons/RandomShrine.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "Kismet/GameplayStatics.h"
#include "TemperateHillsWorld.h"
#include "TemperateForestHabitat.h"
#include "../Building/BronzeTorch.h"
#include "VillageShopTorches.h"
#include "../Building/BuildingDaylight.h"
#include "../Building/ColdSteelDoor.h"
#include "Components/ChildActorComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/Package.h"

namespace TemperateHillsChapel
{
const FName NunComponentName(TEXT("OldChapel_Nun"));

AChapelNun* FindNun(ATemperateHillsWorld* Hills)
{
    if (!IsValid(Hills)) return nullptr;
    const auto* ChapelComponent = FindObjectFast<UChildActorComponent>(Hills, NunComponentName);
    return IsValid(ChapelComponent) ? Cast<AChapelNun>(ChapelComponent->GetChildActor()) : nullptr;
}

const TCHAR* const Roles[] = {
    TEXT("SolidBay"),TEXT("WindowBay"),TEXT("WestGable"),TEXT("EastGable"),TEXT("SlateRoofBay"),
    TEXT("OakTruss"),TEXT("PurlinBay"),TEXT("FloorBay"),TEXT("Foundation"),TEXT("Oculus"),
    TEXT("LancetGlass"),TEXT("OculusGlass"),TEXT("Bellcote"),TEXT("Bell"),
    TEXT("Portal"),TEXT("Door"),TEXT("Lancet"),TEXT("Buttress"),TEXT("Pew"),TEXT("Altar"),
    TEXT("Font"),TEXT("Lectern"),TEXT("Headstone"),TEXT("SanctuarySteps"),
    TEXT("YardWallA"),TEXT("YardWallB"),TEXT("YardPier"),TEXT("YardPathStone"),TEXT("VergeGrass")};
FSoftObjectPath MeshPath(const TCHAR* Role)
{
    if(FCString::Strncmp(Role,TEXT("YardWall"),8)==0 || FCString::Strcmp(Role,TEXT("YardPier"))==0)
        return VillageMasonry::Mesh(FString(TEXT("SM_Chapel")) + Role);
    if(FCString::Strcmp(Role,TEXT("VergeGrass"))==0)
        return FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass/SM_SoftWildGrassLow.SM_SoftWildGrassLow"));
    return FSoftObjectPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_Chapel%s.SM_Chapel%s"),Role,Role));
}
bool IsChapelWorld(const UWorld* World)
{
    if(!World)return false;
    const FString Package=World->GetPackage()->GetName();
    return (World->WorldType==EWorldType::PIE?UWorld::RemovePIEPrefix(Package):Package)==TEXT("/Game/GameMaps/L_TemperateHills_Initial");
}
void AddMeshPaths(TArray<FSoftObjectPath>& Paths)
{
    for(const TCHAR* Role:Roles)Paths.Add(MeshPath(Role));
    if(!IsRunningDedicatedServer()) ChapelCourtyardDressing::AddMeshPaths(Paths);
    RandomShrine::AddMeshPaths(Paths);
    AChapelShrine::AddAssetPaths(Paths);
    TemperateVillagePerimeter::AddMeshPaths(Paths);
}
}

void ATemperateHillsWorld::AssembleOldChapel()
{
    BuildVillagePerimeter();
    if(VillageSite.bHilltop&&!IsValid(VillagePlantingDisplay))
    {VillagePlantingDisplay=GetWorld()->SpawnActor<AVillagePlantingDisplay>();VillagePlantingDisplay->Initialize(this);}
    using namespace TemperateHillsChapel;
    TMap<FName,UStaticMesh*> Meshes;
    for(const TCHAR* MeshRole:Roles)
    {
        UStaticMesh* Mesh=Cast<UStaticMesh>(MeshPath(MeshRole).ResolveObject());
        if(!Mesh){UE_LOG(LogTemp,Error,TEXT("HILLS_CHAPEL missing streamed mesh %s"),MeshRole);return;}
        Meshes.Add(FName(MeshRole),Mesh);
    }
    const FVector Floor=ChapelSite.Ground+FVector(0,0,FTemperateChapelSite::FloorRise);
    constexpr double Size=FTemperateChapelSite::AssemblyScale;
    const double SiteYaw=FMath::RadiansToDegrees(FMath::Atan2(ChapelSite.Axis.Y,ChapelSite.Axis.X));
    const FQuat Orientation=FRotator(0.,SiteYaw,0.).Quaternion();
    auto AtFloor=[&](FVector Local){return Floor+Orientation.RotateVector(Local*Size);};
    if(GroundMID)
    {
        GroundMID->SetVectorParameterValue(TEXT("ChapelGroundAndTrail"),FLinearColor(
            Floor.X,Floor.Y,ChapelSite.Trail.X,ChapelSite.Trail.Y));
        GroundMID->SetScalarParameterValue(TEXT("ChapelAssemblyScale"),Size);
        for(int32 I=1;I<UE_ARRAY_COUNT(FTemperateChapelSite::GraveWalk);++I)
        {
            const auto A=FTemperateChapelSite::GraveWalk[I-1],B=FTemperateChapelSite::GraveWalk[I];
            GroundMID->SetVectorParameterValue(FName(*FString::Printf(TEXT("ChapelGraveSegment%d"),I)),FLinearColor(A.X,A.Y,B.X,B.Y));
        }
    }
    TMap<FName,TArray<FTransform>> Groups;
    auto Put=[&](const TCHAR* MeshRole,double X,double Y,double Z,double Yaw=0.,FVector Scale=FVector::OneVector)
    {
        Groups.FindOrAdd(FName(MeshRole)).Emplace(FRotator(0,SiteYaw+Yaw,0),AtFloor(FVector(X,Y,Z)),Scale*Size);
    };
    Put(TEXT("Foundation"),0,0,0);
    Put(TEXT("WestGable"),-766,0,0);Put(TEXT("EastGable"),775,0,0);
    // Project the carved face beyond the masonry without moving the inward door rebate.
    Put(TEXT("Portal"),-777.2,0,0,0,FVector(1.82,1,1));
    Put(TEXT("Oculus"),-766,0,532);Put(TEXT("OculusGlass"),-766,0,532);
    Put(TEXT("Bellcote"),-766,0,850);Put(TEXT("Bell"),-766,-70,925);
    // Daylight comes through the real apertures. Nearby artificial rectangle
    // lights used to bleach the deep stone reveals when viewed from outside.
    // Reuse the village's view-local adaptation, bounded by the nave interior.
    if(GetNetMode()!=NM_DedicatedServer)
    {
        auto* VisionRoom=NewObject<UChildActorComponent>(this,TEXT("OldChapel_InteriorVision"));
        VisionRoom->SetupAttachment(RootComponent);
        const FTransform RoomTransform(Orientation,Floor,FVector(Size));
        VisionRoom->SetRelativeTransform(RoomTransform.GetRelativeTransform(RootComponent->GetComponentTransform()));
        VisionRoom->SetChildActorClass(ABuildingDaylight::StaticClass());
        AddInstanceComponent(VisionRoom);
        VisionRoom->RegisterComponent();
        if(auto* Room=Cast<ABuildingDaylight>(VisionRoom->GetChildActor()))
        {
            Room->RoomMinimum=FVector(-722.,-348.,0.);
            Room->RoomMaximum=FVector(746.,348.,450.);
            // The deep stone nave uses the same daylight adaptation as the tavern hall.
            Room->ExposureCompensation=2.f;
            Room->AdditionalDarkAdaptationStops=4.f;
            Room->EntranceTransitionCm=60.f;
            Room->ShadowContrast=.5f;
            // Child actor registration may have already run construction with
            // default house bounds; apply the authored chapel bounds as well.
            Room->OnConstruction(Room->GetActorTransform());
        }
    }
    for(int32 Bay=0;Bay<4;++Bay)
    {
        const double X=-600.+400.*Bay;
        // The long walls terminate at the inner faces of the gables.
        const double StartX=Bay==0?-732.:-800.+400.*Bay;
        const double EndX=Bay==3?750.:-400.+400.*Bay;
        for(int32 Sign:{-1,1})
        {
            const double Y=375.*Sign,Yaw=-90.*Sign;
            // Fit the end bays between the thicker gables and the grid joints.
            Put(Bay?TEXT("WindowBay"):TEXT("SolidBay"),(StartX+EndX)*.5,Y,0,Yaw,FVector(1,(EndX-StartX)/400.,1));
            // Seat the verge just behind the exposed stone gable face.
            const double RoofStart=Bay==0?-788.:X-200.,RoofEnd=Bay==3?788.:X+200.;
            Put(TEXT("SlateRoofBay"),(RoofStart+RoofEnd)*.5,0,0,Sign==1?0.:180.,
                FVector((RoofEnd-RoofStart)/400.,1,1));
            if(Bay)
            {
                const double WindowX=(StartX+EndX)*.5;
                Put(TEXT("Lancet"),WindowX,Y,136,-Yaw,FVector(1.48,1,1));
                Put(TEXT("LancetGlass"),WindowX,Y,136,-Yaw);
            }
        }
        const double TimberStart=Bay==0?-732.:X-200.,TimberEnd=Bay==3?792.:X+200.;
        Put(TEXT("PurlinBay"),(TimberStart+TimberEnd)*.5,0,0,0,FVector((TimberEnd-TimberStart)/400.,1,1));
    }
    Put(TEXT("Lancet"),775,0,260,180,FVector(1.48,1,1));Put(TEXT("LancetGlass"),775,0,260,180);
    for(double X:{-400.,0.,400.})Put(TEXT("OakTruss"),X,0,0);
    // Local +X is the tall back. Bed it into the rough wall face at |Y|=400 cm.
    constexpr double ButtressCenterY=442.;
    // Each carved pier keys two centimetres into its projecting bearing stone.
    constexpr double ButtressBaseZ=-8.;
    for(int32 Sign:{-1,1})for(double X:{-754.,-400.,0.,400.,754.})
        Put(TEXT("Buttress"),X,Sign*ButtressCenterY,ButtressBaseZ,-90.*Sign);
    for(int32 I=0;I<8;++I)for(int32 J=0;J<4;++J)
        Put(TEXT("FloorBay"),-639.375+I*185.25,-262.5+J*175.,0,0,FVector(.92625,.875,1));
    for(double X:{-360.,-170.,20.,210.})for(int32 S:{-1,1})
        Put(TEXT("Pew"),X,205.*S,0,180);
    Put(TEXT("SanctuarySteps"),350,0,0);
    Put(TEXT("Altar"),570,0,20,0,FVector(.75));
    Put(TEXT("Font"),-464,-194,0);
    Put(TEXT("Lectern"),460,-224,20,20);
    // Stand behind the stone altar on the chapel centerline, facing the entrance.
    auto* Nun=FindObjectFast<UChildActorComponent>(this,NunComponentName);
    if(!Nun)
    {
        Nun=NewObject<UChildActorComponent>(this,NunComponentName);
        Nun->SetupAttachment(RootComponent);
        Nun->SetChildActorClass(AChapelNun::StaticClass());
        AddInstanceComponent(Nun);
    }
    const FTransform NunTransform(FRotator(0,SiteYaw+180.,0),AtFloor(FVector(665.,0.,20.))+FVector(0,0,84.));
    Nun->SetRelativeTransform(NunTransform.GetRelativeTransform(RootComponent->GetComponentTransform()));
    if(!Nun->IsRegistered())Nun->RegisterComponent();

    for(const auto& Grave : FTemperateChapelSite::Graves)
    {
        const FVector2D At=ChapelSite.World(Grave.Head.X*Size,Grave.Head.Y*Size);
        Put(TEXT("Headstone"),Grave.Head.X,Grave.Head.Y,(Height(At.X,At.Y)-Floor.Z)/Size-14.,Grave.Yaw);
    }
    // Bed small details on the triangles rendered around the chapel (one metre grid).
    // The user can still dig on the path; load existing edits into the support height.
    const double HalfWorld=SizeMeters*50.;
    auto PlaceOnSoil=[&](FName Kind,FVector2D Local,double Width,double Tall,double Yaw,double Sink)
    {
        UStaticMesh* const* Mesh=Meshes.Find(Kind);
        if(!Mesh) return;
        const FVector2D At=ChapelSite.World(Local.X*Size,Local.Y*Size);
        const double X0=FMath::FloorToDouble((At.X+HalfWorld)/100.)*100.-HalfWorld;
        const double Y0=FMath::FloorToDouble((At.Y+HalfWorld)/100.)*100.-HalfWorld;
        const double U=(At.X-X0)*.01,V=(At.Y-Y0)*.01;
        const double A=Height(X0,Y0),D=Height(X0+100.,Y0+100.);
        const double B=U>=V?Height(X0+100.,Y0):Height(X0,Y0+100.);
        const double DX=U>=V?B-A:D-B,DY=U>=V?D-B:B-A;
        const double Z=A+DX*U+DY*V;
        const FVector Up=FVector(-DX,-DY,100.).GetSafeNormal();
        const FQuat Tilt=FQuat(Up,FMath::DegreesToRadians(SiteYaw+Yaw))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
        const FBox Box=(*Mesh)->GetBoundingBox();
        const double ScaleXY=Width/FMath::Max(1.,FMath::Max(Box.GetSize().X,Box.GetSize().Y));
        const FVector S(ScaleXY,ScaleXY,Tall/FMath::Max(1.,Box.GetSize().Z));
        const FVector Root=FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z)*S;
        Groups.FindOrAdd(Kind).Emplace(Tilt,FVector(At,Z-Sink)-Tilt.RotateVector(Root),S);
    };
    // The west footing ends at X=-820. With its back against that face, the
    // pew leaves the stair, torch, and a full standing space in front clear.
    // Place it on all peers so hits and seated transforms resolve to the same instance.
    const FVector PewSize=Meshes.FindChecked(TEXT("Pew"))->GetBoundingBox().GetSize()*Size;
    PlaceOnSoil(TEXT("Pew"),FTemperateChapelSite::RestPew,FMath::Max(PewSize.X,PewSize.Y),PewSize.Z,0.,.6);
    if(GetNetMode()!=NM_DedicatedServer)
    {
        ChapelCourtyardDressing::ResolveMeshes(Meshes);
        ChapelCourtyardDressing::Place(ChapelSite,Seed,PlaceOnSoil);
    }
    // The yard kit uses world centimetres. Seat the coursing in short level steps
    // while carrying the masonry into the corner piers on either end of each run.
    const auto& Yard=ChapelSite.YardNodes;
    const FVector2D GateAcross=(Yard[0]-Yard[FTemperateChapelSite::YardNodeCount-1]).GetSafeNormal();
    const double PostYaw=FMath::RadiansToDegrees(FMath::Atan2(GateAcross.Y,GateAcross.X))-90.;
    FRandomStream Masonry(Seed);
    for(int32 I=0;I<FTemperateChapelSite::YardNodeCount;++I)
    {
        const FVector2D A=Yard[I];
        const bool bGate=I==0||I==FTemperateChapelSite::YardNodeCount-1;
        Groups.FindOrAdd(TEXT("YardPier")).Emplace(FRotator(0,bGate?PostYaw:SiteYaw,0),
            FVector(A,BaseHeight(A.X,A.Y)),FVector(1.,1.,bGate?1.:.90));
        if(I+1==FTemperateChapelSite::YardNodeCount)break;
        const FVector2D B=Yard[I+1],Along=(B-A).GetSafeNormal();
        const double Length=FVector2D::Distance(A,B);
        const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(Along.Y,Along.X));
        // Stop inside the solid piers. Their caps and finished end faces stay exposed.
        const FVector2D Start=A+Along*23.;
        const double Run=Length-46.;
        const int32 Count=FMath::Max(1,FMath::RoundToInt(Run/165.));
        const double Bay=Run/Count;
        double PreviousZ=BaseHeight(Start.X,Start.Y);
        for(int32 J=0;J<Count;++J)
        {
            const FVector2D Mid=Start+Along*((J+.5)*Bay);
            const FVector2D End=Start+Along*((J+1)*Bay);
            const double MidZ=BaseHeight(Mid.X,Mid.Y),EndZ=BaseHeight(End.X,End.Y);
            const int32 Steps=FMath::Clamp(FMath::CeilToInt((FMath::Abs(MidZ-PreviousZ)+FMath::Abs(EndZ-MidZ))/40.),1,6);
            const double Span=Bay/Steps;
            for(int32 K=0;K<Steps;++K)
            {
                const FVector2D P=Start+Along*(J*Bay+(K+.5)*Span);
                const TCHAR* WallMesh=Masonry.RandRange(0,1)?TEXT("YardWallA"):TEXT("YardWallB");
                const double Facing=Masonry.RandRange(0,1)?Yaw:Yaw+180.;
                const double Z=Steps==1?MidZ:BaseHeight(P.X,P.Y);
                Groups.FindOrAdd(FName(WallMesh)).Emplace(FRotator(0,Facing,0),FVector(P,Z),FVector((Span+1.5)/180.,1.,1.));
            }
            PreviousZ=EndZ;
        }
    }
    for(const auto& Pair:Groups)
    {
        const FName PartName(*FString::Printf(TEXT("OldChapel_%s"),*Pair.Key.ToString()));
        auto* Part=Pair.Key==TEXT("Foundation")?NewObject<UChapelFoundationNavMesh>(this,PartName):
            NewObject<UInstancedStaticMeshComponent>(this,PartName);
        // Every peer assembles these fixed instances locally. They are valid
        // walking/interaction collision, but are not network movement bases.
        Part->SetMobility(EComponentMobility::Static);
        if(GetNetMode()==NM_Client) Part->SetCanEverAffectNavigation(false);
        const bool bCourtyardDetail=ChapelCourtyardDressing::IsDetail(Pair.Key);
        if(!bCourtyardDetail) Part->ComponentTags.Add(TEXT("HillsStaticSupport"));
        Part->SetupAttachment(RootComponent);
        Part->SetStaticMesh(Meshes.FindChecked(Pair.Key));
        // Surface masks use centimetres above the chapel floor for every seed and both wall orientations.
        if(!bCourtyardDetail)
        {
            Part->SetCustomPrimitiveDataVector4(0,FVector4(Floor.X,Floor.Y,Floor.Z,Size));
            Part->SetCustomPrimitiveDataFloat(4,FMath::DegreesToRadians(SiteYaw));
        }
        const bool bDetail=bCourtyardDetail||Pair.Key==TEXT("VergeGrass")||Pair.Key==TEXT("YardPathStone");
        if(bDetail) Part->SetCullDistances(bCourtyardDetail?4500:3000,bCourtyardDetail?6500:4200);
        if(bCourtyardDetail)
        {
            Part->SetCanEverAffectNavigation(false);
            Part->SetReceivesDecals(false);
            if(Pair.Key==TEXT("CourtyardGrass")||Pair.Key==TEXT("CourtyardHerb")||Pair.Key==TEXT("CourtyardFlower"))
                Part->SetCastShadow(false);
        }
        if(Pair.Key==TEXT("VergeGrass"))Part->SetCastShadow(false);
        const bool bOverhead=Pair.Key==TEXT("OculusGlass")||Pair.Key==TEXT("PurlinBay")||Pair.Key==TEXT("Bell");
        Part->SetCollisionProfileName((bDetail||bOverhead)?TEXT("NoCollision"):TEXT("BlockAll"));
        Part->SetGenerateOverlapEvents(false);
        // The glazing sections transmit sunlight; only the opaque lead cames cast their pattern.
        AddInstanceComponent(Part);
        Part->RegisterComponent();
        Part->AddInstances(Pair.Value,false,true);
    }
    // The bronze bracket starts 16 cm ahead of its pivot. At a 21 cm inset
    // the arm beds 5 cm into the stone and the cup stands 29 cm clear.
    auto MountTorch=[&](FName Name,FVector WallPoint,FVector Outward,bool bAlwaysLit=false)
    {
        Outward=Orientation.RotateVector(Outward);
        const FVector Pivot=AtFloor(WallPoint)-Outward*21.;
        const FTransform Mount(Outward.Rotation(),Pivot);
        auto* Socket=NewObject<UChildActorComponent>(this,Name);
        Socket->SetupAttachment(RootComponent);
        Socket->SetRelativeTransform(Mount.GetRelativeTransform(RootComponent->GetComponentTransform()));
        Socket->SetChildActorClass(ABronzeTorch::StaticClass());
        AddInstanceComponent(Socket);
        Socket->RegisterComponent();
        if(auto* Torch=Cast<ABronzeTorch>(Socket->GetChildActor()))
        {
            Torch->SetSceneSpecularScale(VillageShopTorches::FixtureSpecular);
            // Interior flames stay lit independently of the world's day/night clock.
            if(bAlwaysLit)Torch->SetLit(true);
            if(GetNetMode()==NM_DedicatedServer)Torch->SetActorTickEnabled(false);
        }
    };
    // West gable exterior face at X=-800; both mounts sit clear of the carved portal.
    MountTorch(TEXT("OldChapel_EntryTorchA"),FVector(-800,-151,142),-FVector::ForwardVector);
    MountTorch(TEXT("OldChapel_EntryTorchB"),FVector(-800, 151,142),-FVector::ForwardVector);
    // Mount on solid masonry between features, below the oak knees and above the pew ends.
    MountTorch(TEXT("OldChapel_NaveTorchA"),FVector(-510,-350,150), FVector::RightVector,true);
    MountTorch(TEXT("OldChapel_NaveTorchB"),FVector(-510, 350,150),-FVector::RightVector,true);
    MountTorch(TEXT("OldChapel_NaveTorchC"),FVector( 330,-350,150), FVector::RightVector,true);
    MountTorch(TEXT("OldChapel_NaveTorchD"),FVector( 330, 350,150),-FVector::RightVector,true);
    if(HasAuthority())
    {
        FRandomStream ShrineRandom(int32(uint32(Seed)^DungeonRunDomains::ShrineSelection));
        const auto Choice=RandomShrine::Choose(ShrineRandom);
        auto* ShrineMesh=Choice?Cast<UStaticMesh>(FSoftObjectPath(Choice->GetStringField(TEXT("mesh"))).ResolveObject()):nullptr;
        if(ShrineMesh)
        {
            const FVector2D Point=ChapelSite.Shrine();
            double MeshFrontYaw=90.;Choice->TryGetNumberField(TEXT("front_local_yaw_deg"),MeshFrontYaw);
            const FQuat Facing=FRotator(0.,SiteYaw+180.-MeshFrontYaw,0.).Quaternion();
            // Keep the combat/interaction root at human height; the actor seats its
            // doubled statue and round stone pedestal from the actual mesh bounds.
            const FTransform Placement(Facing,FVector(Point,Height(Point.X,Point.Y)+100.));
            if(auto* Shrine=GetWorld()->SpawnActorDeferred<AChapelShrine>(AChapelShrine::StaticClass(),Placement,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
            {
                Shrine->WorldSeed=Seed;Shrine->WorldId=WorldId;
                UGameplayStatics::FinishSpawningActor(Shrine,Placement);
                ChapelShrine=Shrine;
            }
        }
        else UE_LOG(LogTemp,Error,TEXT("HILLS_SHRINE selected mesh unavailable"));
        FActorSpawnParameters Params;Params.Owner=this;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        // The pointed leaf opens from the inner face of the stone reveal.
        const FTransform DoorTransform(Orientation,AtFloor(FVector(-725,0,1)),FVector(Size));
        auto* Door=GetWorld()->SpawnActor<AColdSteelDoor>(AColdSteelDoor::StaticClass(),DoorTransform,Params);
        if(Door)
        {
            Door->ConfigureStandaloneLeaf(Meshes.FindChecked(TEXT("Door")),false,.7f,0.f);
            Door->SetInwardOnly();
            ChapelDoor=Door;
        }
    }
}

