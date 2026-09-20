"""MCP programmatic entry: apply existing-function changes outside PIE."""

def is_playing():
    return execute_tool('EditorToolset.EditorAppToolset.IsPIERunning', '{}')['returnValue']

def stop_play():
    return execute_tool('EditorToolset.EditorAppToolset.StopPIE', '{}')

def compile_changes():
    return execute_tool('LiveCodingToolset.LiveCodingToolset.CompileLiveCoding', '{}')['returnValue']

def run():
    stopped = is_playing()
    if stopped:
        stop_play()
    result = compile_changes()
    if not result.startswith('Result: Success'):
        raise RuntimeError(result)
    return {'stopped_pie': stopped, 'compile': result}
