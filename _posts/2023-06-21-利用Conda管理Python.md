---
title: 利用Conda管理Python(包+版本+环境)
date: 2023-06-21 10:09:52 +0800
categories:
  - Tools
tags:
  - Python
  - Anaconda
---
## 基本介绍
Python 的管理涉及的以下三个方面：

- 包管理（Package Management）
- **版本管理（Version Management）**
- **环境管理（Environmental Management）**

在前一篇文章当中已经介绍了 Python 包管理的内容在这篇文章中，本来是打算使用 pyenv 进行版本管理，使用 virtualenv 进行环境管理（正好就可以分成三部分内容去介绍），但是由于 pyenv 目前存在问题[^1]，所以最后还是选择了 conda 替代 pyenv。

而对 conda 来说，它的 python **版本管理**和**环境管理**联系比较紧密，不太适合分开来介绍，故临时决定将 python 的版本管理和环境管理放到一起说，也就是这篇文章。
<!--more-->
### 为什么需要 Python 版本管理

Pyhton 版本管理的价值在于将系统需要的 Python 和 开发需要的 Python 分隔开：

- 通常系统里会存在多个版本的 Python，这些 Python 大多都是作为软件依赖，一般不要轻易去动，否则可能会导致一些软件无法正常使用
- 不同的开发需求通常也会用到不同的 Python 版本，当 Python 版本过多时，如果不使用版本管理工具，我们就需要去记录很多命令以区分不同版本的 Python[^2]，而版本管理工具就能简化这些工作

### Python 环境管理的优势

Python 环境管理的价值在于将同一个 Python 版本的不同需求分开，比如：项目 A 和 项目 B 都需要 Python 3.10.11 这个版本，都用到了 requests 包，但是项目 A 需要 requests 2.1，而项目 B 需要 requests 2.2。

通常情况下，同一个 Python 版本是不可能既安装 requests 2.1 又安装 requests 2.2 的，如果没有 Python 环境管理工具，只能在开发项目 A 时，卸载 requests 2.2，安装 requests 2.1；反之，在开发项目 B 时，卸载 requests 2.1，安装 requests 2.2。如果恰好有需要在项目 A 和项目 B 之间进行频繁切换时，可想而之会有多麻烦。

但是借助于 Python 环境管理就可以轻松处理上述情况，对于同一个版本的 Python 的不同需求去创建不同的虚拟环境。

下面即将要介绍的 Python 管理工具 —— conda[^3]，它能够：

- 管理包。查找可供您安装的软件包。安装软件包
- 管理 Python。创建一个具有不同版本 Python 的环境。
- 管理环境。创建环境并在它们之间轻松切换。

总之，通过 conda 这一个工具就可以实现 Python 管理，但是在本篇文章中，还是先重点关注 conda 的版本管理部分。

老规矩，在文章开始之前先简单罗列一下基本环境：

- 操作系统（OS）：Ventura 13.4
- Python 版本：3.11.3
- pip 版本：23.1.2


## Conda 基本介绍

> 任何语言的包、依赖和环境管理 --- Python, R, Ruby, Lua, Scala, Java, JavaScript, C/ C++, FORTRAN。--- 来自官方的介绍

Conda 是一个运行在 Windows、MacOS 和 Linux 上的开源包管理系统和环境管理系统。Conda 可以：

- 快速安装、运行和更新包及其依赖项
- 轻松地在本地计算机上创建、保存、加载和切换环境

它是为 Python 程序创建的，但它可以为任何语言打包和分发软件。

简单总结一下就是 Conda 很好、很强大，使用 Conda 会让你很省心。（人生苦短，我选 "Conda"）

## Conda 的安装、更新和卸载

### 区别：Conda、Miniconda 和 Anaconda

在安装 Conda 之前，我觉得有必要先简单区分一下 Conda、Miniconda 和 Anaconda 这三者的区别[^4]：

- Anaconda：一个非常流行的 Python 发行版，用于科学计算。它包含了 Conda、Python 和超过 150 个科学软件包及其依赖项

- Miniconda：Anaconda 的轻量级版本，只包含了 Python 和 Conda，以及它们的依赖项
- Conda：一个开源的**包管理**系统和**环境管理**系统，用于安装多种语言的软件包

如果用 Linux 操作系统来比喻的话，Conda 相当于 Linus Torvalds 最初写的最原始的 Linux 内核，而 Miniconda 就相当于 min Linux，最后是 Anaconda 就相当于 Linux 的各种发行版，比如：Ubuntu，CentOS等等。
<img src="../assets/images/posts/2023-06-21/Obsidian202306181716277-fc43919b.png" alt="image-20230618171658097" style="zoom: 67%;" />

