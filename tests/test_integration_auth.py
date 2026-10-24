import unittest

from onboardops.auth import AuthorizationError, require_integration_read, require_permission, resolve_actor


class IntegrationReadAuthorizationTests(unittest.TestCase):
    def test_demo_identity_cannot_perform_live_integration_lookups(self):
        actor = resolve_actor(environ={"ONBOARDOPS_AUTH_MODE": "demo"})
        with self.assertRaises(AuthorizationError):
            require_permission(actor, "integrations:read", production_only=True)

    def test_only_operator_and_admin_roles_can_read_live_integrations(self):
        env = {"ONBOARDOPS_AUTH_MODE": "trusted_proxy", "ONBOARDOPS_TRUSTED_AUTH_PROXY": "true"}
        for role in ("onboardops-admin", "onboardops-operator"):
            with self.subTest(role=role):
                actor = resolve_actor(
                    {"X-Auth-Request-User": "operator@example.invalid",
                     "X-Auth-Request-Groups": role},
                    environ=env,
                )
                require_permission(actor, "integrations:read", production_only=True)

        for role in ("onboardops-requester", "onboardops-approver", "onboardops-demo", "unknown"):
            with self.subTest(role=role):
                with self.assertRaises(AuthorizationError):
                    actor = resolve_actor(
                        {"X-Auth-Request-User": "reader@example.invalid",
                         "X-Auth-Request-Groups": role},
                        environ=env,
                    )
                    require_permission(actor, "integrations:read", production_only=True)


    def test_live_lookup_entry_point_re_resolves_and_enforces_permission(self):
        demo_env = {"ONBOARDOPS_AUTH_MODE": "demo"}
        with self.assertRaises(AuthorizationError):
            require_integration_read(environ=demo_env)

        proxy_env = {"ONBOARDOPS_AUTH_MODE": "trusted_proxy", "ONBOARDOPS_TRUSTED_AUTH_PROXY": "true"}
        actor = require_integration_read(
            {"X-Auth-Request-User": "operator@example.invalid",
             "X-Auth-Request-Groups": "onboardops-operator"},
            environ=proxy_env,
        )
        self.assertEqual(actor.subject, "operator@example.invalid")

if __name__ == "__main__":
    unittest.main()
