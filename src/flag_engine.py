"""Feature flags engine — zero dependencies.

Uses only Python stdlib (time, json, hashlib, collections).
Provides feature toggles, percentage rollout, A/B testing, user targeting.
"""
import time
import json
import hashlib
from collections import defaultdict
from typing import Any, Dict, List, Optional


class FeatureFlagEngine:
    """Feature flag operations with zero external dependencies."""

    @staticmethod
    def create_store() -> Dict:
        return {"flags": {}, "history": [], "total_evaluations": 0}

    @staticmethod
    def create_flag(store: Dict, name: str, enabled: bool = False, rollout: float = 100.0, description: str = "") -> Dict:
        if name in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' already exists"}
        store["flags"][name] = {
            "name": name, "enabled": enabled, "rollout": rollout,
            "description": description, "created": time.time(),
            "updated": time.time(), "targets": [], "variants": {},
            "evaluations": 0, "enabled_count": 0,
        }
        return {"success": True, "name": name, "enabled": enabled}

    @staticmethod
    def is_enabled(store: Dict, name: str, user_id: str = None) -> Dict:
        if name not in store["flags"]:
            return {"success": True, "enabled": False, "name": name, "reason": "not_found"}
        flag = store["flags"][name]
        store["total_evaluations"] += 1
        flag["evaluations"] += 1

        if not flag["enabled"]:
            return {"success": True, "enabled": False, "name": name, "reason": "flag_disabled"}

        if flag["targets"]:
            matched = False
            for target in flag["targets"]:
                if target.get("type") == "user" and user_id == target.get("value"):
                    matched = True
                    return {"success": True, "enabled": True, "name": name, "reason": "targeted"}
                if target.get("type") == "all":
                    matched = True
                    return {"success": True, "enabled": True, "name": name, "reason": "targeted_all"}
            if not matched:
                return {"success": True, "enabled": False, "name": name, "reason": "not_targeted"}

        if flag["rollout"] >= 100.0:
            flag["enabled_count"] += 1
            return {"success": True, "enabled": True, "name": name, "reason": "full_rollout"}

        if user_id:
            hash_val = int(hashlib.md5(f"{name}:{user_id}".encode()).hexdigest(), 16) % 100
            if hash_val < flag["rollout"]:
                flag["enabled_count"] += 1
                return {"success": True, "enabled": True, "name": name, "reason": "rollout", "hash": hash_val}
            return {"success": True, "enabled": False, "name": name, "reason": "rollout_excluded", "hash": hash_val}

        flag["enabled_count"] += 1
        return {"success": True, "enabled": True, "name": name, "reason": "no_user_id"}

    @staticmethod
    def enable(store: Dict, name: str) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        store["flags"][name]["enabled"] = True
        store["flags"][name]["updated"] = time.time()
        store["history"].append({"flag": name, "action": "enable", "timestamp": time.time()})
        return {"success": True, "name": name, "enabled": True}

    @staticmethod
    def disable(store: Dict, name: str) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        store["flags"][name]["enabled"] = False
        store["flags"][name]["updated"] = time.time()
        store["history"].append({"flag": name, "action": "disable", "timestamp": time.time()})
        return {"success": True, "name": name, "enabled": False}

    @staticmethod
    def toggle(store: Dict, name: str) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        new_state = not store["flags"][name]["enabled"]
        store["flags"][name]["enabled"] = new_state
        store["flags"][name]["updated"] = time.time()
        return {"success": True, "name": name, "enabled": new_state}

    @staticmethod
    def set_rollout(store: Dict, name: str, percentage: float) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        if not (0 <= percentage <= 100):
            return {"success": False, "error": "Percentage must be 0-100"}
        store["flags"][name]["rollout"] = percentage
        store["flags"][name]["updated"] = time.time()
        return {"success": True, "name": name, "rollout": percentage}

    @staticmethod
    def add_target(store: Dict, name: str, target_type: str, value: str) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        store["flags"][name]["targets"].append({"type": target_type, "value": value})
        return {"success": True, "name": name, "target": {"type": target_type, "value": value}}

    @staticmethod
    def remove_targets(store: Dict, name: str) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        count = len(store["flags"][name]["targets"])
        store["flags"][name]["targets"] = []
        return {"success": True, "name": name, "removed": count}

    @staticmethod
    def set_variants(store: Dict, name: str, variants: Dict) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        store["flags"][name]["variants"] = variants
        return {"success": True, "name": name, "variant_count": len(variants)}

    @staticmethod
    def get_variant(store: Dict, name: str, user_id: str = None) -> Dict:
        if name not in store["flags"]:
            return {"success": True, "variant": None, "name": name, "reason": "not_found"}
        flag = store["flags"][name]
        if not flag["enabled"]:
            return {"success": True, "variant": None, "name": name, "reason": "disabled"}
        variants = flag["variants"]
        if not variants:
            return {"success": True, "variant": None, "name": name, "reason": "no_variants"}
        keys = list(variants.keys())
        if user_id:
            idx = int(hashlib.md5(f"{name}:{user_id}".encode()).hexdigest(), 16) % len(keys)
        else:
            import random
            idx = random.randint(0, len(keys) - 1)
        selected = keys[idx]
        return {"success": True, "variant": selected, "value": variants[selected], "name": name}

    @staticmethod
    def get_flag(store: Dict, name: str) -> Dict:
        if name not in store["flags"]:
            return {"success": False, "error": f"Flag '{name}' not found"}
        return {"success": True, "flag": store["flags"][name]}

    @staticmethod
    def list_flags(store: Dict, enabled_only: bool = False) -> Dict:
        flags = store["flags"]
        if enabled_only:
            flags = {k: v for k, v in flags.items() if v["enabled"]}
        result = {k: {"enabled": v["enabled"], "rollout": v["rollout"], "evaluations": v["evaluations"]} for k, v in flags.items()}
        return {"success": True, "flags": result, "count": len(result)}

    @staticmethod
    def delete_flag(store: Dict, name: str) -> Dict:
        if name not in store["flags"]:
            return {"success": True, "name": name, "deleted": False}
        del store["flags"][name]
        return {"success": True, "name": name, "deleted": True}

    @staticmethod
    def get_history(store: Dict, limit: int = 20) -> Dict:
        events = store["history"][-limit:]
        return {"success": True, "events": events, "count": len(events), "total": len(store["history"])}

    @staticmethod
    def stats(store: Dict) -> Dict:
        flags = list(store["flags"].values())
        return {
            "success": True,
            "total_flags": len(flags),
            "enabled_flags": sum(1 for f in flags if f["enabled"]),
            "disabled_flags": sum(1 for f in flags if not f["enabled"]),
            "total_evaluations": store["total_evaluations"],
            "flags_with_targets": sum(1 for f in flags if f["targets"]),
            "flags_with_variants": sum(1 for f in flags if f["variants"]),
        }

    @staticmethod
    def reset(store: Dict) -> Dict:
        old = FeatureFlagEngine.stats(store)
        store["flags"] = {}
        store["history"] = []
        store["total_evaluations"] = 0
        return {"success": True, "reset": old}
