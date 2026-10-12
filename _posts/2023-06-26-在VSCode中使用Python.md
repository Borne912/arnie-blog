---
title: 在 VS Code 中使用 Python
date: 2023-06-26 11:05:25 +0800
categories:
  - Tools
tags:
  - Python
  - VSCode
---
## 基本介绍

在之前的文章当中介绍了 Python 管理，本文主要在之前文章的基础上介绍如何在 Visual Studio Code 中使用 Python 3 创建、运行和调试 Python 程序以及如何使用虚拟环境、使用包等等[^1]。

在文章开始前，先简单罗列一下本文会用到的一些软件/工具：

- Python 3[^2]
- VS Code（版本: 1.79.1）
- VS Code Python extension（Microsoft Python）[^3]
<!--more-->
## 安装 Python 插件

在 VS Code 中使用 Python，需要使用到 **Microsoft Python** 插件。该插件利用了 VS Code 来提供了下面这些功能：

- 自动补全和智能感知
- 检测、调试和单元测试
- 在Python环境(包括虚拟环境和 conda 环境)之间轻松切换

在 VS Code 中安装插件非常的简单，只需要打开 VS Code，选择 "**扩展**"，在 "**扩展：商店**" 的搜索栏中输入 "Python"，选择相应的插件，点击 "安装"，即可：

<img src="../assets/images/posts/2023-06-26/Obsidian202306231457428-cc8d7305.png" alt="安装 Python 插件" style="zoom: 67%;" />

安装完成插件之后，通常需要重启 VS Code，以启用安装的插件：

<img src="../assets/images/posts/2023-06-26/Obsidian202306231502662-fbeb5b1c.png" alt="重启 VS Code" style="zoom:67%;" />

重启 VS Code 之后，打开**命令面板**（⇧⌘P），键入 "**Python**"，可以看到命令面板出现了一些下拉选项，说明插件安装成功：

![Python 插件](../assets/images/posts/2023-06-26/Obsidian202306231509330-b31b5bb6.png)

## 使用 Python 的常规流程

### Step 1：在工作区文件夹中启动 VS Code

通过在文件夹中启动 VS Code，该文件夹将成为“工作区”。

使用命令提示符或终端，创建一个名为 `hello` 的空文件夹，导航到该文件夹，然后通过输入以下命令打开该文件夹 ( `.` ) 中的 VS Code ( `code` )：

```bash
mkdir hello
cd hello
code .
```

>Notes: 使用 `code` 命令前请确保已经将 VS Code 的可以执行路径添加到环境变量当中！

### Step 2：创建虚拟环境

Python 开发者的最佳实践是使用特定于项目的 `virtual environment` 。一旦激活该环境，安装的任何软件包都将与其他环境（包括全局解释器环境）隔离，从而减少因软件包版本冲突而可能引起的许多复杂情况[^4]。

可以使用 Venv 或 Conda 和 Python 在 VS Code 中创建非全局环境：创建环境。

打开**命令面板** ( `⇧⌘P` )，开始键入 **Python: Create Environment** 命令进行搜索，然后选择该命令。该命令显示环境类型列表，Venv 或 Conda。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231515462-bed24438.png" alt="Python: Create Environment" style="zoom: 50%;" />

下面将以 Conda 为例，展示创建虚拟环境的过程，Venv 与 Conda 的过程基本一样：

对于显示环境类型列表，Venv 或 Conda，选择 Conda

<img src="../assets/images/posts/2023-06-26/Obsidian202306231518409-7efadaeb.png" alt="环境类型列表" style="zoom:50%;" />

然后该命令会显示可用于项目的解释器列表，选择需要的解释器

<img src="../assets/images/posts/2023-06-26/Obsidian202306231521846-fabe6e42.png" alt="解释器列表" style="zoom:50%;" />

选择解释器后，将显示一条通知，显示环境创建的进度

<img src="../assets/images/posts/2023-06-26/Obsidian202306231523107-cca97d6f.png" alt="image-20230623152357056" style="zoom:50%;" />

并且环境文件夹 ( `/.conda` ) 将出现在工作区中

<img src="../assets/images/posts/2023-06-26/Obsidian202306231526411-97372551.png" alt=".conda 文件夹" style="zoom:50%;" />

### Step 3：创建 Python 源文件

从文件资源管理器工具栏中，选择 `hello` 文件夹上的新建文件按钮：

