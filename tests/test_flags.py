"""Tests for MCP Feature Flags Tools — toggles, rollout, A/B, targeting."""
import json, pytest, os, sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.server import MCPFeatureFlagsToolsServer, TOOL_DEFS
from src.flag_engine import FeatureFlagEngine

class TestToolDefs:
    def test_names(self):
        for t in TOOL_DEFS: assert "name" in t and len(t["name"])>0
    def test_descs(self):
        for t in TOOL_DEFS: assert "description" in t and len(t["description"])>10
    def test_schema(self):
        for t in TOOL_DEFS: assert "inputSchema" in t and t["inputSchema"]["type"]=="object"
    def test_count(self):
        assert len(TOOL_DEFS)==16
    def test_required(self):
        names={t["name"] for t in TOOL_DEFS}
        expected={"create_flag","is_enabled","enable","disable","toggle","set_rollout","add_target","remove_targets","set_variants","get_variant","get_flag","list_flags","delete_flag","get_history","stats","reset"}
        assert names==expected

class TestManifest:
    def test_manifest(self):
        s=MCPFeatureFlagsToolsServer();m=s.manifest()
        assert m["server"]["name"]=="mcp-feature-flags-tools"
        assert len(m["tools"])==16

class TestCreateEnable:
    def test_create(self):
        s=FeatureFlagEngine.create_store()
        r=FeatureFlagEngine.create_flag(s,"new_ui")
        assert r["success"] is True
    def test_duplicate(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1")
        r=FeatureFlagEngine.create_flag(s,"f1")
        assert r["success"] is False
    def test_enable_disable(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1")
        FeatureFlagEngine.enable(s,"f1")
        assert FeatureFlagEngine.is_enabled(s,"f1")["enabled"] is True
        FeatureFlagEngine.disable(s,"f1")
        assert FeatureFlagEngine.is_enabled(s,"f1")["enabled"] is False
    def test_toggle(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True)
        r=FeatureFlagEngine.toggle(s,"f1")
        assert r["enabled"] is False
        r=FeatureFlagEngine.toggle(s,"f1")
        assert r["enabled"] is True

class TestRollout:
    def test_full_rollout(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True,rollout=100)
        r=FeatureFlagEngine.is_enabled(s,"f1","user1")
        assert r["enabled"] is True
    def test_zero_rollout(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True,rollout=0)
        r=FeatureFlagEngine.is_enabled(s,"f1","user1")
        assert r["enabled"] is False
    def test_partial_consistency(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True,rollout=50)
        r1=FeatureFlagEngine.is_enabled(s,"f1","user1")
        r2=FeatureFlagEngine.is_enabled(s,"f1","user1")
        assert r1["enabled"]==r2["enabled"]  # Same user always gets same result
    def test_set_rollout(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1")
        r=FeatureFlagEngine.set_rollout(s,"f1",25)
        assert r["rollout"]==25
    def test_invalid_rollout(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1")
        r=FeatureFlagEngine.set_rollout(s,"f1",150)
        assert r["success"] is False

class TestTargeting:
    def test_user_target(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True)
        FeatureFlagEngine.add_target(s,"f1","user","alice")
        assert FeatureFlagEngine.is_enabled(s,"f1","alice")["enabled"] is True
        assert FeatureFlagEngine.is_enabled(s,"f1","bob")["enabled"] is False
    def test_all_target(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True,rollout=0)
        FeatureFlagEngine.add_target(s,"f1","all","")
        assert FeatureFlagEngine.is_enabled(s,"f1","anyone")["enabled"] is True
    def test_remove_targets(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True)
        FeatureFlagEngine.add_target(s,"f1","user","alice")
        r=FeatureFlagEngine.remove_targets(s,"f1")
        assert r["removed"]==1

class TestVariants:
    def test_set_get(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True)
        FeatureFlagEngine.set_variants(s,"f1",{"A":"red","B":"blue"})
        r=FeatureFlagEngine.get_variant(s,"f1","user1")
        assert r["variant"] in ["A","B"]
    def test_consistent(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True)
        FeatureFlagEngine.set_variants(s,"f1",{"A":"red","B":"blue"})
        r1=FeatureFlagEngine.get_variant(s,"f1","user1")
        r2=FeatureFlagEngine.get_variant(s,"f1","user1")
        assert r1["variant"]==r2["variant"]
    def test_no_variants(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",enabled=True)
        r=FeatureFlagEngine.get_variant(s,"f1","user1")
        assert r["variant"] is None

class TestListGet:
    def test_list(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"a")
        FeatureFlagEngine.create_flag(s,"b",enabled=True)
        r=FeatureFlagEngine.list_flags(s)
        assert r["count"]==2
    def test_list_enabled(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"a")
        FeatureFlagEngine.create_flag(s,"b",enabled=True)
        r=FeatureFlagEngine.list_flags(s,enabled_only=True)
        assert r["count"]==1
    def test_get_flag(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1",description="test")
        r=FeatureFlagEngine.get_flag(s,"f1")
        assert r["success"] is True
    def test_delete(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1")
        r=FeatureFlagEngine.delete_flag(s,"f1")
        assert r["deleted"] is True

class TestHistory:
    def test_basic(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"f1")
        FeatureFlagEngine.enable(s,"f1")
        FeatureFlagEngine.disable(s,"f1")
        r=FeatureFlagEngine.get_history(s)
        assert r["count"]==2

class TestStatsReset:
    def test_stats(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"a",enabled=True)
        FeatureFlagEngine.create_flag(s,"b")
        FeatureFlagEngine.is_enabled(s,"a","user1")
        r=FeatureFlagEngine.stats(s)
        assert r["total_flags"]==2
        assert r["enabled_flags"]==1
        assert r["total_evaluations"]==1
    def test_reset(self):
        s=FeatureFlagEngine.create_store()
        FeatureFlagEngine.create_flag(s,"a")
        r=FeatureFlagEngine.reset(s)
        assert r["reset"]["total_flags"]==1
        assert FeatureFlagEngine.stats(s)["total_flags"]==0

class TestDispatch:
    def test_unknown(self):
        s=MCPFeatureFlagsToolsServer();assert "error" in json.loads(s.handle_tool_call("nope",{}))
    def test_missing(self):
        s=MCPFeatureFlagsToolsServer();assert "error" in json.loads(s.handle_tool_call("create_flag",{}))
    def test_create_dispatch(self):
        s=MCPFeatureFlagsToolsServer()
        r=json.loads(s.handle_tool_call("create_flag",{"name":"test"}))
        assert r["success"] is True

class TestSTDIO:
    def test_manifest_flag(self,capsys):
        from src.server import main
        with patch("sys.argv",["server","--manifest"]):main()
        parsed=json.loads(capsys.readouterr().out.strip())
        assert parsed["server"]["name"]=="mcp-feature-flags-tools"
