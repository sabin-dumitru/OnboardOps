"""Explicit role/permission matrix tests to prevent accidental privilege drift."""
import unittest

from onboardops.auth import Actor, AuthorizationError, require_permission


class AuthorizationMatrixTests(unittest.TestCase):
    def test_each_role_has_only_its_declared_permissions(self):
        expected = {
            "onboardops-admin": {"cases:read", "cases:create", "cases:transition",
                                 "approvals:review", "provider:write"},
            "onboardops-requester": {"cases:read", "cases:create"},
            "onboardops-approver": {"cases:read", "approvals:review"},
            "onboardops-operator": {"cases:read", "cases:transition", "provider:write"},
            "onboardops-demo": {"cases:read", "cases:create", "cases:transition"},
        }
        all_permissions = {"cases:read", "cases:create", "cases:transition",
                           "approvals:review", "provider:write", "cases:delete",
                           "admin:configure"}
        for role, allowed in expected.items():
            actor = Actor("test-user", frozenset({role}), "demo" if role == "onboardops-demo" else "trusted_proxy")
            for permission in all_permissions:
                with self.subTest(role=role, permission=permission):
                    if permission in allowed:
                        require_permission(actor, permission)
                    else:
                        with self.assertRaises(AuthorizationError):
                            require_permission(actor, permission)

    def test_unknown_role_cannot_inherit_any_permission(self):
        actor = Actor("test-user", frozenset({"onboardops-superuser", "unknown"}), "trusted_proxy")
        for permission in ("cases:read", "cases:create", "cases:transition",
                           "approvals:review", "provider:write", "admin:configure"):
            with self.subTest(permission=permission):
                with self.assertRaises(AuthorizationError):
                    require_permission(actor, permission)

    def test_production_only_actions_are_denied_to_demo_identity(self):
        actor = Actor("local-demo", frozenset({"onboardops-admin", "onboardops-demo"}), "demo")
        with self.assertRaises(AuthorizationError):
            require_permission(actor, "provider:write", production_only=True)


if __name__ == "__main__":
    unittest.main()
