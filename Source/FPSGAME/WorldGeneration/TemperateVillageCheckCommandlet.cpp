#include "TemperateVillageCheckCommandlet.h"
#include "TemperateHillsWorld.h"
#include "TemperateHillsBackdrop.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

int32 UTemperateVillageCheckCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("DefenseBlocks")))return CheckDefenseBlocks(Params);
    UWorld* Map=LoadObject<UWorld>(nullptr,TEXT("/Game/GameMaps/L_TemperateHills_Initial.L_TemperateHills_Initial"));
    ATemperateHillsWorld* Hills=nullptr;
    if(Map && Map->PersistentLevel)
        for(const auto& Actor:Map->PersistentLevel->Actors)
            if((Hills=Cast<ATemperateHillsWorld>(Actor)))break;
    if(!Hills || !Hills->Assets)return 1;

    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_World"),0));
    const float MapSize=Hills->SizeMeters;
    struct FScenario { int32 Seed,Version; float Size; };
    TArray<FScenario> Cases;
    if(Save)Cases.Add({Save->Seed,Save->GeneratorVersion,MapSize});
    for(int32 Seed:{0,-1,122,7391,20261111,438071,-104729,1704983,32768,8171,3406982,INT32_MIN})
        Cases.Add({Seed,2,MapSize});
    for(int32 Seed:{0,122,7391,-104729})
        for(float Size:{256.f,384.f,640.f})Cases.Add({Seed,2,Size});
    Cases.Add({7391,1,MapSize});
    FString Rows=TEXT("seed,version,size_m,user_save,placed,center_x_m,center_y_m,center_z_m,spawn_dx_m,spawn_dy_m,shoulder_m,pad_error_cm,max_approach_degrees,mouth_offset_cm,wet_samples,house_proxy_error_cm,side_lane,outer_slope_p95_degrees,replay_match\n");
    int32 Errors=0;
    for(int32 I=0;I<Cases.Num();++I)
    {
        const auto C=Cases[I];
        Hills->Seed=C.Seed; Hills->GeneratorVersion=C.Version; Hills->SizeMeters=C.Size;
        Hills->bStartLocationCached=false;
        Hills->RiverPlan.Reset(); Hills->ForestWaterPlan.Reset(); Hills->VillageSite={}; Hills->ChapelSite={};
        Hills->NetEdits.Reset();
        if(I==0 && Save)
        {
            Hills->NetEdits=Save->Edits;
            for(const auto& Crater:Save->Craters)
            {
                FHillsTerrainEditRecord R;
                R.X=Crater.X; R.Y=Crater.Y; R.Radius=Crater.Radius; R.Amplitude=-Crater.Depth; R.Lip=Crater.Rim;
                R.Seed=int32(TemperateHillsSurface::Key(int32(R.X),int32(R.Y),uint32(C.Seed),7043));
                Hills->NetEdits.Add(R);
            }
        }
        Hills->ConvertNetEdits();
        const double Half=C.Size*50.;
        const FVector Spawn=Hills->GetStartLocation();
        if(!Hills->Assets->RiverMaterial.IsNull())
            Hills->RiverPlan=TemperateRiver::Generate(C.Seed,Half,FVector2D(Spawn),Hills->Assets->RiverBankReliefCm,C.Version);
        else
        {
            auto River=MakeShared<TemperateRiver::FPlan,ESPMode::ThreadSafe>();
            River->GenerationVersion=C.Version; River->BuildRainforest(C.Seed,Half); Hills->RiverPlan=River;
        }
        Hills->ForestWaterPlan=TemperateForestWater::Generate(C.Seed,Half,Hills->RiverPlan,Hills->TerrainEdits,C.Version);
        const auto Natural=Hills->TerrainEdits.IsEmpty()?Hills->ForestWaterPlan:TemperateForestWater::Generate(C.Seed,Half,Hills->RiverPlan,{},C.Version);
        Hills->PlanAbandonedVillage(Natural);
        const auto& Village=Hills->VillageSite;
        double Pad=0.,Slope=0.,Mouth=0.,Proxy=0.;
        int32 Wet=0; double P95=0.;
        if(I==0 && Save && Village.bPlaced)
        {
            FString Field=TEXT("x_m,y_m,z_m,river\n");
            for(int32 Y=0;Y<=128;++Y)for(int32 X=0;X<=128;++X)
            {
                const double WX=Half*(X/64.-1.), WY=Half*(Y/64.-1.);
                Field+=FString::Printf(TEXT("%.3f,%.3f,%.3f,%.2f\n"),WX/100.,WY/100.,Hills->Height(WX,WY)/100.,Hills->SampleRiver(WX,WY).Wet);
            }
            FString Points=TEXT("type,x_m,y_m\n");
            auto Mark=[&](const TCHAR* Kind,FVector2D P){Points+=FString::Printf(TEXT("%s,%.4f,%.4f\n"),Kind,P.X/100.,P.Y/100.);};
            Mark(TEXT("spawn"),FVector2D(Spawn));
            if(Hills->ChapelSite.bPlaced)Mark(TEXT("chapel"),FVector2D(Hills->ChapelSite.Ground));
            Mark(TEXT("west"),Village.Mouth(-1.));Mark(TEXT("east"),Village.Mouth(1.));
            for(int32 X=0;X<=200;++X)
            {
                const double WX=Half*(X/100.-1.);Mark(TEXT("valley"),{WX,TemperateHillsSurface::ValleyY(WX,C.Seed)});
            }
            for(const auto& P:Hills->RiverPlan->Points)Mark(TEXT("river"),P.XY);
            for(int32 H=0;H<7;++H) { const auto& B=TemperateVillageLayout::Beds[H]; Mark(TEXT("house"),Village.World(B.X,B.Y)); }
            const FString Dir=FPaths::ProjectSavedDir()/TEXT("VillageSiteReview");
            if(!FFileHelper::SaveStringToFile(Field,*(Dir/TEXT("current-terrain.csv"))) ||
               !FFileHelper::SaveStringToFile(Points,*(Dir/TEXT("current-landmarks.csv"))))return 2;
        }
        if(Village.bPlaced)
        {
            for(int32 X=-4600;X<=4600;X+=100)for(int32 Y=-3200;Y<=3200;Y+=100)
            {
                const auto P=Village.World(X,Y);
                const double Datum=Hills->ChapelSite.Grade(P.X,P.Y,Village.Ground.Z);
                Pad=FMath::Max(Pad,FMath::Abs(Hills->Height(P.X,P.Y)-Datum));
                Wet+=Hills->SampleRiver(P.X,P.Y).Wet>0 || Hills->ForestWaterPlan->Sample(P.X,P.Y).Wet;
            }
            for(int32 H=0;H<7;++H)
            {
                const auto& B=TemperateVillageLayout::Beds[H];
                for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)
                {
                    const auto P=Village.World(B.X+X*B.HalfX*B.Cos-Y*B.HalfY*B.Sin,B.Y+X*B.HalfX*B.Sin+Y*B.HalfY*B.Cos);
                    const double Z=TemperateBackdrop::CoreTriangleHeight(P.X,P.Y,Half,C.Seed,Hills->RiverPlan,C.Version,Village);
                    Proxy=FMath::Max(Proxy,FMath::Abs(Z-Village.Ground.Z));
                }
            }
            for(double Side:{-1.,1.})
            {
                const auto Door=Village.Mouth(Side);
                if(!Village.bSideLane || Side<0.)
                {
                    const auto Junction=Door-(Side<0.?Village.FeederLength:0.)*Village.Axis;
                    Mouth=FMath::Max(Mouth,FMath::Abs(Junction.Y-TemperateHillsSurface::ValleyY(Junction.X,C.Seed)));
                }
                FVector2D Prev=Door; double PrevZ=Village.Ground.Z;
                for(int32 J=1;J<=FMath::CeilToInt(FMath::Max(Village.Shoulder,Side<0.?Village.FeederLength:0.)/100.)+1;++J)
                {
                    const FVector2D P=Village.Approach(Side,J*100.,C.Seed);
                    const double Z=Hills->Height(P.X,P.Y);
                    Slope=FMath::Max(Slope,FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Z-PrevZ),(P-Prev).Size())));
                    Prev=P;PrevZ=Z;
                }
            }
        }
        if(Village.bPlaced)
        {
            TArray<double> Slopes;
            for(int32 Face=0;Face<4;++Face)for(int32 T=-4;T<=4;++T)
            {
                double Last=Village.Ground.Z;
                for(double D=100.;D<=Village.Shoulder;D+=100.)
                {
                    const double Side=(Face%2)?1.:-1.;
                    const auto P=(Face<2)?Village.World(Side*(4600.+D),T*800.):Village.World(T*1150.,Side*(3200.+D));
                    const double Z=Hills->Height(P.X,P.Y);
                    Slopes.Add(FMath::RadiansToDegrees(FMath::Atan(FMath::Abs(Z-Last)/100.)));Last=Z;
                }
            }
            Slopes.Sort(); P95=Slopes[FMath::FloorToInt((Slopes.Num()-1)*.95)];
        }
        const auto First=Village;
        const auto FirstChapel=Hills->ChapelSite;
        Hills->ChapelSite={}; Hills->VillageSite={};
        Hills->PlanAbandonedVillage(Natural);
        const bool Replay=First.bPlaced==Village.bPlaced && First.Ground==Village.Ground && First.Axis==Village.Axis && First.Shoulder==Village.Shoulder && First.FeederLength==Village.FeederLength && FirstChapel.Ground==Hills->ChapelSite.Ground;
        const auto Lot=Village.ChapelLot();
        const bool Joined=Hills->ChapelSite.bPlaced && Hills->ChapelSite.Ground.Equals(Lot.Ground,.01)
            && Hills->ChapelSite.Trail.Equals(Lot.Trail,.01) && Hills->ChapelSite.Axis.Equals(Village.Axis,1.e-6);
        if(!Village.bPlaced || !Joined || Pad>.01 || Mouth>1. || Wet || !Replay)++Errors;
        Rows+=FString::Printf(TEXT("%d,%d,%.0f,%d,%d,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.2f,%.3f,%d,%.2f,%d,%.2f,%d\n"),
            C.Seed,C.Version,C.Size,int32(I==0&&Save),int32(Village.bPlaced),Village.Ground.X/100.,Village.Ground.Y/100.,Village.Ground.Z/100.,
            (Village.Ground.X-Spawn.X)/100.,(Village.Ground.Y-Spawn.Y)/100.,Village.Shoulder/100.,Pad,Slope,Mouth,Wet,Proxy,int32(Village.bSideLane),P95,int32(Replay));
    }
    FString Output=FPaths::ProjectSavedDir()/TEXT("VillageSiteReview/seeds.csv");
    FParse::Value(*Params,TEXT("Output="),Output);
    if(!FFileHelper::SaveStringToFile(Rows,*Output))return 2;
    UE_LOG(LogTemp,Display,TEXT("VILLAGE_REVIEW cases=%d errors=%d output=%s"),Cases.Num(),Errors,*Output);
    return Errors?3:0;
}
