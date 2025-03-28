import os


def show_missing_vars_in_env():
    from fastapi.responses import HTMLResponse

    from llm.proxy.proxy_server import master_key, prisma_client

    if prisma_client is None and master_key is None:
        return HTMLResponse(
            content=missing_keys_form(
                missing_key_names="DATABASE_URL, LLM_MASTER_KEY"
            ),
            status_code=200,
        )
    if prisma_client is None:
        return HTMLResponse(
            content=missing_keys_form(missing_key_names="DATABASE_URL"), status_code=200
        )

    if master_key is None:
        return HTMLResponse(
            content=missing_keys_form(missing_key_names="LLM_MASTER_KEY"),
            status_code=200,
        )
    return None


# LLM Admin UI - Non SSO Login
url_to_redirect_to = os.getenv("PROXY_BASE_URL", "")
url_to_redirect_to += "/login"
html_form = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}

        form {{
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }}

        label {{
            display: block;
            margin-bottom: 8px;
        }}

        input {{
            width: 100%;
            padding: 8px;
            margin-bottom: 16px;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 4px;
        }}

        input[type="submit"] {{
            background-color: #4caf50;
            color: #fff;
            cursor: pointer;
        }}

        input[type="submit"]:hover {{
            background-color: #45a049;
        }}
    </style>
</head>
<body>
    <form action="{url_to_redirect_to}" method="post">
        <h2>Admin Login</h2>
        <br>
        <label for="username">Username:</label>
        <input type="text" id="username" name="username" required>
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required>
        <input type="submit" value="Submit">
    </form>
"""


def missing_keys_form(missing_key_names: str):
    missing_keys_html_form = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    color: #333;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 800px;
                    margin: auto;
                    padding: 20px;
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                h1 {{
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                pre {{
                    background: #f8f8f8;
                    padding: 1px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    overflow-x: auto;
                    font-size: 14px;
                }}
                .env-var {{
                    font-weight: normal;
                }}
                .comment {{
                    font-weight: normal;
                    color: #777;
                }}
            </style>
            <title>Environment Setup Instructions</title>
        </head>
        <body>
            <div class="container">
                <h1>Environment Setup Instructions</h1>
                <p>Please add the following variables to your environment variables:</p>
                <pre>
    <span class="env-var">LLM_MASTER_KEY="sk-1234"</span> <span class="comment"># Your master key for the proxy server. Can use this to send /chat/completion requests etc</span>
    <span class="env-var">LLM_SALT_KEY="sk-XXXXXXXX"</span> <span class="comment"># Can NOT CHANGE THIS ONCE SET - It is used to encrypt/decrypt credentials stored in DB. If value of 'LLM_SALT_KEY' changes your models cannot be retrieved from DB</span>
    <span class="env-var">DATABASE_URL="postgres://..."</span> <span class="comment"># Need a postgres database? (Check out Supabase, Neon, etc)</span>
    <span class="comment">## OPTIONAL ##</span>
    <span class="env-var">PORT=4000</span> <span class="comment"># DO THIS FOR RENDER/RAILWAY</span>
    <span class="env-var">STORE_MODEL_IN_DB="True"</span> <span class="comment"># Allow storing models in db</span>
                </pre>
                <h1>Missing Environment Variables</h1>
                <p>{missing_keys}</p>
            </div>

            <div class="container">
            <h1>Need Help? Support</h1>
            <p>Discord: <a href="https://discord.com/invite/XthHQQj" target="_blank">https://discord.com/invite/XthHQQj</a></p>
            <p>Docs: <a href="https://docs.hanzo.ai/docs/" target="_blank">https://docs.hanzo.ai/docs/</a></p>
            </div>
        </body>
        </html>
    """
    return missing_keys_html_form.format(missing_keys=missing_key_names)


def admin_ui_disabled():
    from fastapi.responses import HTMLResponse

    ui_disabled_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    color: #333;
                    margin: 20px;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 800px;
                    margin: auto;
                    padding: 20px;
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                h1 {{
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                pre {{
                    background: #f8f8f8;
                    padding: 1px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    overflow-x: auto;
                    font-size: 14px;
                }}
                .env-var {{
                    font-weight: normal;
                }}
                .comment {{
                    font-weight: normal;
                    color: #777;
                }}
            </style>
            <title>Admin UI Disabled</title>
        </head>
        <body>
            <div class="container">
                <h1>Admin UI is Disabled</h1>
                <p>The Admin UI has been disabled by the administrator. To re-enable it, please update the following environment variable:</p>
                <pre>
    <span class="env-var">DISABLE_ADMIN_UI="False"</span> <span class="comment"># Set this to "False" to enable the Admin UI.</span>
                </pre>
                <p>After making this change, restart the application for it to take effect.</p>
            </div>

            <div class="container">
            <h1>Need Help? Support</h1>
            <p>Discord: <a href="https://discord.com/invite/XthHQQj" target="_blank">https://discord.com/invite/XthHQQj</a></p>
            <p>Docs: <a href="https://docs.hanzo.ai/docs/" target="_blank">https://docs.hanzo.ai/docs/</a></p>
            </div>
        </body>
        </html>
    """

    return HTMLResponse(
        content=ui_disabled_html,
        status_code=200,
    )
