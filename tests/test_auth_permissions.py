import unittest
from onboardops.auth import Actor, AuthorizationError, require_permission, resolve_actor


class PermissionMatrixTests(unittest.TestCase):
    def test_role_permission_matrix_is_least_privilege(self):
        cases = [
            ("onboardops-requester", {"cases:read", "cases:create"}),
            ("onboardops-approver", {"cases:read", "approvals:review"}),
            ("onboardops-operator", {"cases:read", "cases:transition", "provider:write"}),
            ("onboardops-admin", {"cases:read", "cases:create", "cases:transition", "approvals:review", "provider:write"}),
        ]
        permissions = {"cases:read", "cases:create", "cases:transition", "approvals:review", "provider:write"}
        for role, allowed in cases:
            actor = Actor("test-user", frozenset({role}), "trusted_proxy")
            for permission in permissions:
                with self.subTest(role=role, permission=permission):
                    if permission in allowed:
                        require_permission(actor, permission)
                    else:
                        with self.assertRaises(AuthorizationError):
                            require_permission(actor, permission)

    def test_demo_provider_write_is_denied_even_if_role_has_permission(self):
        actor = Actor("local-demo", frozenset({"onboardops-admin"}), "demo")
        with self.assertRaises(AuthorizationError):
            require_permission(actor, "provider:write", production_only=True)

    def test_malformed_subject_and_unknown_roles_fail_closed(self):
        env = {"ONBOARDOPS_AUTH_MODE": "trusted_proxy", "ONBOARDOPS_TRUSTED_AUTH_PROXY": "true"}
        for subject in ("", "alice name", "x" * 129, "alice/../root"):
            with self.subTest(subject=subject):
                with self.assertRaises(AuthorizationError):
                    resolve_actor({"X-Auth-Request-User": subject, "X-Auth-Request-Groups": "onboardops-requester"}, environ=env)
        with self.assertRaises(AuthorizationError):
            resolve_actor({"X-Auth-Request-User": "alice", "X-Auth-Request-Groups": "unknown-role"}, environ=env)

    def test_proxy_roles_are_case_sensitive_and_proxy_must_be_trusted(self):
        env = {"ONBOARDOPS_AUTH_MODE": "trusted_proxy", "ONBOARDOPS_TRUSTED_AUTH_PROXY": "true"}
        with self.assertRaises(AuthorizationError):
            resolve_actor({"X-Auth-Request-User": "alice", "X-Auth-Request-Groups": "ONBOARDOPS-ADMIN"}, environ=env)
        with self.assertRaises(AuthorizationError):
            resolve_actor({"X-Auth-Request-User": "alice", "X-Auth-Request-Groups": "onboardops-admin"},
                          environ={"ONBOARDOPS_AUTH_MODE": "trusted_proxy", "ONBOARDOPS_TRUSTED_AUTH_PROXY": "false"})


if __name__ == "__main__":
    unittest.main()
