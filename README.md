# Guardian
Guardian is an advanced backend for offensive security reporting. It streamlines test execution, letting security
experts prioritize vulnerability identification and defense strengthening. With clear reporting, Guardian offers a
detailed view of system security. Illuminate vulnerabilities and excel with Guardian.

# Repository Setup

This repository contains the backend code for Guardian. The database schema is maintained in a separate repository to
ensure that it can be shared with other projects. The schema repository is added as a submodule to this repository
using the following commands:

```commandline
git clone --recursive git@github.com:chopicalqui/guardian-backend.git
```

# Identity Provider Configuration

Guardian does not implement its own user management and just integrates with one of the following Identity
Providers (IdP):

- **Keycloak**: In Keycloak, the OpenID configuration is usually accessible via the following URL:
  `$origin/realms/$realm/.well-known/openid-configuration`.
- **Microsoft Active Directory Federation Services** (ADFS): In ADFS, the OpenID configuration is usually accessible
  via the following URL: `$origin/adfs/.well-known/openid-configuration`.

In order to integrate with one of these IdPs, we have to expose the following environment variables, which can also be
defined in file [.env.api.dev](./app/.env.api).

| **Ref.** | **Variable** | **Description** |
| --- | ---------- | --------- |
| 1 | `IDP`               | Tells Guardian the type of IdP being used. Valid values are: `keycloak`, `adfs` |
| 2 | `CLIENT_ID`         | The client ID obtained from KeyCloak/ADFS to uniquely identify the application. |
| 3 | `CLIENT_SECRET`     | The client secret associated with the `CLIENT_ID`. Guardian uses the `CLIENT_ID` and `CLIENT_SECRET` to authenticate to ther IdP in the background. |
| 4 | `REDIRECT_URI`      | The Guardian's callback URL (`$origin/api/callback`) to which the IdP redirects after the successful authentication. |
| 5 | `AUDIENCE`          | The token endpoint (see `TOKEN_URL`) returns an access token, which contains an `aud` attribute. The `AUDIENCE` value must match the returned `aud` value, else token validation fails. |
| 6 | `ISSUER`            | The value of the JSON attribute `issuer` of the OpenID configuration. It is used during token validation to ensure it was issued by the right authority. If there is a mismatch, then token validation fails. |
| 7 | `TOKEN_URL`         | The value of the JSON attribute `token_endpoint` of the OpenID configuration. |
| 8 | `AUTHORIZATION_URL` | The value of the JSON attribute `authorization_endpoint` of the OpenID configuration. |
| 9 | `JWKS_URL`          | The value of the JSON attribute `jwks_uri` of the OpenID configuration. |

# Development Setup

In order to develop the application, we need to start the following services:

| **Ref.** | **Service** | **Port** | **Description**    | **Docker** | **Web Address**                                             |
|----------|-------------|----------|--------------------|------------|-------------------------------------------------------------|
| 1        | PostgreSQL  | 5432     | Database           | Yes        | -                                                           |
| 2        | Keycloak    | 8081     | Identity Provider  | Yes        | http://localhost:8000/idp                                   |
| 3        | NGINX       | 8000     | Reverse Proxy      | Yes        | -                                                           |
| 4        | Frontend    | 3000     | Web application    | No         | http://localhost:8000/                                      |
| 5        | Backend     | 8000     | REST API           | No         | http://localhost:8000/api, http://localhost:8090/api        |
| 6        | OpenAPI     | 8090     | OpenAPI Definition | No         | http://127.0.0.1:8090/docs#/, http://127.0.0.1:8090/redoc#/ |

The NGINX reverse proxy ensures that the frontend and backend are accessible via the same port (8000). This is
necessary because the backend issues cookies, which are only accessible via the same origin.

The Docker environment can be launched using the following command:

```commandline
docker-compose up
```

Note that running `docker-compose` with argument `up` is important in order to expose Nginx at TCP port 8000 and 
PostgreSQL at TCP port 5432.

Once everything is up and running, you can access the different web applications via the reverse proxy at
http://localhost:8000.

# Audit Report

The audit report is a document that contains information about security relevant configurations. The report lists
the scopes for each REST API endpoint as well as the mapping between scopes and roles. The report is generated using
the following command:

```commandline
python app/audit-report.py -t scopes roles -o "Audit Report.xlsx"
```
