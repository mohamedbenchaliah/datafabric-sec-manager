import json
import logging
import os

from flask import abort, request
from flask_appbuilder.security.manager import AUTH_REMOTE_USER
from flask_appbuilder.security.views import AuthView, expose
from flask_login import current_user, login_user
from jwcrypto import jwk, jws, jwt

try:
    from airflow.www_rbac.security import AirflowSecurityManager, EXISTING_ROLES
except ImportError:
    try:
        from airflow.www.security import AirflowSecurityManager, EXISTING_ROLES
    except ImportError:
        # Airflow not installed, likely we are running setup.py to _install_ things
        class AirflowSecurityManager(object):
            def __init__(self, appbuilder):
                pass

        EXISTING_ROLES = []


_logger: logging.Logger = logging.getLogger(__name__)


class SecurityManagerMixin(object):
    """Flask Class to auto-creates users based 
    on the signed JWT token from the Datafabric platform.
    """

    def __init__(self, appbuilder, jwt_signing_cert, allowed_audience, roles_to_manage=None, validity_leeway=60):
        super().__init__(appbuilder)
        if self.auth_type == AUTH_REMOTE_USER:
            self.authremoteuserview = AuthJwtView
        self.jwt_signing_cert = jwt_signing_cert
        self.allowed_audience = allowed_audience
        self.roles_to_manage = roles_to_manage
        self.validity_leeway = validity_leeway

    def before_request(self):
        """Validate  the JWT token provider in the
        Authorization HTTP header and log in the user.

        Returns
        -------
        None
        """

        if request.path == "/health":
            return super().before_request()

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return abort(403)

        if not auth_header.startswith("Bearer "):
            return abort(403)

        try:
            token = jwt.JWT(
                check_claims={
                    # These must be present - any value
                    "sub": None,
                    "email": None,
                    "full_name": None,
                    "roles": None,
                    # Use it's built in handling - 60s leeway, 10minutes validity.
                    "exp": None,
                    "nbf": None,
                    # This must match exactly
                    "aud": self.allowed_audience,
                }
            )

            token.leeway = self.validity_leeway
            token.deserialize(jwt=auth_header[7:], key=self.jwt_signing_cert)
            claims = json.loads(token.claims)
        except jws.InvalidJWSSignature:
            abort(403)
        except jwt.JWException as e:
            _logger.debug(e)
            abort(403)

        if not isinstance(claims["roles"], list):
            abort(403)

        if current_user.is_anonymous:
            user = self.find_user(username=claims["sub"])
            if user is None:
                _logger.info("Creating airflow user details for %s from JWT", claims["email"])
                user = self.user_model(
                    username=claims["sub"],
                    first_name=claims["full_name"] or claims["email"],
                    last_name="",
                    email=claims["email"],
                    roles=[self.find_role(role) for role in claims["roles"]],
                    active=True,
                )
            else:
                _logger.info("Updating airflow user details for %s from JWT", claims["email"])

                user.username = claims["sub"]
                user.first_name = claims["full_name"] or claims["email"]
                user.last_name = ""
                user.active = True
                self.manage_user_roles(user, claims["roles"])

            self.get_session.add(user)
            self.get_session.commit()
            if not login_user(user):
                raise RuntimeError("Error logging user in!")

        super().before_request()

    def manage_user_roles(self, user, roles):

        """Manage the core roles on the user.

        Parameters
        ----------
        user : str
            e.g. data_engineer
        roles : list[str]
            e.g. ['Admin', 'User', 'Other']

        Returns
        -------
        None
        """

        desired = set(roles)

        if self.roles_to_manage:
            roles_to_remove = self.roles_to_manage - desired
        else:
            # Every role that isn't in `roles` should be removed from this
            # user
            roles_to_remove = {r.name for r in user.roles} - desired

        # Capture it in a variable - otherwise it changes underneath us as we
        # iterate and we miss some
        current_roles = list(user.roles)

        for role in current_roles:
            if role.name in roles_to_remove:
                user.roles.remove(role)
            elif role.name in desired:
                desired.remove(role.name)

        # Anything left in desired is a role we need to add
        for role in desired:
            user.roles.append(self.find_role(role))


