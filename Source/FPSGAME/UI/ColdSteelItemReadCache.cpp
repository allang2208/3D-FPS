#include "ColdSteelItemReadCache.h"
#include "Serialization/JsonSerializer.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

TSharedPtr<const FJsonObject> ColdSteelItemData::Read(const FString& Json)
{
    static thread_local FColdSteelJsonReadCache Cache;
    return Cache.Get(Json,[&]() -> TSharedPtr<const FJsonObject>
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelItemData_ParseMiss);
        TSharedPtr<FJsonObject> Object;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Object);
        return Object;
    });
}
