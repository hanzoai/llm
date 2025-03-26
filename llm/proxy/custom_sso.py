"""
Example Custom SSO Handler

Use this if you want to run custom code after llm has retrieved information from your IDP (Identity Provider).

Flow:
- User lands on Admin UI
- LLM redirects user to your SSO provider
- Your SSO provider redirects user back to LLM
- LLM has retrieved user information from your IDP
- Your custom SSO handler is called and returns an object of type SSOUserDefinedValues
- User signed in to UI
"""

from fastapi_sso.sso.base import OpenID

from llm.proxy._types import LlmUserRoles, SSOUserDefinedValues
from llm.proxy.management_endpoints.internal_user_endpoints import user_info


async def custom_sso_handler(userIDPInfo: OpenID) -> SSOUserDefinedValues:
    try:
        print("inside custom sso handler")  # noqa
        print(f"userIDPInfo: {userIDPInfo}")  # noqa

        if userIDPInfo.id is None:
            raise ValueError(
                f"No ID found for user. userIDPInfo.id is None {userIDPInfo}"
            )

        # check if user exists in llm proxy DB
        _user_info = await user_info(user_id=userIDPInfo.id)
        print("_user_info from llm DB ", _user_info)  # noqa

        return SSOUserDefinedValues(
            models=[],
            user_id=userIDPInfo.id,
            user_email=userIDPInfo.email,
            user_role=LLMUserRoles.INTERNAL_USER.value,
            max_budget=10,
            budget_duration="1d",
        )
    except Exception:
        raise Exception("Failed custom auth")
