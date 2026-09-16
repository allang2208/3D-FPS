"""Run Python inside the running Unreal Editor over the Python plugin's remote-execution socket.

Why: the MCP bridge is fine for individual tool calls, but every modeling step would cost a
process start plus HTTP round trips. Remote execution opens one long-lived channel and runs a
whole script in-editor, which is what multi-step work (build -> boolean -> UV -> bake ->
collision -> save) actually wants. Vibe3D's service is reachable from that script as
`unreal.ModelingService.<snake_case>(...)`.

Requires (project side): `Config/DefaultEngine.ini` ->
    [/Script/PythonScriptPlugin.PythonScriptPluginSettings]
    bRemoteExecution=True
and an editor restart so the socket binds. Default endpoints are local-only:
multicast 239.0.0.1:6766, command 127.0.0.1:6776.

Usage (plain CPython 3; the shipped client is pure standard library):
    python Tools/AssetPipeline/ue_python_exec.py --list
    python Tools/AssetPipeline/ue_python_exec.py --script path/to/script.py
    python Tools/AssetPipeline/ue_python_exec.py --statement "import unreal; print(unreal.SystemLibrary.get_engine_version())"
    python Tools/AssetPipeline/ue_python_exec.py --eval "1+1"

The script is executed with MODE_EXEC_FILE, so it may contain multiple statements and may read
`sys.argv` style arguments passed after the script path.
"""

import argparse
import importlib.util
import os
import sys
import time

DEFAULT_REMOTE_EXEC = (
    r"E:\Program Files (x86)\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin"
    r"\Content\Python\remote_execution.py"
)
DISCOVERY_TIMEOUT_SECONDS = 6.0


def load_client(path):
    spec = importlib.util.spec_from_file_location("ue_remote_execution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pick_node(nodes, wanted):
    if wanted:
        for node in nodes:
            if node.get("node_id") == wanted:
                return node
        return None
    if len(nodes) == 1:
        return nodes[0]
    # Several editors open: prefer the FPSGAME one, otherwise fail loudly.
    for node in nodes:
        project = str(node.get("project_name") or "")
        if "FPSGAME" in project.upper():
            return node
    return None


def main():
    parser = argparse.ArgumentParser(description="Execute Python in the running UE editor.")
    parser.add_argument("--remote-exec", default=os.environ.get("UE_REMOTE_EXECUTION_PY", DEFAULT_REMOTE_EXEC))
    parser.add_argument("--script", help="path to a .py file to execute in-editor")
    parser.add_argument("--statement", help="single Python statement to execute")
    parser.add_argument("--eval", dest="evaluate", help="Python expression to evaluate and print")
    parser.add_argument("--node", help="remote node id to connect to")
    parser.add_argument("--list", action="store_true", help="list discovered editor nodes and exit")
    parser.add_argument("--timeout", type=float, default=DISCOVERY_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if not os.path.exists(args.remote_exec):
        print("ERROR: remote_execution.py not found: %s" % args.remote_exec, file=sys.stderr)
        return 2

    client = load_client(args.remote_exec)
    remote = client.RemoteExecution()
    remote.start()
    try:
        deadline = time.time() + args.timeout
        nodes = []
        while time.time() < deadline:
            nodes = list(remote.remote_nodes)
            if nodes:
                break
            time.sleep(0.2)

        if not nodes:
            print(
                "ERROR: 没有发现可连接的编辑器节点。检查：编辑器是否在运行、"
                "bRemoteExecution 是否为 True、是否在改配置后重启过编辑器。",
                file=sys.stderr,
            )
            return 3

        if args.list:
            for node in nodes:
                print(
                    "{node_id}  engine={engine_version}  project={project_name}  endpoint={command_endpoint}".format(
                        node_id=node.get("node_id"),
                        engine_version=node.get("engine_version"),
                        project_name=node.get("project_name"),
                        command_endpoint=node.get("command_endpoint"),
                    )
                )
            return 0

        node = pick_node(nodes, args.node)
        if node is None:
            print("ERROR: 发现多个节点但无法唯一确定，请用 --node 指定。可用节点：", file=sys.stderr)
            for candidate in nodes:
                print("  %s (%s)" % (candidate.get("node_id"), candidate.get("project_name")), file=sys.stderr)
            return 4

        remote.open_command_connection(node["node_id"])
        if args.script:
            command = os.path.abspath(args.script)
            mode = client.MODE_EXEC_FILE
        elif args.statement:
            command = args.statement
            mode = client.MODE_EXEC_STATEMENT
        elif args.evaluate:
            command = args.evaluate
            mode = client.MODE_EVAL_STATEMENT
        else:
            parser.error("需要 --script / --statement / --eval 之一（或用 --list）")

        result = remote.run_command(command, exec_mode=mode)
        success = result.get("success") if isinstance(result, dict) else None
        output = result.get("output") if isinstance(result, dict) else result
        print("[node] %s  success=%s" % (node.get("node_id"), success))
        if output:
            print(output)
        remote.close_command_connection()
        return 0 if success in (True, None) else 1
    finally:
        remote.stop()


if __name__ == "__main__":
    sys.exit(main())