<img src="../assets/images/posts/2023-06-26/Obsidian202306231536552-e04459ed.png" alt="新建 hello 文件" style="zoom:50%;" />

将文件命名为 `hello.py` ，VS Code 会自动在编辑器中打开它：

<img src="../assets/images/posts/2023-06-26/Obsidian202306231538824-8382bf90.png" alt="打开 hello 文件夹" style="zoom:50%;" />

通过使用 `.py` 文件扩展名，告诉 VS Code 将此文件解释为 Python 程序，以便它使用 Python 扩展名和选定的解释器评估内容。

> Notes：文件资源管理器工具栏还允许在工作区中创建文件夹以更好地组织代码。可以使用新建文件夹按钮快速创建文件夹。

下面简单以一个 demo 举例，现在工作区中有一个代码文件，在 `hello.py` 中输入以下源代码：

```python
msg = "Roll a dice"
print(msg)
```

当开始输入 `print` 时，请注意 **IntelliSense** 如何显示 "自动补全（Auto-completion）" 选项

<img src="../assets/images/posts/2023-06-26/Obsidian202306231548857-07b81713.png" alt="IntelliSense" style="zoom: 33%;" />

**IntelliSense** 和 "自动补全" 适用于：

- 标准 Python 模块
- 安装到所选 Python 解释器环境中的其他包
- 对象类型上可用的方法

例如，由于 `msg` 变量包含字符串，因此当您键入 `msg.` 时，**IntelliSense** 会提供字符串方法：

<img src="../assets/images/posts/2023-06-26/Obsidian202306231553899-fcf276b9.png" alt="对象类型上可用的方法" style="zoom: 33%;" />

最后，保存文件 ( `⌘S` )。此时，就已准备好在 VS Code 中运行第一个 Python 文件。

### Step 4：运行 hello.py

单击编辑器右上角的 **Run Python File in Terminal** 运行按钮。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231603244-dfcdaf3d.png" alt="Run Python File in Terminal" style="zoom:50%;" />

该按钮会打开一个终端面板，其中会自动激活 Python 解释器，然后运行 `python3 hello.py` (macOS/Linux) 或 `python hello.py` (Windows)：

<img src="../assets/images/posts/2023-06-26/Obsidian202306231606957-5c0c54f3.png" alt="终端面板运行 Python" style="zoom:50%;" />

还可以通过其他三种方式在 VS Code 中运行 Python 代码：

1. 右键单击编辑器窗口中的任意位置，然后选择 **Run > Python File in Terminal**（这会自动保存文件）
   ![](../assets/images/posts/2023-06-26/Obsidian202306231610631-2708195f.png)

2. 选择一行或多行，然后按 `Shift+Enter` 或右键单击并选择 **在 Python 终端中运行选择/行**。该命令对于仅测试文件的一部分非常方便

3. 从命令面板 (`⇧⌘P`) 中，选择 **Python: Start REPL** 命令为当前选择的 Python 解释器打开 REPL 终端。在 REPL 中，您可以一次输入并运行一行代码

### Step 5：配置并运行调试器

下面让我们尝试调试我们的 Hello World 程序。

首先，通过将光标放在 `print` 调用上并按 `F9`，在 `hello.py` 的第 2 行设置断点。或者，单击编辑器左侧的行号旁边的装订线。设置断点时，装订线中会出现一个红色圆圈。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231625206-4f874dc7.png" alt="Setting a breakpoint in hello.py" style="zoom:67%;" />

接下来，要初始化调试器，请按 `F5`。由于这是第一次调试此文件，配置菜单将从命令面板打开，允许为打开的文件选择想要的调试配置类型。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231628860-9966982c.png" alt="Debug configurations after launch.json is created" style="zoom: 33%;" />

> Notes：VS Code 的所有各种配置都使用 JSON 文件，launch.json 是包含调试配置的文件的标准名称。

选择 **Python File**，这是使用当前选择的 Python 解释器运行编辑器中显示的当前文件的配置。

通过单击编辑器上运行按钮旁边的向下箭头并在终端中选择调试 Python 文件来启动调试器。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231632078-fd3f2373.png" alt="Using the debug Python file in terminal button" style="zoom: 50%;" />

调试器将在文件断点的第一行停止。当前行在左边距中用黄色箭头指示。如果此时检查局部变量窗口，将看到现在已定义的 msg 变量出现在局部窗格中。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231634278-54b044b2.png" alt="Debugging step 2 - variable defined" style="zoom: 50%;" />