### 安装 Miniconda

根据不同的需求，从 Anaconda 和 Miniconda 二者选其一进行，进行安装即可：

- 图方便，省事，想一步到位就可以选 Anaconda
- 想要小巧，灵活，快速就选 Miniconda

这里，选择 Miniconda 进行安装，还是通过 homebrew 进行安装：

1. 可以先尝试简单搜索一下

   ```bash
   $ brew search conda
   ==> Formulae
   conda-lock                         conan                              conman
   conda-zsh-completion               confd
   
   ==> Casks
   anaconda                           miniconda                          pycharm-with-anaconda-plugin
   coda                               pycharm-ce-with-anaconda-plugin
   ```

   发现在 Casks 中存在我们想要安装的 miniconda。

2. 再进一步查看 miniconda 的相关信息：

   ```bash
   $ brew info miniconda
   ==> miniconda: py310_23.3.1-0 (auto_updates)
   https://docs.conda.io/en/latest/miniconda.html
   Not installed
   From: https://mirrors.ustc.edu.cn/homebrew-cask.git
   ==> Name
   Miniconda
   ==> Description
   Minimal installer for conda
   ==> Artifacts
   Miniconda3-py310_23.3.1-0-MacOSX-x86_64.sh (Installer)
   /usr/local/Caskroom/miniconda/base/condabin/conda (Binary)
   ==> Caveats
   Please run the following to setup your shell:
     conda init "$(basename "${SHELL}")"
   ==> Analytics
   install: 11,497 (30 days), 11,875 (90 days), 11,875 (365 days)
   ```

3. 安装 miniconda

   ```bash
   $ brew install miniconda
   ```

4. 根据第 2 步（Caveats）提示的信息，需要对 conda 进行初始化：

   ```bash
   $ conda init "$(basename "${SHELL}")"
   no change     /usr/local/Caskroom/miniconda/base/condabin/conda
   no change     /usr/local/Caskroom/miniconda/base/bin/conda
   no change     /usr/local/Caskroom/miniconda/base/bin/conda-env
   no change     /usr/local/Caskroom/miniconda/base/bin/activate
   no change     /usr/local/Caskroom/miniconda/base/bin/deactivate
   no change     /usr/local/Caskroom/miniconda/base/etc/profile.d/conda.sh
   no change     /usr/local/Caskroom/miniconda/base/etc/fish/conf.d/conda.fish
   no change     /usr/local/Caskroom/miniconda/base/shell/condabin/Conda.psm1
   modified      /usr/local/Caskroom/miniconda/base/shell/condabin/conda-hook.ps1
   no change     /usr/local/Caskroom/miniconda/base/lib/python3.10/site-packages/xontrib/conda.xsh
   no change     /usr/local/Caskroom/miniconda/base/etc/profile.d/conda.csh
   modified      /Users/borne/.zshrc
   
   ==> For changes to take effect, close and re-open your current shell. <==
   ```

   可以看到初始化其实是分别修改了两个文件：`conda-hook.ps1` 和 `.zshrc`，简单看看 `.zshrc` 文件的变化：

   ```bash
   $ cat /Users/borne/.zshrc | grep -i conda
   # >>> conda initialize >>>
   # !! Contents within this block are managed by 'conda init' !!
   __conda_setup="$('/usr/local/Caskroom/miniconda/base/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
       eval "$__conda_setup"
       if [ -f "/usr/local/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]; then
           . "/usr/local/Caskroom/miniconda/base/etc/profile.d/conda.sh"
           export PATH="/usr/local/Caskroom/miniconda/base/bin:$PATH"
   unset __conda_setup
   # <<< conda initialize <<<
   ```

   其实就是做了一些环境变量的设置，比如：将 miniconda 的 `bin` 文件夹加入到 `PATH` 环境变量。

5. 按照提示，需要重启当前 `shell` 让改变生效，重启之后，执行下面命令，测试是否按照成功：

   ```bash
   $ conda list
   # Name                    Version                   Build  Channel
   boltons                   23.0.0          py310hecd8cb5_0
   brotlipy                  0.7.0           py310hca72f7f_1002
   bzip2                     1.0.8                h1de35cc_0
   ...												...										...
   ```

   成功显示已安装软件包的列表，说明安装成功！

### 更新 Miniconda

对 Miniconda 进行更新，应该有下面两种方式：

1. 利用 conda 对 Miniconda 进行更新

   ```bash
   $ conda update conda
   ```

2. 借助 homebrew 进行更新，因为我们是通过 homebrew 安装的 miniconda

   ```bash
   $ brew upgrade miniconda
   ```

