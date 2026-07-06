"""MCP Server for feature flags — toggles, rollout, A/B testing, targeting."""
import json, sys, argparse
from typing import Any, Dict, List, Optional
from .flag_engine import FeatureFlagEngine

_store = FeatureFlagEngine.create_store()

TOOL_DEFS = [
    {"name":"create_flag","description":"Create a feature flag.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"enabled":{"type":"boolean","default":False},"rollout":{"type":"number","default":100},"description":{"type":"string","default":""}},"required":["name"]}},
    {"name":"is_enabled","description":"Check if a flag is enabled for a user.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"user_id":{"type":"string"}},"required":["name"]}},
    {"name":"enable","description":"Enable a flag.","inputSchema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"disable","description":"Disable a flag.","inputSchema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"toggle","description":"Toggle a flag.","inputSchema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"set_rollout","description":"Set rollout percentage (0-100).","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"percentage":{"type":"number"}},"required":["name","percentage"]}},
    {"name":"add_target","description":"Add a target (user or all).","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"target_type":{"type":"string"},"value":{"type":"string"}},"required":["name","target_type","value"]}},
    {"name":"remove_targets","description":"Remove all targets from a flag.","inputSchema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"set_variants","description":"Set A/B test variants.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"variants":{"type":"object"}},"required":["name","variants"]}},
    {"name":"get_variant","description":"Get A/B test variant for a user.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"user_id":{"type":"string"}},"required":["name"]}},
    {"name":"get_flag","description":"Get flag details.","inputSchema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"list_flags","description":"List all flags.","inputSchema":{"type":"object","properties":{"enabled_only":{"type":"boolean","default":False}},"required":[]}},
    {"name":"delete_flag","description":"Delete a flag.","inputSchema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"get_history","description":"Get flag change history.","inputSchema":{"type":"object","properties":{"limit":{"type":"integer","default":20}},"required":[]}},
    {"name":"stats","description":"Get flag statistics.","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"reset","description":"Reset all flags.","inputSchema":{"type":"object","properties":{},"required":[]}},
]

class MCPFeatureFlagsToolsServer:
    def __init__(self,name="mcp-feature-flags-tools",version="1.0.0"):
        self.name=name;self.version=version
    def list_tools(self):return TOOL_DEFS
    def manifest(self):return{"server":{"name":self.name,"version":self.version},"capabilities":{"tools":{"listChanged":False},"resources":{},"prompts":{}},"tools":self.list_tools()}
    def handle_tool_call(self,name,args):
        try:
            if name=="create_flag":return json.dumps(FeatureFlagEngine.create_flag(_store,args["name"],args.get("enabled",False),args.get("rollout",100),args.get("description","")))
            elif name=="is_enabled":return json.dumps(FeatureFlagEngine.is_enabled(_store,args["name"],args.get("user_id")))
            elif name=="enable":return json.dumps(FeatureFlagEngine.enable(_store,args["name"]))
            elif name=="disable":return json.dumps(FeatureFlagEngine.disable(_store,args["name"]))
            elif name=="toggle":return json.dumps(FeatureFlagEngine.toggle(_store,args["name"]))
            elif name=="set_rollout":return json.dumps(FeatureFlagEngine.set_rollout(_store,args["name"],args["percentage"]))
            elif name=="add_target":return json.dumps(FeatureFlagEngine.add_target(_store,args["name"],args["target_type"],args["value"]))
            elif name=="remove_targets":return json.dumps(FeatureFlagEngine.remove_targets(_store,args["name"]))
            elif name=="set_variants":return json.dumps(FeatureFlagEngine.set_variants(_store,args["name"],args["variants"]))
            elif name=="get_variant":return json.dumps(FeatureFlagEngine.get_variant(_store,args["name"],args.get("user_id")))
            elif name=="get_flag":return json.dumps(FeatureFlagEngine.get_flag(_store,args["name"]))
            elif name=="list_flags":return json.dumps(FeatureFlagEngine.list_flags(_store,args.get("enabled_only",False)))
            elif name=="delete_flag":return json.dumps(FeatureFlagEngine.delete_flag(_store,args["name"]))
            elif name=="get_history":return json.dumps(FeatureFlagEngine.get_history(_store,args.get("limit",20)))
            elif name=="stats":return json.dumps(FeatureFlagEngine.stats(_store))
            elif name=="reset":return json.dumps(FeatureFlagEngine.reset(_store))
            else:return json.dumps({"error":f"Unknown tool: {name}"})
        except KeyError as e:return json.dumps({"error":f"Missing required parameter: {e}","tool":name})
        except Exception as e:return json.dumps({"error":str(e),"tool":name})

def _run_stdio():
    server=MCPFeatureFlagsToolsServer()
    for line in sys.stdin:
        line=line.strip()
        if not line:continue
        try:request=json.loads(line)
        except json.JSONDecodeError:print(json.dumps({"jsonrpc":"2.0","error":{"code":-32700,"message":"Parse error"}}),flush=True);continue
        method=request.get("method","");req_id=request.get("id");params=request.get("params",{})
        if method=="initialize":response={"jsonrpc":"2.0","id":req_id,"result":{"server":server.name,"version":server.version}}
        elif method=="tools/list":response={"jsonrpc":"2.0","id":req_id,"result":{"tools":server.list_tools()}}
        elif method=="tools/call":
            result=server.handle_tool_call(params.get("name",""),params.get("arguments",{}))
            response={"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":result}]}}
        elif method=="shutdown":response={"jsonrpc":"2.0","id":req_id,"result":{}};print(json.dumps(response),flush=True);break
        else:response={"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":f"Method not found: {method}"}}
        print(json.dumps(response),flush=True)

def main():
    parser=argparse.ArgumentParser(description="MCP Feature Flags Tools Server")
    parser.add_argument("--stdio",action="store_true")
    parser.add_argument("--manifest",action="store_true")
    args=parser.parse_args()
    if args.manifest:print(json.dumps(MCPFeatureFlagsToolsServer().manifest(),indent=2))
    elif args.stdio:_run_stdio()
    else:parser.print_help()

if __name__=="__main__":main()
