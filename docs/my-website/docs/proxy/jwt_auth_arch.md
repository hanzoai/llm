import Image from '@theme/IdealImage';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Control Model Access with OIDC (Azure AD/Keycloak/etc.)

:::info

✨ JWT Auth is on LLM Enterprise

[Enterprise Pricing](https://www.hanzo.ai/#pricing)

[Get free 7-day trial key](https://www.hanzo.ai/#trial)

:::

<Image img={require('../../img/control_model_access_jwt.png')} style={{ width: '100%', maxWidth: '4000px' }} />

## Example Token 

<Tabs>
<TabItem value="Azure AD">

```bash
{
  "sub": "1234567890",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "roles": ["basic_user"] # 👈 ROLE
}
```
</TabItem>
<TabItem value="Keycloak">

```bash
{
  "sub": "1234567890",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "resource_access": {
    "llm-test-client-id": {
      "roles": ["basic_user"] # 👈 ROLE
    }
  }
}
```
</TabItem>
</Tabs>

## Proxy Configuration

<Tabs>
<TabItem value="Azure AD">

```yaml
general_settings:
  enable_jwt_auth: True 
  llm_jwtauth:
    user_roles_jwt_field: "roles" # the field in the JWT that contains the roles 
    user_allowed_roles: ["basic_user"] # roles that map to an 'internal_user' role on LLM 
    enforce_rbac: true # if true, will check if the user has the correct role to access the model
  
  role_permissions: # control what models are allowed for each role
    - role: internal_user
      models: ["anthropic-claude"]

model_list:
    - model: anthropic-claude
      llm_params:
        model: claude-3-5-haiku-20241022
    - model: openai-gpt-4o
      llm_params:
        model: gpt-4o
```

</TabItem>
<TabItem value="Keycloak">

```yaml
general_settings:
  enable_jwt_auth: True 
  llm_jwtauth:
    user_roles_jwt_field: "resource_access.llm-test-client-id.roles" # the field in the JWT that contains the roles
    user_allowed_roles: ["basic_user"] # roles that map to an 'internal_user' role on LLM 
    enforce_rbac: true # if true, will check if the user has the correct role to access the model
  
  role_permissions: # control what models are allowed for each role
    - role: internal_user
      models: ["anthropic-claude"]

model_list:
    - model: anthropic-claude
      llm_params:
        model: claude-3-5-haiku-20241022
    - model: openai-gpt-4o
      llm_params:
        model: gpt-4o
```

</TabItem>
</Tabs>


## How it works

1. Specify JWT_PUBLIC_KEY_URL - This is the public keys endpoint of your OpenID provider. For Azure AD it's `https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys`. For Keycloak it's `{keycloak_base_url}/realms/{your-realm}/protocol/openid-connect/certs`.

1. Map JWT roles to LLM roles - Done via `user_roles_jwt_field` and `user_allowed_roles`
    -  Currently just `internal_user` is supported for role mapping. 
2. Specify model access: 
    - `role_permissions`: control what models are allowed for each role. 
        - `role`: the LLM role to control access for. Allowed roles = ["internal_user", "proxy_admin", "team"]
        - `models`: list of models that the role is allowed to access. 
    - `model_list`: parent list of models on the proxy. [Learn more](./configs.md#llm-configs-model_list)

3. Model Checks: The proxy will run validation checks on the received JWT. [Code](https://github.com/hanzoai/llm/blob/3a4f5b23b5025b87b6d969f2485cc9bc741f9ba6/llm/proxy/auth/user_api_key_auth.py#L284)