### 卸载 Miniconda

卸载 Miniconda 的话，其实非常简单，主要分为以下几个步骤：

1. 删除 Miniconda 软件

由于我们是通过 homebrew 进行安装的，卸载的话自然也通过 homebrew：

```bash
$ brew uninstall miniconda
```

2. 删除环境变量 `PATH` 中的 Miniconda 目录

主要就是删除前面提到的 conda 初始化时在 `.zshrc` 文件中添加的那部分

```bash
# >>> conda initialize >>>
......
# <<< conda initialize <<<
```

3. 删除与 Miniconda 相关的配置文件

主要包括以下可能已在主目录中创建的隐藏文件和文件夹：

- `.condarc` 文件
- `.conda` 目录
- `.continuum` 目录

可以通过运行下面的命令进行删除：

```bash
$ rm -rf ~/.condarc ~/.conda ~/.continuum
```

## conda 管理环境

利用 Conda 可以创建单独的环境，其中包含不与其他环境交互的文件、包及其依赖项。

当开始使用 conda 时，已经默认创建了一个 `base` 的环境，但是，如果不想将程序放入这个基础环境（`base`）中，可以选择创建单独的环境以使程序彼此隔离。

### 查看所有环境的列表

借助 `conda info` 命令可以查看与 conda 相关的一些信息，配合 `-e, --envs` 选项，可以查看所有环境的列表

```bash
$ conda info --envs
# conda environments:
#
base                  *  /usr/local/Caskroom/miniconda/base
```

这个展示结果和我们前面介绍的情况相同，conda 会默认创建一个 `base` 环境。

### 创建一个新环境

通过 `conda create` 命令可以创建一个新环境，利用 `--name` 选项，可以为新环境命名，比如：创建一个新环境 `test`

```bash
$ conda create --name test
```

这时候，再查看所有环境的列表：

```bash
$ conda info --envs
# conda environments:
#
base                  *  /usr/local/Caskroom/miniconda/base
test                     /usr/local/Caskroom/miniconda/base/envs/test
```

可以看到这时的环境中就出现了我们之前创建的 `test` 环境，其中，`*` 表示当前处在哪个环境中。

### 使用或“激活”新环境

要使用或"激活"新环境，需要使用下面的命令，比如：激活 `test` 环境：

```bash
$ conda activate test
```

- 如果直接使用 `conda activate` （不带环境名），会默认切回 `base` 环境。

再次查询所有环境的列表：

```bash
$ conda info --envs
# conda environments:
#
base                     /usr/local/Caskroom/miniconda/base
test                  *  /usr/local/Caskroom/miniconda/base/envs/test
```

观察 `*` 的变化可以发现，当前已经成功切换到 `test` 环境。

> Notes：`conda activate` 仅适用于 conda 4.6 及更高版本

### 删除一个环境

删除环境需要用到 `conda remove` 命令：

```bash
$ conda remove --name ENVIRONMENT --all
```

比如：删除前面创建的 test 环境

```bash
$ conda remove --name test --all
```

查询所有环境的列表，看是否删除成功：

```bash
# conda environments:
#
base                  *  /usr/local/Caskroom/miniconda/base
```

发现已经成功删除，只剩下 base 环境。

## conda 管理 Python 版本

在前面创建新环境时，conda 会默认安装在下载和安装 Anaconda/Miniconda 时使用的相同 Python 版本。

如果要使用不同版本的 Python，例如 Python 3.10.11，只需创建一个新环境并指定所需的 Python 版本即可。

### 创建环境时指定 Python 版本

为了方便后面比较，先查询一下 `base` 环境下的 Python 版本：

```bash
$ conda activate && Python -V
Python 3.10.11
```

然后创建一个名为 `test` 的包含 Python 3.7.1 的新环境：

```bash
$ conda create --name test python=3.7.1
```

验证一下是否成功，切换到 test 环境，查询 Python 版本：

```bash
$ conda activate test && Python -V
Python 3.7.1
```

从展示的结果来看已经成功，test 环境下的 Python 版本为我们指定的 3.7.1 版本。

## Conda 配置

conda 配置文件 `.condarc` 是一个可选的运行时配置文件[^5]，它允许高级用户配置 conda 的各个方面，例如它搜索包的渠道、代理设置和环境目录。

`.condarc` 文件可以更改许多参数，包括：

- conda 在哪里寻找包
- conda 是否以及如何使用代理服务器
- conda 列出已知环境的位置
- 是否使用当前激活的环境名称更新 Bash 提示符
- 用户构建的包是否应该上传到 Anaconda.org
- 在新环境中包含哪些默认包或功能