class AirflowFabricSecurityManager(SecurityManagerMixin, AirflowSecurityManager):
    """
    A class to configure the Security Manager for use in Airflow.
    """

    def __init__(self, appbuilder):
        from airflow.configuration import conf
        from airflow.exceptions import AirflowConfigException

        self.jwt_signing_cert_mtime = 0

        self.jwt_signing_cert_path = conf.get("datafabric", "jwt_signing_cert")
        self.reload_jwt_signing_cert()

        allowed_audience = conf.get("datafabric", "jwt_audience")

        kwargs = {
            "appbuilder": appbuilder,
            "jwt_signing_cert": self.jwt_signing_cert,
            "allowed_audience": allowed_audience,
            "roles_to_manage": EXISTING_ROLES,
        }

        # Airflow 1.10.2 doesn't have `fallback` support yet
        try:
            leeway = conf.get("datafabric", "jwt_validity_leeway", fallback=None)
            if leeway is not None:
                kwargs["validity_leeway"] = int(leeway)
        except AirflowConfigException:
            pass

        super().__init__(**kwargs)

    def reload_jwt_signing_cert(self):
        """
        Load the JWT signing certificate from disk if the file has been modified.
        """
        stat = os.stat(self.jwt_signing_cert_path)
        if stat.st_mtime_ns > self.jwt_signing_cert_mtime:
            _logger.info("Loading datafabric JWT signing cert from %s", self.jwt_signing_cert_path)
            with open(self.jwt_signing_cert_path, "rb") as fh:
                self.jwt_signing_cert = jwk.JWK.from_pem(fh.read())
                # This does a second stat, but only when changed, and ensures
                # that the time we record matches _exactly_ the time of the
                # file we opened.
                self.jwt_signing_cert_mtime = os.fstat(fh.fileno()).st_mtime_ns

    def before_request(self):
        # To avoid making lots of stat requests don't do this for static
        # assets, just Airflow pages and API endpoints
        if not request.path.startswith("/static/"):
            self.reload_jwt_signing_cert()
        return super().before_request()

    def sync_roles(self):
        super().sync_roles()

        for (view_menu, permission) in [
            ("UserDBModelView", "can_userinfo"),
            ("UserDBModelView", "userinfoedit"),
            ("UserRemoteUserModelView", "can_userinfo"),
            ("UserRemoteUserModelView", "userinfoedit"),
            ("UserInfoEditView", "can_this_form_get"),
            ("UserInfoEditView", "can_this_form_post"),
        ]:
            perm = self.find_permission_view_menu(permission, view_menu)
            # If we are only using the RemoteUser auth type, then the DB permissions won't exist. Just continue
            if not perm:
                continue

            self.add_permission_role(self.find_role("User"), perm)
            self.add_permission_role(self.find_role("Op"), perm)
            self.add_permission_role(self.find_role("Viewer"), perm)

        for (view_menu, permission) in [
            ("Airflow", "can_dagrun_success"),
            ("Airflow", "can_dagrun_failed"),
            ("Airflow", "can_failed"),
        ]:
            self.add_permission_role(self.find_role("User"), self.find_permission_view_menu(permission, view_menu))
            self.add_permission_role(self.find_role("Op"), self.find_permission_view_menu(permission, view_menu))

        for (view_menu, permission) in [("VariableModelView", "varexport")]:
            self.add_permission_role(self.find_role("Op"), self.find_permission_view_menu(permission, view_menu))


class AuthJwtView(AuthView):
    """
    If no permissions, users are automatically redirected
    to the login function of this class. This class is faking a 403 error.
    """

    @expose("/access-denied/")
    def login(self):
        return abort(403)
