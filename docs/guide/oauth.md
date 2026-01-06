# OAuth Configuration

RiceBall supports third-party login via OAuth 2.0. You can configure multiple OAuth providers in the system.

## Configuration Management

OAuth providers are stored in the database. You can manage them through the Admin UI or by initializing them using system scripts.

Common fields for all providers:

- **Provider Name**: Unique identifier (e.g., `google`, `github`, `wecom`). Some names trigger special handling logic.
- **Client ID**: The public identifier for the app.
- **Client Secret**: The secret key for the app.
- **Auth URL**: The URL where users are redirected to authorize the app.
- **Token URL**: The URL used to exchange the authorization code for an access token.
- **User Info URL**: The URL used to fetch user profle information.
- **Scopes**: List of permissions to request (e.g., `["email", "profile"]`).
- **User Mapping**: JSON object mapping the provider's user info response fields to RiceBall's user fields.
  - Source: Field path in provider's JSON response (supports dot notation like `data.email`).
  - Target: RiceBall user field (`email`, `name`, `avatar`).

## Callback URL (Redirect URI)

When registering your application with the OAuth provider, you will need to provide a **Callback URL** (or Redirect URI). RiceBall generates this URL automatically based on your deployment.

Format:
`https://{YOUR_DOMAIN}/api/v1/auth/{PROVIDER_NAME}/callback`

Examples:
- **Local Dev (Google)**: `http://localhost:8000/api/v1/auth/google/callback`
- **Production (GitHub)**: `https://chat.example.com/api/v1/auth/github/callback`
- **Production (WeCom)**: `https://chat.example.com/api/v1/auth/wecom/callback`

> **Note**: Ensure the **Provider Name** in the URL matches exactly the name you used when configuring the provider in RiceBall.

---

## Standard OAuth 2.0 Provider

For standard OAuth 2.0 providers (like Google, Auth0, Keycloak), use the standard configuration.

**Example (Google):**

- **Name**: `google`
- **Client ID**: `YOUR_GOOGLE_CLIENT_ID`
- **Client Secret**: `YOUR_GOOGLE_CLIENT_SECRET`
- **Auth URL**: `https://accounts.google.com/o/oauth2/v2/auth`
- **Token URL**: `https://oauth2.googleapis.com/token`
- **User Info URL**: `https://www.googleapis.com/oauth2/v3/userinfo`
- **Scopes**: `["openid", "email", "profile"]`
- **User Mapping**:
  ```json
  {
    "email": "email",
    "name": "name",
    "avatar": "picture"
  }
  ```

---

## GitHub

GitHub requires special handling because the user's email might not be public or included in the default profile response. RiceBall has a built-in handler for GitHub.

**Requirements:**
- **Provider Name**: Must be `github`.

**Configuration:**

- **Name**: `github`
- **Client ID**: `YOUR_GITHUB_CLIENT_ID`
- **Client Secret**: `YOUR_GITHUB_CLIENT_SECRET`
- **Auth URL**: `https://github.com/login/oauth/authorize`
- **Token URL**: `https://github.com/login/oauth/access_token`
- **User Info URL**: `https://api.github.com/user`
- **Scopes**: `["user:email"]` (Required to fetch email address)
- **User Mapping**:
  ```json
  {
    "email": "email",
    "name": "login",
    "avatar": "avatar_url"
  }
  ```

**How it works:**
The backend will automatically fetch emails from `https://api.github.com/user/emails` if the primary email is missing in the user info, selecting the primary and verified email address.

---

## Enterprise WeChat (WeCom / Weixin Work)

Enterprise WeChat uses a non-standard OAuth flow. RiceBall provides a dedicated handler for WeCom.

**Requirements:**
- **Provider Name**: Must be `wecom`.

**Field Mapping:**
- **Client ID**: Fill in your **CorpID** (e.g., `ww1234...`).
- **Client Secret**: Fill in your **App Secret**.
- **Auth URL**: Must include the `agentid` parameter.

**Configuration Example:**

- **Name**: `wecom`
- **Client ID**: `ww1234567890abcdef` (Your CorpID)
- **Client Secret**: `YOUR_APP_SECRET`
- **Auth URL**: 
  ```
  https://login.work.weixin.qq.com/wwlogin/sso/login
  ```

- **Token URL**: `https://qyapi.weixin.qq.com/cgi-bin/gettoken`
- **User Info URL**: `https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo`
- **Scopes**: *(Leave empty, not used for scan login)*
- **User Mapping**:
  ```json
  {
    "id": "userid",
    "name": "name",
    "email": "email",
    "avatar": "avatar"
  }
  ```

**How it works:**
1. **Authorization**: Redirects user to WeCom Scan Login (qrConnect/SSO) page.
2. **Token Exchange**: Uses `client_credentials` flow (CorpID + Secret) to get a global **App Access Token**.
3. **User Info**: Uses the App Access Token and the `code` from the callback to fetch the user's identity (`userid`) and then their detailed profile.

---
