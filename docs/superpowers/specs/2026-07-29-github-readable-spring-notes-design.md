# GitHub 可读的 Spring 笔记设计

日期：2026-07-29  
目标仓库：`15827196717/study-spring`

## 背景

公司网络可以访问 `github.com`，但可能限制 `github.io`、有道云笔记、CDN
和其他外部资源。仓库中的 Word 文档无法在 GitHub 文件页面直接预览，并且
当前文档约 14.9 MB，也超过 GitHub 常规文件展示的适宜大小。

因此，主要阅读入口必须使用 GitHub 原生渲染的 Markdown；GitHub Pages
只能作为附加体验，不能是唯一入口。

## 目标

- 访问仓库首页即可看到笔记简介和完整章节目录。
- 所有正文、代码块和图片均可在 `github.com` 内直接阅读。
- 不依赖有道云、外部字体、CDN、第三方脚本或外部图片。
- 将完整笔记拆分为适合 GitHub 渲染的章节文档。
- 保留现有 Word 文档，供下载和离线编辑。
- 提供可选的增强版 GitHub Pages 阅读页。
- 建立自动检查，防止章节、题目、图片或链接遗漏。

## 非目标

- 不修改已有的 Spring 源码学习资料目录。
- 不引入数据库、后端服务、登录系统或内容管理系统。
- 不要求公司网络能够访问 `github.io`。
- 不在 GitHub Markdown 页面中依赖自定义 JavaScript。

## 信息架构

仓库首页使用 `README.md` 作为稳定入口，展示：

- 笔记名称与适用范围；
- 阅读说明；
- 按主题组织的章节目录；
- Word 文档下载入口；
- 可选的 GitHub Pages 增强版入口。

正文按主题拆分为以下文档：

1. Spring Framework
2. Spring IoC
3. Spring Beans
4. Spring 注解
5. Spring AOP
6. Spring 事务
7. Spring 其他
8. Spring MVC
9. Spring Boot
10. 微服务

每章顶部显示返回首页链接，底部显示上一章和下一章链接。

## 文件结构

```text
README.md
docs/
  01-spring-framework.md
  02-spring-ioc.md
  03-spring-beans.md
  04-spring-annotations.md
  05-spring-aop.md
  06-spring-transactions.md
  07-spring-other.md
  08-spring-mvc.md
  09-spring-boot.md
  10-microservices.md
assets/
  images/
site/
  index.html
  styles.css
  app.js
.github/
  workflows/
    pages.yml
```

设计文档保存在 `docs/superpowers/specs/`，不出现在用户阅读目录中。

## 内容转换

转换以已经从有道云分享页提取的完整内容快照为源，不从 Word 文档反向解析。

处理规则：

- 将一级主题转换为 Markdown 一级标题；
- 将编号问题转换为二级标题，并生成稳定的章节锚点；
- 保留普通段落、编号列表、项目列表和代码块；
- 将 69 张图片下载到 `assets/images/`；
- 将 WebP 图片转换为 PNG，其他兼容格式保持不变；
- 使用仓库相对路径引用图片和章节；
- 保留题目原编号和原文，包括原笔记自身的缺号或重复编号，不擅自补题或重写
  技术答案。

## GitHub 原生阅读

GitHub 原生 Markdown 是公司环境的主要交付方式：

- 页面只依赖 `github.com` 及其自身静态资源；
- GitHub 负责代码高亮、深色模式和标题目录；
- 文档可通过浏览器页面内搜索查找关键词；
- 根目录 README 和各章节页面均不加载自定义脚本；
- 图片从同一仓库读取，不回源到有道云。

## GitHub Pages 增强版

Pages 版本为单页静态站点，包含：

- 固定或可折叠的章节目录；
- 全文关键词搜索；
- 当前章节高亮；
- 阅读进度；
- 深色模式；
- 返回顶部；
- 手机端响应式布局。

Pages 站点不使用框架、外部字体或 CDN，仅包含原生 HTML、CSS、JavaScript
和仓库内图片。它是附加入口；Pages 无法访问时，Markdown 阅读不受影响。

## 数据流

```text
有道云内容快照
  -> 内容转换脚本
  -> Markdown 章节 + 本地图片
  -> README 导航
  -> 静态 HTML 页面
  -> 本地验证
  -> Git 分支和 Pull Request
  -> 合并到 main
  -> GitHub README 立即可读
  -> GitHub Actions 部署可选 Pages
```

## 异常处理

- 图片下载失败：转换任务失败并报告具体 URL，不生成缺图的最终提交。
- 图片格式不兼容：转换为 PNG 后再引用。
- 题目或章节数量异常：验证失败并阻止提交。
- Markdown 链接失效：本地链接检查失败并阻止提交。
- Pages 构建失败：保留 GitHub Markdown 作为稳定阅读入口，并从 Actions
  日志定位构建问题。
- 公司网络屏蔽 Pages：用户仍从仓库首页和 `docs/` 阅读全部内容。

## 验证

提交前必须完成：

- 10 个章节文件全部存在；
- 转换后的题目标题清单与原始快照逐项一致，题号范围保留到 100；
- 69 张图片全部存在并能被对应文档引用；
- 不存在指向有道云或其他外部图片的引用；
- README 中的章节和下载链接均有效；
- 所有 Markdown 相对链接均能解析到仓库文件；
- HTML、CSS 和 JavaScript 可在本地静态服务器中加载；
- 搜索、目录高亮、深色模式和返回顶部在桌面与手机视口可用；
- GitHub Pages 工作流语法有效。

发布后必须验证：

- 仓库首页能渲染 README；
- 每章正文和图片能在 `github.com` 显示；
- Word 文件仍可下载；
- Pages 工作流成功；
- Pages URL 可访问；若公司网络不可访问，确认不影响 Markdown 路径。

## 发布策略

所有实现放在 `codex/github-readable-notes` 分支中，通过 Pull Request
合并到 `main`。这样可以审阅变更、查看自动检查结果并在需要时回滚。

合并后：

- `https://github.com/15827196717/study-spring` 是公司环境的主要入口；
- `https://15827196717.github.io/study-spring/` 是可选的增强版入口。

## 完成标准

用户在只能访问 GitHub 仓库页面的公司网络中，可以从仓库首页进入任意章节，
阅读完整文字、代码和图片，而不依赖 Word 在线预览或 GitHub Pages。
