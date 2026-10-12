---
title: Windows 下 MIT/GNU Scheme 安装
date: 2023-09-03 15:28:55 +0800
categories: 
  - Tools
tags: 
excerpt: 最近，在看《计算机程序的构造和解释》，书中所用的语言为 Lisp 的方言 Scheme，所以就需要安装一下，下面简单记录了安装的过程中的一些细节。
---
<!--more-->
## 一、支持 Windows 的MIT/GNU Scheme 版本

首先，访问 [MIT/GNU Scheme](https://www.gnu.org/software/mit-scheme/) 的主页，去下载适用于 Windows 的二进制包，但是从官网给出的信息中发现，目前 MIT/GNU Scheme 的最新版本（12.1），已经不再支持 Windows，

![MIT/GNU Scheme Release status and future plans](../assets/images/posts/2023-09-03/MIT-GNU-Scheme-Release-status-and-future-cb14fc63.png)

所以只能去寻找支持 Windows 的[历史版本](https://ftp.gnu.org/gnu/mit-scheme/stable.pkg/)，经过一番搜寻发现支持 Windows 的 MIT/GNU Scheme 的最新版本为 [9.2 版本](https://ftp.gnu.org/gnu/mit-scheme/stable.pkg/9.2/)，下载相应的  Windows 的二进制包：

![MIT/GNU Scheme 9.2 版本](../assets/images/posts/2023-09-03/mit-scheme-9-2-611463c0.png)

和安装其它软件一样，安装 MIT/GNU Scheme 没什么特别的，下载好 [mit-scheme-9.2-i386-win32.exe](https://ftp.gnu.org/gnu/mit-scheme/stable.pkg/9.2/mit-scheme-9.2-i386-win32.exe) 后，点击安装即可，如果没什么特殊需求直接一直点击 "下一步" 即可完成安装。

## 二、Requested allocation is too large. Try again with a smaller argument to'--heap'.

由于  MIT/GNU Scheme 从  9.2 版本之后，就不再提供对于 Windows  的支持，所以下载完成之后直接运行 MIT/GNU Scheme 会出现错误：

<img src="../assets/images/posts/2023-09-03/GNU-Scheme-terminating-1e3e55b2.png" alt="MIT/GNU Scheme terminating" style="zoom:50%;" />

根据提示，需要利用 `--heap` 对 MIT/GUN Scheme 进行设置：

<img src="../assets/images/posts/2023-09-03/MIT-GNU-Scheme-553f18b9.png" alt="MIT/GNU Scheme 属性" style="zoom:50%;" />

将 "目标(T)" 修改为 `"D:\Program Files (x86)\MIT-GNU Scheme\bin\mit-scheme.exe" --library "D:\Program Files (x86)\MIT-GNU Scheme\lib" --heap 512 --edit`，修改完成后，再次运行 MIT/GNU Scheme，发现原来的错误已经消失，能够成功运行程序。

## 三、Edwin 环境下 / 以命令行交互方式启动 Scheme

默认情况下，MIT GNU Scheme 会以 Edwin 环境下启动 Scheme。其中，Edwin 是一个类似 emacs 的编辑器。

### Edwin 环境下的 Scheme

Edwin 与 命令交互状态之间可以相互切换，详见 [MIT Scheme 的基本使用](https://www.math.pku.edu.cn/teachers/qiuzy/progtech/scheme/mit_scheme.htm) 文档。

下面简单介绍一下 Edwin 环境下的 Scheme 的一些常用指令：

- `C-x z`（表示按 Ctrl-x 后按 z 键）：从 Edwin 中退到 Scheme 的命令交互状态。此时 Edwin 挂起，可用 `(edit)` 唤醒挂起的 Edwin，回到挂起前的状态；
- `C-x c`：停止 Edwin 并回到 Scheme 的命令交互状态；
- `C-x C-z`：停止 Edwin 并挂起 Scheme 系统。再次启动 Scheme 将唤醒挂起的 Scheme 系统，回到挂起前的系统状态；
- `C-x C-c`：停止 Edwin 和 Scheme 系统。

![Edwin 环境下的 MIT/GNU Scheme](../assets/images/posts/2023-09-03/Edwin-scheme-8ab01719.png)

### 命令行交互方式下的 Scheme

接着，简单介绍一下 命令行交互方式下的 Scheme 的一些常用指令：

- 从进入 Edwin：在交互方式下执行 `(edit) ` 或 `(edwin)`，将启动或返回 Edwin；
- 在提示符下键入下面表达式并回车：`1 ]=> (exit)` ，从命令行交互方式下退出。

![命令行交互式下的 MIT/GNU Scheme](../assets/images/posts/2023-09-03/MIT-Scheme-e49892e1.png)

### 将命令行交互方式设置为 Scheme 的默认启动方式

由于比较常用 Scheme 的命令行交互方式，所以下面将其设置为默认启动方式，避免每次切换的麻烦。

设置方式非常简单，只需要将前面 "目标(T)" 中 ：

`"D:\Program Files (x86)\MIT-GNU Scheme\bin\mit-scheme.exe" --library "D:\Program Files (x86)\MIT-GNU Scheme\lib" --heap 512 --edit` 的 `--edit` 去掉即可，

即：将 "目标(T)"  修改为`"D:\Program Files (x86)\MIT-GNU Scheme\bin\mit-scheme.exe" --library "D:\Program Files (x86)\MIT-GNU Scheme\lib" --heap 512`

当然，如果想保留 Edwin 环境下启动 Scheme 的默认方式，也可以将这段指令：

`"D:\Program Files (x86)\MIT-GNU Scheme\bin\mit-scheme.exe" --library "D:\Program Files (x86)\MIT-GNU Scheme\lib" --heap 512`

放到 `.txt` 文本中去，保存之后，修改文件后缀为 `.bat`，每次想以命令行交互方式启动就点击文件即可。

## 参考：

- 安装MIT-Scheme: https://deathking.github.io/yast-cn/contents/chapter1.html
- Linux和Windows下安装MIT Scheme - LunaElf - 博客园: https://www.cnblogs.com/lunaelf/p/5275620.html
- MIT Scheme 的基本使用: https://www.math.pku.edu.cn/teachers/qiuzy/progtech/scheme/mit_scheme.htm
- 介绍 - Scheme 语言简明教程: https://wizardforcel.gitbooks.io/teach-yourself-scheme/content/index.html
- MIT/GNU Scheme - GNU Project - Free Software Foundation --- MIT/GNU 计划 - GNU 项目 - 自由软件基金会: https://www.gnu.org/software/mit-scheme/