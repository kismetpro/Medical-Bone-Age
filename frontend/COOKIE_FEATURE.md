# Cookie 功能说明

## 概述

本项目已实现完整的 Cookie 管理功能，包括用户认证、偏好设置和 Cookie 同意管理。

## 功能特性

### 1. Cookie 类型

#### 必要 Cookie
- **用途**: 用户认证、会话管理
- **状态**: 始终启用，无法禁用
- **数据**: 用户名、角色、认证令牌
- **过期时间**: 30 天

#### 功能 Cookie
- **用途**: 界面偏好设置、个性化体验
- **状态**: 可选择启用/禁用
- **数据**: 主题、语言、界面设置等
- **过期时间**: 30 天

#### 分析 Cookie
- **用途**: 系统优化、性能提升
- **状态**: 可选择启用/禁用
- **数据**: 使用统计、性能数据
- **过期时间**: 30 天

### 2. Cookie 管理组件

#### CookieBanner (Cookie 横幅)
- **位置**: 页面底部
- **触发**: 首次访问或未同意时显示
- **功能**:
  - 显示 Cookie 使用说明
  - 提供"接受所有 Cookie"和"仅必要 Cookie"选项
  - 可展开查看详细 Cookie 类型说明
  - 记录用户同意状态

#### CookieSettings (Cookie 设置)
- **位置**: 模态对话框
- **触发**: 通过首页导航栏的设置按钮打开
- **功能**:
  - 管理各类 Cookie 的启用状态
  - 重置为默认设置
  - 清除所有 Cookie
  - 实时保存偏好设置

### 3. Cookie 安全性

- **HttpOnly**: 认证 Cookie 设置为 HttpOnly，防止 XSS 攻击
- **Secure**: 生产环境下启用 HTTPS 传输
- **SameSite**: 设置为 'lax'，防止 CSRF 攻击
- **加密**: 敏感数据不存储在 Cookie 中

## 技术实现

### 文件结构

```
frontend/src/
├── lib/
│   └── cookieManager.ts          # Cookie 管理工具
├── components/
│   ├── CookieBanner.tsx           # Cookie 横幅组件
│   ├── CookieBanner.module.css     # Cookie 横幅样式
│   ├── CookieSettings.tsx         # Cookie 设置组件
│   └── CookieSettings.module.css  # Cookie 设置样式
├── context/
│   └── AuthContext.tsx           # 认证上下文（已集成 Cookie）
└── lib/
    └── api.ts                    # API 工具（已集成 Cookie）
```

### CookieManager 工具

提供统一的 Cookie 操作接口：

```typescript
// 基础操作
CookieManager.set(key, value, options)
CookieManager.get(key)
CookieManager.getJSON(key)
CookieManager.remove(key)
CookieManager.removeAll()

// 认证相关
AuthCookie.setUser(user)
AuthCookie.getUser()
AuthCookie.setToken(token)
AuthCookie.getToken()
AuthCookie.clearAuth()

// 同意管理
ConsentCookie.setConsent(consented)
ConsentCookie.getConsent()
ConsentCookie.hasConsented()

// 偏好设置
PreferencesCookie.setPreferences(preferences)
PreferencesCookie.getPreferences()
PreferencesCookie.updatePreference(key, value)
```

### 集成现有系统

#### 认证系统
- 用户登录时同时保存到 localStorage 和 Cookie
- 认证请求优先从 Cookie 获取令牌
- 登出时清除所有认证相关的 Cookie

#### API 请求
- `buildAuthHeaders()` 函数自动从 Cookie 获取认证令牌
- 支持跨域请求的 Cookie 传输
- 与后端的 HttpOnly Cookie 兼容

## 使用示例

### 用户流程

1. **首次访问**
   - 显示 Cookie 横幅
   - 用户选择接受或拒绝 Cookie
   - 记录用户同意状态

2. **登录**
   - 用户输入凭据
   - 系统创建认证 Cookie
   - 同时保存到 localStorage 和 Cookie

3. **使用中**
   - 自动携带 Cookie 进行认证请求
   - 根据偏好设置调整界面
   - 收集使用统计数据（如果启用）

4. **设置管理**
   - 点击导航栏设置按钮
   - 调整 Cookie 偏好
   - 保存设置或清除 Cookie

### 开发者使用

```typescript
import { AuthCookie, PreferencesCookie } from './lib/cookieManager';

// 获取当前用户
const user = AuthCookie.getUser();

// 更新用户偏好
PreferencesCookie.updatePreference('theme', 'dark');

// 检查用户是否同意 Cookie
if (ConsentCookie.hasConsented()) {
  // 启用分析功能
}
```

## 隐私合规

### GDPR 合规
- 提供明确的 Cookie 同意机制
- 用户可随时撤回同意
- 详细的 Cookie 类型说明
- 清除所有 Cookie 的选项

### 数据保护
- 最小化数据收集原则
- 敏感数据不存储在 Cookie 中
- 定期清理过期 Cookie
- 提供数据删除功能

## 配置选项

### 环境变量

```env
# Cookie 安全设置
NODE_ENV=production  # 生产环境启用 Secure Cookie

# Cookie 过期时间（天）
COOKIE_EXPIRES_DAYS=30
```

### 自定义配置

在 `cookieManager.ts` 中修改：

```typescript
const COOKIE_OPTIONS = {
  expires: 30,              // 过期时间（天）
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/'
};
```

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 故障排除

### Cookie 不生效
1. 检查浏览器是否禁用 Cookie
2. 确认没有隐私插件拦截
3. 检查域名和路径设置
4. 查看浏览器开发者工具的 Cookie 面板

### 跨域问题
1. 确认后端 CORS 设置正确
2. 检查 SameSite 属性设置
3. 确认域名匹配

### 认证失败
1. 清除所有 Cookie 重新登录
2. 检查 Cookie 过期时间
3. 确认令牌格式正确

## 未来改进

- [ ] 添加 Cookie 使用统计面板
- [ ] 实现更细粒度的权限控制
- [ ] 添加 Cookie 导入/导出功能
- [ ] 支持多语言 Cookie 说明
- [ ] 集成第三方分析工具（如 Google Analytics）

## 技术支持

如有问题或建议，请联系开发团队。