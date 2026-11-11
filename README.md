# ManicEMU → TrollStore

自动把 ManicEMU 的 SideloadJIT 包转成 TrollStore 能装的版本。

## 为什么需要

ManicEMU 从 2.0.0 起只发 SideloadJIT 包，TrollStore 装不上。
本仓库把 v1.9.2 里的 TrollStore 素材（JIT 插件 + entitlements）搬到新版本上。

## 用法

打开 [Releases](../../releases)，下最新的 `ManicEMU.vX.X.X.TrollStore.ipa`。

安装：

1. 先卸载设备上的旧版（同 Bundle ID，不卸会沿用旧数据目录）
2. 长按 ipa → 共享 → TrollStore → Install

点开秒退时查：设置 → 隐私与安全性 → 分析与改进 → 分析数据 → `ManicEmu-*.ips`

## 自动化

每 6 小时查一次上游最新 release：

- 上游有官方 `TrollStoreJIT` 资产 → 原样转发
- 只有 `SideloadJIT` → 走转制
- 该版本已发布过 → 跳过

手动触发：

```
Actions → Build TrollStore IPA → Run workflow
  version: 2.0.3      # 留空取最新
  force:   true       # 覆盖已有 release
```

## 转制原理

| 步骤 | 内容 |
|---|---|
| 提取素材 | 从上游 v1.9.2 TrollStoreJIT 包取插件 dylib + 主程序 entitlements |
| 注入 | Mach-O 头 `32+sizeofcmds` 处写 72 字节 `LC_LOAD_WEAK_DYLIB`，指向 `@executable_path/TrollStoreJITEnabler.dylib` |
| 签名 | 主程序 `ldid -S ts.entitlements`，其余 Mach-O 空签，插件 dylib 不重签 |
| 打包 | 只遍历 `Payload`，Mach-O 设 0755，其他 0644 |

关键数值（无效即停）：

- dylib `158896` 字节，sha256 `f1b267ba…3e45ae30`
- entitlements `998` 字节
- injections 后 `LC_CODE_SIGNATURE` 的 `dataoff+datasz` 必须等于文件长度

entitlements 共 11 项，`no-sandbox` 与 `storage.AppDataContainers` 必须同时存在，否则点开秒崩。

## 文件

| 文件 | 作用 |
|---|---|
| `inject.py` | 往主程序写入加载指令 |
| `sign.py` | 批量重签（主程序带权限，其余空签） |
| `pack.py` | 打包 ipa，控制权限位 |
| `findmain.py` | 定位 .app 里的主程序 |
| `verify.py` | 产物自检 |
| `pdl.sh` | 8 段并行下载 |
| `build.sh` | 本地一键转制 |

## 本地使用

```sh
sh pdl.sh "<SideloadJIT的ipa链接>" src.ipa 8
sh build.sh src.ipa ./out
```

需要 `ldid`、`python3`、`unzip`。

## 校验记录

v2.0.2 转制产物（本仓库流程复现）：

```
293,208,150 字节
sha256 a3c6a2abcff798bcbb79ccc87096af17aa0fb1dd2811cde38577a3081b3e56ae
```
