#include "DragonFluidInspectCommandlet.h"
#include "AssetCompilingManager.h"
#include "Engine/World.h"
#include "Engine/TextureRenderTargetVolume.h"
#include "FXSystem.h"
#include "Misc/FileHelper.h"
#include "NiagaraComponent.h"
#include "NiagaraComputeExecutionContext.h"
#include "NiagaraDataInterfaceRenderTargetVolume.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "NiagaraSimCache.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraEmitter.h"
#include "NiagaraSimulationStageBase.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraSystemInstanceController.h"
#include "NiagaraWorldManager.h"
#include "NiagaraScript.h"
#include "PreviewScene.h"
#include "SceneInterface.h"
#include "RenderingThread.h"
#include "RHIGPUReadback.h"
#include "TextureResource.h"
#include "Serialization/JsonSerializer.h"

namespace
{
TSharedRef<FJsonObject> DragonReadStore(const FNiagaraParameterStore& Store)
{
    auto Result=MakeShared<FJsonObject>();TArray<FNiagaraVariable> Vars;Store.GetParameters(Vars);
    for(const auto& Var:Vars)
    {
        const auto* Struct=Var.GetType().GetScriptStruct();
        const uint8* Data=Store.GetParameterData(Var);
        if(!Struct||!Data||Var.IsDataInterface()||Var.IsUObject())continue;
        FString Value;Struct->ExportText(Value,Data,nullptr,nullptr,PPF_None,nullptr);
        Result->SetStringField(Var.GetName().ToString(),Value);
    }
    return Result;
}
}

