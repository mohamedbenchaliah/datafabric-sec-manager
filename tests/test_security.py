import os
import time

import pytest
from flask import g, url_for

from sec_manager.security import AirflowFabricSecurityManager

from .conftest import AUDIENCE


@pytest.mark.usefixtures("client_class", "run_in_transaction")
class TestAstroSecurityManagerMixin:
    def test_no_auth(self, appbuilder):
        resp = self.client.get(appbuilder.get_url_for_userinfo)
        assert resp.status_code == 403

    def test_invalid_jwt(self, appbuilder, invalid_jwt):
        resp = self.client.get(appbuilder.get_url_for_userinfo, headers=[("Authorization", "Bearer " + invalid_jwt)])
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        "claims",
        [
            {"made_up_claim": "admin"},
            {"email": None, "roles": None},
            {"email": None, "roles": None, "sub": None, "full_name": None, "aud": AUDIENCE},
            {"email": None, "roles": None, "sub": None, "full_name": None, "aud": AUDIENCE},
            {
                "email": "airflow@datafabric.com",
                "roles": None,
                "sub": "airflow@datafabric.com",
                "full_name": None,
                "aud": AUDIENCE,
            },
            {
                "email": "airflow@datafabric.com",
                "sub": "airflow@datafabric.com",
                "full_name": None,
                "roles": "NotAList",
                "aud": AUDIENCE,
            },
        ],
    )
    def test_signed_jwt_invalid_claims(self, appbuilder, signed_jwt, claims):
        jwt = signed_jwt(claims)
        resp = self.client.get(url_for("home"), headers=[("Authorization", "Bearer " + jwt)])
        assert resp.status_code == 403

    def test_signed_jwt_valid_claims_new_user(self, appbuilder, signed_jwt, valid_claims):
        jwt = signed_jwt(valid_claims)
        resp = self.client.get(url_for("home"), headers=[("Authorization", "Bearer " + jwt)])
        assert resp.status_code == 200
        assert g.user.is_anonymous is False
        assert ["Op"] == [r.name for r in g.user.roles]

        assert appbuilder.sm.find_user(username=valid_claims["sub"]) == g.user

        # Ensure that we actually wrote to the DB
        appbuilder.session.refresh(g.user)

    def test_signed_jwt_valid_claims_existing_user(self, appbuilder, user, signed_jwt, valid_claims, mocker):
        # Testing of role behaviour is checked via test_manage_user_roles
        mocker.patch.object(appbuilder.sm, "manage_user_roles")

        valid_claims["full_name"] = "Air Flow"
        valid_claims["sub"] = user.username

        jwt = signed_jwt(valid_claims)
        resp = self.client.get(url_for("home"), headers=[("Authorization", "Bearer " + jwt)])
        assert resp.status_code == 200
        assert g.user.is_anonymous is False
        appbuilder.sm.manage_user_roles.assert_called_with(mocker.ANY, valid_claims["roles"])

        appbuilder.session.refresh(g.user)
        assert g.user.first_name == "Air Flow"

    def test_manage_user_roles__manage_all(self, appbuilder, role, user):
        sm = appbuilder.sm

        user.roles.append(role("Other"))
        user.roles.append(role("Viewer"))
        sm.manage_user_roles(user, ["Admin", "User"])

        assert {r.name for r in user.roles} == {"Admin", "User"}

    def test_manage_user_roles__manage_subset(self, appbuilder, user, role, monkeypatch):
        sm = appbuilder.sm
        monkeypatch.setattr(sm, "roles_to_manage", {"Admin", "Viewer", "Op", "User"})
        user.roles.append(role("Other"))
        user.roles.append(role("Viewer"))
        sm.manage_user_roles(user, ["Admin", "User"])

        assert {r.name for r in user.roles} == {"Admin", "User", "Other"}

    @pytest.mark.parametrize("leeway", [0, 60])
    def test_expired(self, appbuilder, signed_jwt, valid_claims, monkeypatch, leeway):
        monkeypatch.setattr(appbuilder.sm, "validity_leeway", leeway)
        valid_claims["exp"] = int(time.time()) - leeway - 1

        jwt = signed_jwt(valid_claims)
        resp = self.client.get(url_for("home"), headers=[("Authorization", "Bearer " + jwt)])
        assert resp.status_code == 403

    @pytest.mark.parametrize("leeway", [0, 60])
    def test_not_yet_valid(self, appbuilder, signed_jwt, valid_claims, monkeypatch, leeway):
        monkeypatch.setattr(appbuilder.sm, "validity_leeway", leeway)
        valid_claims["nbf"] = int(time.time()) + leeway + 10

        jwt = signed_jwt(valid_claims)
        resp = self.client.get(url_for("home"), headers=[("Authorization", "Bearer " + jwt)])
        assert resp.status_code == 403


@pytest.mark.usefixtures("run_in_transaction", "airflow_config")
class TestAirflowAstroSecurityManger:
    def test_default_config(self, appbuilder, jwt_signing_keypair, allowed_audience):
        sm = AirflowFabricSecurityManager(appbuilder)

        assert sm.allowed_audience == allowed_audience
        assert sm.jwt_signing_cert.thumbprint() == jwt_signing_keypair.thumbprint()
        assert sm.validity_leeway == 60

    @pytest.mark.parametrize("leeway", [0, 120])
    def test_leeway(self, appbuilder, monkeypatch, leeway):
        monkeypatch.setitem(os.environ, "AIRFLOW__DATAFABRIC__JWT_VALIDITY_LEEWAY", str(leeway))
        sm = AirflowFabricSecurityManager(appbuilder)

        assert sm.validity_leeway == leeway