### 创建和编辑配置文件

默认情况下不包含 `.condarc` 文件，但它会在第一次运行 `conda config` 命令时自动在主目录(`~`)中创建。

可以通过 `conda config` 命令创建或修改 .condarc 文件，也可以直接在 Home 目录或者根目录直接创建或者编辑 `.condarc` 文件，需要注意的是，`.condarc` 配置文件遵循简单的 YAML 语法。

可以通过 `conda info` 命令来查找有关 `.condarc` 文件的信息：

```bash
$ conda info | grep -i config
user config file : /Users/borne/.condarc
populated config files :
```

### 配置文件的搜索路径

Conda 在以下位置查找 `.condarc` 文件：

```python
if on_win:
    SEARCH_PATH = (
        "C:/ProgramData/conda/.condarc",
        "C:/ProgramData/conda/condarc",
        "C:/ProgramData/conda/condarc.d",
    )
else:
    SEARCH_PATH = (
        "/etc/conda/.condarc",
        "/etc/conda/condarc",
        "/etc/conda/condarc.d/",
        "/var/lib/conda/.condarc",
        "/var/lib/conda/condarc",
        "/var/lib/conda/condarc.d/",
    )

SEARCH_PATH += (
    "$CONDA_ROOT/.condarc",
    "$CONDA_ROOT/condarc",
    "$CONDA_ROOT/condarc.d/",
    "$XDG_CONFIG_HOME/conda/.condarc",
    "$XDG_CONFIG_HOME/conda/condarc",
    "$XDG_CONFIG_HOME/conda/condarc.d/",
    "~/.config/conda/.condarc",
    "~/.config/conda/condarc",
    "~/.config/conda/condarc.d/",
    "~/.conda/.condarc",
    "~/.conda/condarc",
    "~/.conda/condarc.d/",
    "~/.condarc",
    "$CONDA_PREFIX/.condarc",
    "$CONDA_PREFIX/condarc",
    "$CONDA_PREFIX/condarc.d/",
    "$CONDARC",
)

```

其中，需要特别说明的是：

- `XDG_CONFIG_HOME` 是根据 XDG 基本目录规范 (XDGBDS) 定义的用户特定配置文件的存储路径
- `CONDA_ROOT` 是基本 conda 安装的路径
- `CONDA_PREFIX` 是当前活动环境的路径

### 配置间的优先级

当配置之间出现冲突时，采用以下策略：

- Lists - merge
- Dictionaries - merge
- Primitive - clobber

构建 conda 配置的优先级如下所示，从左到右优先级一次递增：

- Config files(by parse order)：配置文件按照解析的顺序，优先级从高到低

  比如：`"~/.config/conda/.condarc"` 优先级高于 `"~/.conda/.condarc"`

- Config files specified by `$CONDARC`：`$CONDARC` 指向的配置文件优先级高于其他配置文件

- Command line parameter：通过 `conda config --set` 命令进行配置的优先级高于配置文件

- Environment variables：通过环境变量进行配置的优先级最高

![Conda Config Precedence](../assets/images/posts/2023-06-21/Obsidian202306201041501-0f8861d0.png)

### 常用配置

#### 配置镜像源