int32 UDragonFluidInspectCommandlet::Main(const FString& Params)
{
    auto* System=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume.NS_DragonVolume"));
    if(!System)return 1;
    System->RequestCompile(false);System->WaitForCompilationComplete(true,false);
    FAssetCompilingManager::Get().FinishAllCompilation();
    const FString Out=TEXT("D:/FPS3D/FPSGAME/Saved/DragonBreathVolumeV8_20261014/direction-frames");
    IFileManager::Get().MakeDirectory(*Out,true);
    FString StageText;
    for(const auto& Handle:System->GetEmitterHandles())
        if(const auto* Data=Handle.GetInstance().GetEmitterData())
            for(auto* Stage:Data->GetSimulationStages())
            {
                StageText+=Stage->GetName()+TEXT("\n");
                for(TFieldIterator<FProperty> P(Stage->GetClass());P;++P)
                    if(P->GetName().Contains(TEXT("Enabled"))||P->GetName().Contains(TEXT("Iteration"))||P->GetName().Contains(TEXT("DataInterface"))||P->GetName().Contains(TEXT("SimulationStageName")))
                    {FString V;P->ExportText_InContainer(0,V,Stage,nullptr,Stage,PPF_None);StageText+=P->GetName()+TEXT("=")+V+TEXT("\n");}
            }
    FFileHelper::SaveStringToFile(StageText,*FPaths::Combine(Out,TEXT("stage-bindings.txt")));
    FFileHelper::SaveStringToFile(System->GetSystemSpawnScript()->GetVMExecutableData().LastHlslTranslation,*FPaths::Combine(Out,TEXT("system-spawn.hlsl")));
    FFileHelper::SaveStringToFile(System->GetSystemUpdateScript()->GetVMExecutableData().LastHlslTranslation,*FPaths::Combine(Out,TEXT("system-update.hlsl")));
    FPreviewScene Scene(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false));
    auto* World=Scene.GetWorld();
    if(!World->FXSystem)World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    World->Scene->SetFXSystem(World->FXSystem.Get());
    for(float Yaw:{0.f,90.f,180.f})
    {
        const FVector Origin(6000,-4500,180);const FQuat Q=FRotator(0,Yaw,0).Quaternion();
        auto* FX=NewObject<UNiagaraComponent>();FX->AddToRoot();FX->SetAutoActivate(false);FX->SetAsset(System);
        FX->SetForceSolo(true);FX->SetAllowScalability(false);
        Scene.AddComponent(FX,FTransform(Q,Origin+Q.GetForwardVector()*230));
        FX->SetVariablePosition(TEXT("User.Origin"),Origin);
        FX->SetVariableVec3(TEXT("User.Forward"),Q.GetForwardVector());FX->SetVariableVec3(TEXT("User.Side"),Q.GetRightVector());FX->SetVariableVec3(TEXT("User.Up"),Q.GetUpVector());
        FX->SetVariableVec3(TEXT("User.WorldSpaceSize"),FVector(760,935,525));
        FX->SetVariableInt(TEXT("User.ResolutionMaxAxis"),128);FX->SetVariableFloat(TEXT("User.CellSize"),935.f/128);
        FX->SetVariableFloat(TEXT("User.Range"),500);FX->SetVariableFloat(TEXT("User.HalfAngle"),PI/4);
        FX->SetVariableFloat(TEXT("User.Strength"),1);FX->SetVariableFloat(TEXT("User.EmissionScale"),1);
        for(int32 I=0;I<9;++I)FX->SetVariableFloat(*FString::Printf(TEXT("User.Ray%d"),I),500);
        FX->SetSystemFixedBounds(FBox(-FVector(444,531.5,326.5),FVector(444,531.5,326.5)));
        FX->Activate(true);FX->AdvanceSimulation(4,1.f/60);
        FNiagaraWorldManager::Get(World)->FlushComputeAndDeferredQueues(true);
        if(FParse::Param(*Params,TEXT("GpuSamples")))
            for(int32 Frame=0;Frame<36;++Frame)
            {
                ++GFrameCounter;FX->AdvanceSimulation(1,1.f/60);
                FNiagaraWorldManager::Get(World)->FlushComputeAndDeferredQueues(true);
                World->SendAllEndOfFrameUpdates();
                if(auto* Dispatch=FNiagaraGpuComputeDispatchInterface::Get(World))Dispatch->FlushAndWait_GameThread();
            }
        auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("yaw"),Yaw);R->SetStringField(TEXT("component"),FX->GetComponentTransform().ToString());
        if(auto C=FX->GetSystemInstanceController())
        {
            const auto& Emitters=C->GetSystemInstance_Unsafe()->GetEmitters();
            for(int32 I=0;I<Emitters.Num();++I)
            {
                auto E=MakeShared<FJsonObject>();E->SetNumberField(TEXT("state"),int32(Emitters[I]->GetExecutionState()));
                E->SetObjectField(TEXT("renderer"),DragonReadStore(Emitters[I]->GetRendererBoundVariables()));
                if(auto* GPU=Emitters[I]->GetGPUContext())
                {
                    E->SetObjectField(TEXT("gpu"),DragonReadStore(GPU->CombinedParamStore));
                    if(FParse::Param(*Params,TEXT("GpuSamples")))
                        for(auto* DI:GPU->GetDataInterfaces())
                            if(auto* Volume=Cast<UNiagaraDataInterfaceRenderTargetVolume>(DI))
                            {
                                auto* VD=static_cast<FRenderTargetVolumeRWInstanceData_GameThread*>(C->GetSystemInstance_Unsafe()->FindDataInterfaceInstanceData(Volume));
                                if(!VD||!VD->TargetTexture)continue;
                                auto* Resource=VD->TargetTexture->GameThread_GetRenderTargetResource();
                                FRHITexture* Texture=Resource?Resource->GetRenderTargetTexture():nullptr;if(!Texture)continue;
                                TArray<FFloat16Color> Voxels;const FIntVector Size=VD->Size;
                                ENQUEUE_RENDER_COMMAND(ReadDragonGas)([Texture,Size,&Voxels](FRHICommandListImmediate& Cmd)
                                {
                                    const auto Format=Texture->GetFormat();
                                    const int32 PixelBytes=GPixelFormats[Format].BlockBytes;
                                    FRHIGPUTextureReadback Readback(TEXT("DragonGasDiagnosis"));
                                    Readback.EnqueueCopy(Cmd,Texture,FIntVector::ZeroValue,0,Size);
                                    Cmd.SubmitAndBlockUntilGPUIdle(true);
                                    int32 Pitch=0,Height=0;const auto* Bytes=static_cast<const uint8*>(Readback.Lock(Pitch,&Height));
                                    if(Bytes)
                                    {
                                        Voxels.SetNumUninitialized(Size.X*Size.Y*Size.Z);
                                        for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
                                        {
                                            const uint8* P=Bytes+((Z*Height+Y)*Pitch+X)*PixelBytes;
                                            FLinearColor V(0,0,0,0);
                                            if(Format==PF_A32B32G32R32F)V=*reinterpret_cast<const FLinearColor*>(P);
                                            else if(Format==PF_FloatRGBA)V=reinterpret_cast<const FFloat16Color*>(P)->GetFloats();
                                            else if(Format==PF_G32R32F){V.R=reinterpret_cast<const float*>(P)[0];V.G=reinterpret_cast<const float*>(P)[1];}
                                            else if(Format==PF_R32_FLOAT)V.R=*reinterpret_cast<const float*>(P);
                                            else if(Format==PF_G16R16F){V.R=reinterpret_cast<const FFloat16*>(P)[0];V.G=reinterpret_cast<const FFloat16*>(P)[1];}
                                            Voxels[(Z*Size.Y+Y)*Size.X+X]=FFloat16Color(V);
                                        }
                                    }
                                    Readback.Unlock();
                                });
                                FlushRenderingCommands();
                                double MaxR=0,MaxG=0,Total=0,WeightedX=0;int32 Hot=0;
                                for(int32 N=0;N<Voxels.Num();++N)
                                {auto V=Voxels[N].GetFloats();MaxR=FMath::Max(MaxR,double(V.R));MaxG=FMath::Max(MaxG,double(V.G));if(V.G>.1f)++Hot;Total+=V.G;WeightedX+=V.G*(N%Size.X);}
                                auto Read=MakeShared<FJsonObject>();Read->SetStringField(TEXT("size"),Size.ToString());Read->SetNumberField(TEXT("max_density"),MaxR);Read->SetNumberField(TEXT("max_temperature"),MaxG);Read->SetNumberField(TEXT("hot_voxels"),Hot);Read->SetNumberField(TEXT("heat_unit_x"),Total>0?WeightedX/Total/Size.X:-1);
                                Read->SetNumberField(TEXT("voxel_count"),Voxels.Num());
                                Read->SetStringField(TEXT("format"),GPixelFormats[Texture->GetFormat()].Name);
                                E->SetObjectField(Volume->GetName(),Read);
                            }
                }
                R->SetObjectField(System->GetEmitterHandles()[I].GetName().ToString(),E);
            }
        }
        if(FParse::Param(*Params,TEXT("GpuSamples")))
        {
            auto* Cache=NewObject<UNiagaraSimCache>();Cache->AddToRoot();
            if(Cache->BeginWrite(FNiagaraSimCacheCreateParameters::CreateForDebugging(),FX)&&Cache->WriteFrame(FX)&&Cache->EndWrite())
            {
                TArray<FVector> Positions,Directions;TArray<float> Temps;
                Cache->ReadPositionAttribute(Positions,TEXT("Position"),TEXT("ParticleSourceEmitter"));
                Cache->ReadVectorAttribute(Directions,TEXT("JetDirection"),TEXT("ParticleSourceEmitter"));
                Cache->ReadFloatAttribute(Temps,TEXT("fluids_source_temperature"),TEXT("ParticleSourceEmitter"));
                R->SetNumberField(TEXT("source_particles"),Positions.Num());
                if(Positions.Num())R->SetStringField(TEXT("source_first_position"),Positions[0].ToString());
                if(Directions.Num())R->SetStringField(TEXT("source_first_direction"),Directions[0].ToString());
                if(Temps.Num())R->SetNumberField(TEXT("source_first_temperature"),Temps[0]);
                float MaxTemp=0;for(float T:Temps)MaxTemp=FMath::Max(MaxTemp,T);
                R->SetNumberField(TEXT("source_max_temperature"),MaxTemp);
            }
            Cache->RemoveFromRoot();
        }
        FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*FPaths::Combine(Out,FString::Printf(TEXT("yaw-%.0f.json"),Yaw)));
        FX->DeactivateImmediate();FX->RemoveFromRoot();Scene.RemoveComponent(FX);FX->DestroyComponent();FlushRenderingCommands();
        UE_LOG(LogTemp,Display,TEXT("DRAGON_FLUID_FRAME_READ yaw=%.0f"),Yaw);
    }
    return 0;
}