调试工具栏出现在顶部，从左到右有以下命令：继续 (`F5`)、跳过 (`F10`)、进入 (`F11`)、退出 (`⇧F11`)、重新启动 (`⇧⌘F5`) 和停止 (`⇧F5`）。

<img src="../assets/images/posts/2023-06-26/Obsidian202306231637136-65168324.png" alt="Debugging toolbar"  />

状态栏也会改变颜色（在许多主题中为橙色）以指示您处于调试模式。 **Python 调试控制台**也会自动出现在右下面板中，以显示正在运行的命令以及程序输出。要继续运行程序，请选择调试工具栏 (`F5`) 上的继续命令。调试器将程序运行到最后。

> Tips：还可以通过将鼠标悬停在代码上来查看调试信息，例如：变量 `msg`，将鼠标悬停在变量上将在变量上方的框中显示字符串 `Roll a dice! `

还可以在调试控制台中使用变量（如果没有看到它，请在 VS Code 的右下方区域选择**调试控制台**，或者从 ... 菜单中选择它）然后尝试在控制台底部的 > 提示符处输入以下行：

```bash
msg
msg.capitalize()
msg.split()
```

<img src="../assets/images/posts/2023-06-26/Obsidian202306231643679-8f0745e8.png" alt="Debugging step 3 - using the debug console" style="zoom: 67%;" />

再次选择工具栏上的蓝色继续按钮（或按 `F5`）以运行程序直至完成。如果切换回 Python 调试控制台，`Roll a dice!` 会出现在 Python 调试控制台中，一旦程序完成，VS Code 就会退出调试模式。

### Step 6：安装和使用包

在 Python 中，包是获取任意数量的有用代码库（通常来自 `PyPI`）的方式，这些代码库为程序提供附加功能。比如：使用 `numpy` 包来生成随机数。

返回资源管理器视图（左侧最上面的图标，显示文件），打开 `hello.py` ，然后粘贴以下源代码，并运行调试该文件：

```python
import numpy as np

msg = "Roll a dice"
print(msg)

print(np.random.randint(1,9))
```

这时应该看到消息 "**ModuleNotFoundError: No module named 'numpy'**"。此消息表明所需的包在当前解释器中不可用。

要安装 numpy 包，请停止调试器并使用命令面板运行终端：创建新终端 (⌃⇧\`)，并在打开的终端中通过 `conda` 命令安装相应的包：

```bash
conda install numpy
```

安装完成后，再运行程序，发现成功输出随机数！

## Python 调试

通过对调试配置文件进行修改，可以实现对调试过程中某些行为进行个性化的设置[^5]！
### 初始化配置

配置文件通常会直接决定 VS Code 在调试会话期间的行为[^6]。

有关调试的配置在 `launch.json` 文件中进行定义，该文件通常储存在工作区的 `.vscode` 文件夹中。

> Notes：要更改调试配置，代码必须存储在一个文件夹中！

要初始化调试配置，首先选择侧栏中的 "运行和调试(⇧⌘D)" 视图：

![Run icon](../assets/images/posts/2023-06-26/Obsidian202306251044898-a43f25c9.png)

如果当前尚未定义任何配置，将看到一个用于运行和调试的按钮以及一个用于创建配置 (`launch.json`) 文件的链接：

<img src="../assets/images/posts/2023-06-26/Obsidian202306251045931-b08e1e17.png" alt="Debug toolbar settings command" style="zoom: 58%;" />

要使用 Python 配置生成 `launch.json` 文件，需要执行以下步骤：

1. 选择 **create a launch.json file** 的链接（如上图所示），或者打开命令面板（`⇧⌘P`）,键入 "Debug: Add Configuration"，选择并回车

	![](../assets/images/posts/2023-06-26/Obsidian202306251059764-cde3ffaf.png)

2. 配置菜单将从命令面板中打开，允许为打开的文件选择所需的调试配置类型。现在，在出现的 "Select a debug configuration" 菜单中，选择 "Python File"

   ![](../assets/images/posts/2023-06-26/Obsidian202306251051522-585c26b8.png)

   > Notes：在不存在配置的情况下，通过调试面板、`F5` 或 **运行 > 开始调试** 启动调试会话也会显示调试配置菜单，但不会创建 `launch.json` 文件（就是前一节中，"Step 5：配置并运行调试器"所展示的那样，并不会创建 `launch.json` 文件）

3. 然后，Python 扩展创建并打开一个 `launch.json` 文件，其中包含基于之前选择的预定义配置（即："Python File"）。可以修改配置（例如添加参数），也可以添加自定义配置

### 额外的配置

默认情况下，VS Code 仅显示 Python 扩展提供的最常见配置。可以使用列表中显示的 "Add Configuration" 命令和 `launch.json` 编辑器来选择要包含在 `launch.json` 中的其他配置。当使用该命令时，VS Code 会提示和提供所有可用配置的列表（请务必选择 Python 选项）：

<img src="../assets/images/posts/2023-06-26/Obsidian202306251104814-4e328c14.png" alt="Adding a new Python debugging configuration" style="zoom: 67%;" />

选择 "Attach using Process ID" 会产生以下结果：

<img src="../assets/images/posts/2023-06-26/Obsidian202306251107673-f9b7437a.png" alt="Added a configuration" style="zoom:67%;" />

调试期间，状态栏显示当前配置和当前调试解释器。选择配置会弹出一个列表，可以从中选择不同的配置：

<img src="../assets/images/posts/2023-06-26/Obsidian202306251108172-9b17e059.png" alt="Debugging Status Bar" style="zoom:67%;" />

默认情况下，调试器使用为工作区选择的相同解释器，就像 VS Code 的 Python 扩展的其他功能一样。要专门使用不同的解释器进行调试，请为适用的调试器配置设置 `launch.json` 中 `python` 的值。或者，在状态栏上选择指定的解释器以选择其他解释器。

### 设置配置选项

当首次创建 `launch.json` 时，有两种标准配置可以在集成终端（VS Code 内部）或外部终端（VS Code 外部）的编辑器中运行活动文件：

```json
{
  "configurations": [
    {
      "name": "Python: Current File (Integrated Terminal)",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Current File (External Terminal)",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "externalTerminal"
    }
  ]
}
```

下面会对比较常见的 `launch.json` 文件的配置项进行一些简单的说明。

#### `name`：提供 VS Code 下拉列表中显示的调试配置的名称

<img src="../assets/images/posts/2023-06-26/Obsidian202306251118025-976299f5.png" alt="调试配置的名称" style="zoom: 40%;" />

#### `type`：标识要使用的调试器类型

对于 Python 代码，将此设置保留为 `python`

#### `request`：指定开始调试的模式

常见的调试模式有以下两种：

- `launch` ：在 `program` 中指定的文件上启动调试器
- `attach` ：将调试器附加到已经运行的进程，在远程调试中会使用到

#### `program`：提供 python 程序的入口模块（启动文件）的绝对路径

值 `${file}` 通常在默认配置中使用，使用编辑器中当前活动的文件。

通过指定特定的启动文件，无论打开哪些文件，始终可以确保使用相同的入口点启动程序。例如：

```json
"program": "/Users/Me/Projects/PokemonGo-Bot/pokemongo_bot/event_handlers/__init__.py",
```

还可以依赖工作空间根目录的相对路径（ `${workspaceFolder}` ）

例如，如果根是 `/Users/Me/Projects/PokemonGo-Bot`，那么可以使用以下示例：

```json
"program": "${workspaceFolder}/pokemongo_bot/event_handlers/__init__.py",
```

#### `module`：提供指定要调试的模块名称的功能

类似于在命令行运行时的 -m 参数。

#### `python`：指向用于调试的 Python 解释器的完整路径

如果未指定，此设置默认为为您的工作区选择的解释器，这相当于使用值 `${command:python.interpreterPath}` 。

要使用不同的解释器，请在调试配置的 python 属性中指定其路径。

或者，可以使用在每个平台上定义的自定义环境变量来包含要使用的 Python 解释器的完整路径，以便不需要其他文件夹路径。

如果需要将参数传递给 Python 解释器，可以使用 `pythonArgs` 属性.

#### `pythonArgs`：向 Python 解释器传递参数

使用语法 `"pythonArgs": ["<arg 1>", "<arg 2>",...]` 指定要传递给 Python 解释器的参数。

#### `args`：指定要传递给 Python 程序的参数

由空格分隔的参数字符串的每个元素都应包含在引号内，例如：

```json
"args": ["--quiet", "--norepeat", "--port", "1593"],
```

#### `console`：指定在不修改 `redirectOutput` 的默认值的情况下如何显示程序输出

具体有以下三种选择：

- `"internalConsole"`：VS Code 调试控制台。如果 `redirectOutput` 设置为 `False`，则不显示任何输出
- `"integratedTerminal"` (default) ：VS Code 集成终端。如果 `redirectOutput` 设置为 `True`，输出也会显示在调试控制台中
- `"externalTerminal"`：单独的控制台窗口。如果 `redirectOutput` 设置为 `True`，输出也会显示在调试控制台中

#### `purpose`：对 "运行" 按钮进行配置

将 `purpose` 选项设置为 `debug-test` ，定义在 VS Code 中调试测试时应使用该配置。

但是，将该选项设置为 `debug-in-terminal` 定义了仅在访问编辑器右上角的 "运行 Python 文件" 按钮时才应使用该配置（无论该按钮提供的是 "运行 Python 文件" 还是 "调试 Python 文件" 选项）。

> Notes：purpose 选项不能用于通过 `F5` 或 "运行 > 开始调试" 来启动调试器。

#### `autoReload`：修改后重加载

允许在调试器执行到达断点后对代码进行更改时自动重新加载调试器。要启用此功能，请设置 `{"enable": true}` ，如以下代码所示：

```json
{
  "name": "Python: Current File",
  "type": "python",
  "request": "launch",
  "program": "${file}",
  "console": "integratedTerminal",
  "autoReload": {
    "enable": true
  }
}
```

> Notes：当调试器执行重新加载时，导入时运行的代码可能会再次执行。为了避免这种情况，请尝试在模块中仅使用导入（imports）、常量（constants）和定义（definitions），并将所有代码放入函数中。或者，您也可以使用 `if __name__=="__main__"` 检查。

#### `cwd`：指定调试器的当前工作目录

这是代码中使用的任何相对路径的基本文件夹。如果省略，则默认为 `${workspaceFolder}` （在 VS Code 中打开的文件夹）

#### `redirectOutput`：重定向输出

当设置为 `true` （`internalConsole` 的默认值）时，使调试器将程序的所有输出打印到 VS Code 调试输出窗口中。

如果设置为 `false` （`integratedTerminal` 和 `externalTerminal` 的默认值），程序输出不会显示在调试器输出窗口中。

使用 `"console": "integratedTerminal"` 或 `"console": "externalTerminal"` 时通常会禁用此选项，因为无需在调试控制台中复制输出。

#### `justMyCode`：仅限调试用户编写的代码

当省略或设置为 `true` （默认值）时，仅限调试用户编写的代码。设置为 `false` 还可以启用标准库函数的调试。

#### `env`：设置除系统环境变量之外的可选环境变量

为调试器进程设置除调试器始终继承的系统环境变量之外的可选环境变量。这些变量的值必须以字符串形式输入。

#### `envFile`：包含环境变量定义的文件的可选路径

## 后记

对于 VS Code 也好，PyCharm 也罢，这类工具提供给用户的无非是三阶段式的服务，如果用前、中、后期来形容的话：

- 前期是在环境配置阶段，配置好编程语言需要的编译器/解释器，调试器，以及调试器的配置文件等等；

- 中期是在编辑代码时的自动补全、智能提示以及自动跳转等功能；
- 后期是在运行调试阶段，通过提供可视化的界面，让用户能够更方便的进行代码调试。

其实，自己感觉对于这类工具来说最有价值的，也是最能体现出这个工具好不好用的关键是在于中期提供的功能，因为对于前期和后期的提供的功能来说，并不是非有不可的，如果经验比较丰富的话，这些工作完全可以自己来完成。

## 参考

[^1]:Visual Studio Code 中的 Python 入门教程：https://code.visualstudio.com/docs/python/python-tutorial

[^2]:这个部分在之前的两篇文章当中已经详细介绍过了

[^3]:通过使用 Python 扩展，可以将 VS Code 变成一个出色的轻量级 Python 编辑器

[^4]:在 Visual Studio Code 中使用 Python 环境：https://code.visualstudio.com/docs/python/environments

[^5]:在 Visual Studio Code 中调试：https://code.visualstudio.com/docs/editor/debugging#_conditional-breakpoints

[^6]:Debugging configurations for Python apps in Visual Studio Code：https://code.visualstudio.com/docs/python/debugging
