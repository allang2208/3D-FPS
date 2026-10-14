import unreal as u
for obj in [u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate,
            u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache,
            u.NiagaraSimCache.read_position_attribute,u.NiagaraSimCache.read_color_attribute,
            u.NiagaraFunctionLibrary.spawn_system_at_location]:
    print(obj.__doc__)
