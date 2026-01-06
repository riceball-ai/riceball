# OAuth 配置指南

RiceBall 支持通过 OAuth 2.0 进行第三方登录。你可以在系统中配置多个 OAuth 提供商。

## 配置管理

OAuth 提供商信息存储在数据库中。你可以通过管理后台进行配置，或者通过系统脚本进行初始化。

所有提供商的通用字段：

- **名称 (Provider Name)**: 唯一标识符 (例如 `google`, `github`, `wecom`)。某些特定名称会触发内置的特殊处理逻辑。
- **Client ID**: 应用的公开标识符。
- **Client Secret**: 应用的密钥。
- **Auth URL**: 用户授权重定向地址。
- **Token URL**: 用于将授权码 (code) 交换为访问令牌 (access token) 的接口地址。
- **User Info URL**: 用于获取用户个人信息的接口地址。
- **Scopes**: 需要申请的权限列表 (例如 `["email", "profile"]`)。
- **字段映射 (User Mapping)**: 用于将提供商返回的 JSON 用户信息映射到 RiceBall 用户字段的 JSON 对象。
  - 源 (Key): 提供商 JSON 响应中的字段路径 (支持点号 `.` 表示嵌套，如 `data.email`)。
  - 目标 (Value): RiceBall 的用户字段 (`email`, `name`, `avatar`)。

## 回调地址 (Callback URL / Redirect URI)

在 OAuth 提供商处注册应用时，你需要填写 **回调地址**。RiceBall 根据你的部署地址和提供商名称自动生成此地址。

格式:
`https://{你的域名}/api/v1/auth/{PROVIDER_NAME}/callback`

示例:
- **本地开发 (Google)**: `http://localhost:8000/api/v1/auth/google/callback`
- **生产环境 (GitHub)**: `https://chat.example.com/api/v1/auth/github/callback`
- **生产环境 (WeCom)**: `https://chat.example.com/api/v1/auth/wecom/callback`

> **注意**: 确保 URL 中的 **PROVIDER_NAME** 与你在 RiceBall 中配置的“名称”完全一致。

---

## 标准 OAuth 2.0 提供商

对于标准的 OAuth 2.0 提供商 (如 Google, Auth0, Keycloak)，使用通用配置即可。

**示例 (Google):**

- **名称**: `google`
- **Client ID**: `YOUR_GOOGLE_CLIENT_ID`
- **Client Secret**: `YOUR_GOOGLE_CLIENT_SECRET`
- **Auth URL**: `https://accounts.google.com/o/oauth2/v2/auth`
- **Token URL**: `https://oauth2.googleapis.com/token`
- **User Info URL**: `https://www.googleapis.com/oauth2/v3/userinfo`
- **Scopes**: `["openid", "email", "profile"]`
- **字段映射**:
  ```json
  {
    "email": "email",
    "name": "name",
    "avatar": "picture"
  }
  ```

---

## GitHub

GitHub 需要特殊处理，因为用户的邮箱可能不公开，或者默认的用户信息接口不包含邮箱。RiceBall 内置了 GitHub 专用处理器。

**要求:**
- **名称**: 必须为 `github`.

**配置:**

- **名称**: `github`
- **Client ID**: `YOUR_GITHUB_CLIENT_ID`
- **Client Secret**: `YOUR_GITHUB_CLIENT_SECRET`
- **Auth URL**: `https://github.com/login/oauth/authorize`
- **Token URL**: `https://github.com/login/oauth/access_token`
- **User Info URL**: `https://api.github.com/user`
- **Scopes**: `["user:email"]` (必须包含此权限以获取邮箱)
- **字段映射**:
  ```json
  {
    "email": "email",
    "name": "login",
    "avatar": "avatar_url"
  }
  ```

**工作原理:**
如果用户信息中缺少主邮箱，后端会自动调用 `https://api.github.com/user/emails` 接口，并选择经过验证的主邮箱 (Primary Verified Email)。

---

## 企业微信 (WeCom / Wechat Enterprise)

企业微信使用的是非标准的 OAuth 流程。RiceBall 提供了专用的企业微信处理器。

**要求:**
- **名称**: 必须为 `wecom`.

**字段对应关系:**
- **Client ID**: 填写你的 **CorpID** (企业 ID)。
- **Client Secret**: 填写你的 **App Secret** (应用 Secret)。
- **Auth URL**: 必须包含 `agentid` 参数。

**配置示例:**

- **名称**: `wecom`
- **Client ID**: `ww1234567890abcdef` (你的 CorpID)
- **Client Secret**: `YOUR_APP_SECRET`
- **Auth URL**: 
  ```
  https://login.work.weixin.qq.com/wwlogin/sso/login
  ```

- **Token URL**: `https://qyapi.weixin.qq.com/cgi-bin/gettoken`
- **User Info URL**: `https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo`
- **Scopes**: *(可留空，扫码登录不使用此参数)*
- **字段映射**:
  ```json
  {
    "id": "UserId",
    "name": "name",
    "email": "email",
    "avatar": "avatar"
  }
  ```

**工作原理:**
1. **授权**: 重定向用户到企业微信扫码登录页 (qrConnect 或 SSO)。
2. **获取 Token**: 使用 `client_credentials` 模式 (CorpID + Secret) 获取全局的 **App Access Token**。
3. **获取用户信息**: 使用 App Access Token 和回调中的 `code` 换取用户的身份 (`UserId`)，然后进一步获取详细信息。