以[清华的镜像源](https://mirrors.tuna.tsinghua.edu.cn/help/anaconda/)为例：

```yaml
channels:
  - defaults # 使用 defaults 自动包含所有默认频道
# 在显示要下载的内容和 conda list 时显示频道 URL
show_channel_urls: true
# 通常默认通道指向 repo.anaconda.com 存储库中的几个通道，但如果定义了 default_channels ，它会设置新的默认通道列表
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  msys2: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  bioconda: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  menpo: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch-lts: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  simpleitk: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
```

> Notes：如果要为单个环境选择通道，请将 .condarc 文件放在该环境的根目录中。

#### 自动更新 conda

当 `True` 时，只要用户在根环境中更新或安装包，conda 就会更新自身；当 `False` 时，仅当用户手动发出 `conda update` 命令时，conda 才会更新自身（默认值为 `True`）：

```yaml
auto_update_conda: False
```

#### Always yes

每当要求继续时选择 `yes` 选项，例如：在安装时，与在命令行中使用 `--yes` 标志相同（默认值为 `False`）：

```yaml
always_yes: True
```

#### 更改命令提示符 (changeps1)

使用 conda activate 时，将命令提示符从 $PS1 更改为包括已激活的环境（默认值为 True）：

```yaml
changeps1: False
```

#### 配置代理服务器

默认情况下，代理设置是从 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量或系统中提取的。在这里设置它们会覆盖默认值：

```yaml
proxy_servers:
    http: http://user:pass@corp.com:8080
    https: https://user:pass@corp.com:8080
```

### 其他的配置

还有一些可能会用到的配置（考虑到文章篇幅，就只简单罗列不详细阐述了，感兴趣的详见[这里](https://docs.conda.io/projects/conda/en/stable/user-guide/configuration/use-condarc.html#overview)）：

- 设置 channel 别名（ `channel_alias` ）
- 始终默认添加包 ( `create_default_packages` )
- 指定环境目录（ `envs_dirs` ）
- 指定包目录 ( `pkgs_dirs` )
- 禁用依赖项更新 ( `update_dependencies` )

### 配置的一个 demo

下面是官方[^6]给的一个配置的 `demo`：

```yaml
# This is a sample .condarc file.
# It adds the r Anaconda.org channel and enables
# the show_channel_urls option.

# channel locations. These override conda defaults, i.e., conda will
# search *only* the channels listed here, in the order given.
# Use "defaults" to automatically include all default channels.
# Non-url channels will be interpreted as Anaconda.org usernames
# (this can be changed by modifying the channel_alias key; see below).
# The default is just 'defaults'.
channels:
  - r
  - defaults

# Show channel URLs when displaying what is going to be downloaded
# and in 'conda list'. The default is False.
show_channel_urls: True

# For more information about this file see:
# https://conda.io/docs/user-guide/configuration/use-condarc.html
```

一个比较完整的配置文件可以看[这里](https://docs.conda.io/projects/conda/en/stable/configuration.html)。

## Conda 包管理

虽然之前的文章介绍过 `pip` 包管理，但是 `Conda` 也可以非常方便的进行包管理，并且和 `pip` 非常相似，这里也简单介绍一下。

### 检索 Package

想要安装 `beautifulsoup4`，先检测是否可从 Anaconda 存储库中获得：

```bash
$ conda search beautifulsoup4
```

Conda 会在 Anaconda 存储库中显示所有具有该名称的包的列表，因此可以知道它是否可安装。

### 安装 Package

将 `beautifulsoup4` 安装到当前环境中：

```bash
$ conda install beautifulsoup4
```

查看新安装的包是否在这个环境中:

```bash
$ conda list | grep -i beautifulsoup4
```

### 卸载 Package

将 `beautifulsoup4` 从当前环境中卸载：

```bash
$ conda remove beautifulsoup4
```

## Conda 速查表

在文章的最后，简单罗列一些 Conda 的常用命令[^6]

### Quick Start

![QUICK START](../assets/images/posts/2023-06-21/Obsidian202306201743570-20afa95f.png)

### Channels and Packages

![CHANNELS AND PACKAGES](../assets/images/posts/2023-06-21/Obsidian202306201744337-12463b6c.png)

### Working with Conda Environments

![WORKING WITH CONDA ENVIRONMENTS](../assets/images/posts/2023-06-21/Obsidian202306201745277-deba2907.png)

### Environment Management

![ENVIRONMENT MANAGEMENT](../assets/images/posts/2023-06-21/Obsidian202306201746760-64ebf7c0.png)

### Exporting Environments

![EXPORTING ENVIRONMENTS](../assets/images/posts/2023-06-21/Obsidian202306201748007-84e6cefd.png)

### Importing Environments

![IMPORTING ENVIRONMENTS](../assets/images/posts/2023-06-21/Obsidian202306201751023-6c6d491b.png)

### Additional Hints

![ADDITIONAL HINTS](../assets/images/posts/2023-06-21/Obsidian202306201752891-fdab22f2.png)

## 参考

[^1]:本来是想使用另一个管理工具 —— pyenv 的，奈何 pyenv 对于 macOS（新版本）以及 Windows 的适配并不是想象中的好，所以目前就只能用 conda 来替代，等之后主力 OS 换到 Linux 下再进行尝试吧

[^2]:很多时候，光是一个 `pip` 和 `pip3` 都让人傻傻分不清了，更别说再多

[^3]:Conda 官方文档：https://docs.conda.io/projects/conda/en/stable/index.html

[^4]:conda、miniconda、anaconda之间有什么关系？- 知乎：https://www.zhihu.com/question/369468216

[^5]:一个冷知识：文件 `.condarc` 中的 `rc` 代表 `run commands`，详见：https://en.wikipedia.org/wiki/RUNCOM

[^6]:Sample .condarc file — conda documentation：https://docs.conda.io/projects/conda/en/stable/user-guide/configuration/sample-condarc.html

[^7]:Cheat sheet — conda documentation：https://docs.conda.io/projects/conda/en/stable/user-guide/cheatsheet.html