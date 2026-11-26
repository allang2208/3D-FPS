#include "TemperateWetForestCheckCommandlet.h"
#include "TemperateForestWater.h"
#include "TemperateForestHabitat.h"
#include "TemperateHillsWorld.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstance.h"
#include "MaterialShared.h"
#endif

int32 UTemperateWetForestCheckCommandlet::Main(const FString& Params)
{
    (void)TemperateEcology::Get();
    FString Output=FPaths::ProjectDir()/TEXT("SourceAssets/HillsWetForest20261111/Receipts/native-check.json");
    FParse::Value(*Params,TEXT("Output="),Output);
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases,Errors;
    auto Fail=[&](const FString& Text){Errors.Add(MakeShared<FJsonValueString>(Text));};
    TArray<int32> Seeds{122,7391,20261111};
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_World"),0));
    if(Save)Seeds.AddUnique(Save->Seed);
    for(const int32 Seed:Seeds)
    {
        const int32 Version=Save&&Save->Seed==Seed?Save->GeneratorVersion:2;
        TArray<TemperateHillsSurface::FTerrainEdit> Edits;
        if(Save&&Save->Seed==Seed)
        {
            for(const auto& R:Save->Edits)
            {TemperateHillsSurface::FTerrainEdit E;E.Type=R.Type;E.X=R.X;E.Y=R.Y;E.Radius=R.Radius;
                E.HalfX=R.HalfX;E.HalfY=R.HalfY;E.Amplitude=R.Amplitude;E.Lip=R.Lip;E.Seed=R.Seed;
                if(TemperateHillsSurface::TerrainEditValid(E))Edits.Add(E);}
            for(const auto& R:Save->Craters)
            {TemperateHillsSurface::FTerrainEdit E;E.X=R.X;E.Y=R.Y;E.Radius=R.Radius;E.Amplitude=-R.Depth;E.Lip=R.Rim;
                E.Seed=TemperateHillsSurface::Key(int32(R.X),int32(R.Y),uint32(Seed),7043);
                if(TemperateHillsSurface::TerrainEditValid(E))Edits.Add(E);}
        }
        double SX=-25600+173,SY=TemperateHillsSurface::ValleyY(SX,Seed),Best=DBL_MAX;
        if(Version>=2)for(int32 I=0;I<65;++I)
        {
            const double X=-25600+173+I*200.,Y=TemperateHillsSurface::ValleyY(X,Seed);
            const double S=1-TemperateHillsSurface::Normal(X,Y,Seed,Version).Z;
            if(S<Best){Best=S;SX=X;SY=Y;}if(S<=1-FMath::Cos(FMath::DegreesToRadians(8.)))break;
        }
        const auto River=TemperateRiver::Generate(Seed,51200,FVector2D(SX,SY),22,Version);
        const double Started=FPlatformTime::Seconds();
        const auto Plan=TemperateForestWater::Generate(Seed,51200,River,Edits,Version);
        const double Milliseconds=(FPlatformTime::Seconds()-Started)*1000;
        const auto Again=TemperateForestWater::Generate(Seed,51200,River,Edits,Version);
        auto Case=MakeShared<FJsonObject>();Case->SetNumberField(TEXT("seed"),Seed);Case->SetNumberField(TEXT("version"),Version);
        Case->SetBoolField(TEXT("user_save"),Save&&Save->Seed==Seed);Case->SetNumberField(TEXT("edits"),Edits.Num());
        Case->SetNumberField(TEXT("plan_ms"),Milliseconds);Case->SetNumberField(TEXT("pool_count"),Plan->Pools.Num());
        Case->SetNumberField(TEXT("shallow_basins"),Plan->Basins.Num());
        if(Plan->Pools.IsEmpty())Fail(FString::Printf(TEXT("No usable forest pool: seed %d"),Seed));
        const auto Unedited=TemperateForestWater::Generate(Seed,51200,River,{},Version);
        if(Unedited->Basins.Num()!=Plan->Basins.Num())Fail(TEXT("Edits moved basin sites"));
        for(int32 I=0;I<Plan->Basins.Num();++I)
        {
            const auto& B=Plan->Basins[I];
            if(!Unedited->Basins.IsValidIndex(I)||B.Center!=Unedited->Basins[I].Center)Fail(TEXT("Edits moved basin sites"));
            for(int32 Y=-8;Y<=8;++Y)for(int32 X=-8;X<=8;++X)
            {
                const FVector2D P=B.Center+FVector2D(X,Y)*B.Radius/6.;
                const double Z=River->Height(P.X,P.Y,Seed),Shaped=Plan->ShapeGround(P.X,P.Y,Z);
                if(Shaped>Z+.001||Z-Shaped>75.001)Fail(TEXT("Basin deformation outside limit"));
                if(!Plan->HasBasin(P.X,P.Y)&&Z!=Shaped)Fail(TEXT("Basin changed exterior terrain"));
                if(River->Sample(P.X,P.Y).Bank>.01&&Z!=Shaped)Fail(TEXT("Basin changed river terrain"));
            }
        }
        if(Plan->Pools.Num()>8||Plan->Pools.Num()!=Again->Pools.Num())Fail(TEXT("Pool budget/determinism"));
        TArray<TSharedPtr<FJsonValue>> Pools;int32 Tested=0;
        for(int32 I=0;I<Plan->Pools.Num();++I)
        {
            const auto& P=Plan->Pools[I];auto Pool=MakeShared<FJsonObject>();
            Pool->SetNumberField(TEXT("area_m2_estimate"),P.AreaM2);Pool->SetNumberField(TEXT("depth_cm"),P.MaxDepth);
            Pool->SetNumberField(TEXT("x"),P.Bounds.GetCenter().X);Pool->SetNumberField(TEXT("y"),P.Bounds.GetCenter().Y);Pool->SetNumberField(TEXT("water_z"),P.WaterZ);
            Pools.Add(MakeShared<FJsonValueObject>(Pool));
            if(P.WaterZ!=Again->Pools[I].WaterZ||P.Cells.Num()!=Again->Pools[I].Cells.Num())Fail(TEXT("Pool replay differs"));
            if(P.MaxDepth<10||P.MaxDepth>45.01)Fail(TEXT("Pool depth outside budget"));
            for(const auto Cell:P.Cells)
            {
                const double X=Plan->Origin.X+(Cell.X+.5)*TemperateForestWater::Step,Y=Plan->Origin.Y+(Cell.Y+.5)*TemperateForestWater::Step;
                const auto S=Plan->Sample(X,Y);if(!S.Wet)continue;++Tested;
                if(River->RainforestWeight(X,Y)<.4||River->Sample(X,Y).Bank>.02
                    ||FMath::Abs(Y-TemperateHillsSurface::ValleyY(X,Seed))<1600)Fail(TEXT("Water outside forest/dry-land boundary"));
                FVector Hit;
                if(!Plan->IntersectSegment(FVector(X,Y,S.WaterZ+100),FVector(X,Y,S.WaterZ-100),Hit)
                    ||FMath::Abs(Hit.Z-S.WaterZ)>.01)Fail(TEXT("Water render/contact mismatch"));
            }
        }
        UE::Geometry::FDynamicMesh3 Whole;Plan->BuildWaterMesh(-51200,-51200,102400,Whole);
        int32 TileTriangles=0;
        for(int32 Y=0;Y<16;++Y)for(int32 X=0;X<16;++X)
        {if(!Plan->IntersectsCell(-51200+X*6400,-51200+Y*6400,6400))continue;
            UE::Geometry::FDynamicMesh3 Tile;Plan->BuildWaterMesh(-51200+X*6400,-51200+Y*6400,6400,Tile);TileTriangles+=Tile.TriangleCount();}
        if(TileTriangles!=Whole.TriangleCount())Fail(TEXT("Water tile seam missing/duplicate triangles"));
        Case->SetNumberField(TEXT("triangles"),Whole.TriangleCount());Case->SetNumberField(TEXT("wet_samples_checked"),Tested);
        Case->SetArrayField(TEXT("pools"),Pools);Cases.Add(MakeShared<FJsonValueObject>(Case));
    }
    Report->SetArrayField(TEXT("cases"),Cases);Report->SetBoolField(TEXT("save_written"),false);
#if WITH_EDITOR
    TArray<TSharedPtr<FJsonValue>> Materials;
    if(FParse::Param(*Params,TEXT("CompileMaterials")))
    {
        const TCHAR* Paths[]={TEXT("/Game/WorldGeneration/TemperateHills/Grass/M_TemperateMeadow"),
            TEXT("/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround"),
            TEXT("/Game/WorldGeneration/TemperateHills/M_TemperateGround"),
            TEXT("/Game/Fluids/RiverPilot20260923/M_RiverPilot"),TEXT("/Game/WorldGeneration/TemperateHills/WetForest/M_ForestPond")};
        TArray<UMaterial*> Loaded;
        for(const auto Path:Paths)if(auto* M=LoadObject<UMaterial>(nullptr,Path)){Loaded.Add(M);M->AddToRoot();M->PostEditChange();}else Fail(FString(TEXT("Missing "))+Path);
        FAssetCompilingManager::Get().FinishAllCompilation();if(GShaderCompilingManager)GShaderCompilingManager->FinishAllCompilation();
        for(auto* M:Loaded)
        {
            const auto* R=M->GetMaterialResource(GMaxRHIShaderPlatform);
            if(!R||!R->GetGameThreadShaderMap()||!R->GetCompileErrors().IsEmpty())Fail(FString(TEXT("No valid shader map: "))+M->GetPathName());
            else Materials.Add(MakeShared<FJsonValueString>(M->GetPathName()));
            M->RemoveFromRoot();
        }
    }
    Report->SetArrayField(TEXT("compiled_materials"),Materials);
#endif
    Report->SetArrayField(TEXT("errors"),Errors);FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*Output);
    UE_LOG(LogTemp,Display,TEXT("WET_FOREST_CHECK cases=%d errors=%d output=%s"),Cases.Num(),Errors.Num(),*Output);
    return Errors.IsEmpty()?0:1;
}
