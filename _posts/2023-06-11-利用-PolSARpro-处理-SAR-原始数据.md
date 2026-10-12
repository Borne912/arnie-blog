---
title: 利用 PolSARpro 处理 SAR 原始数据
date: 2023-06-11 15:07:45 +0800
categories:
  - Research
tags: 
---
## 基本介绍

不同的卫星，比如：

- Radarsat-2
- GF-3
- ALOS-2

由它们得到的 SAR 原始数据的格式不同，也就意味着对其处理的方式也不尽相同。

下面，将以 Radarsat-2 卫星的 SAR 数据为例，讲解 SAR 原始数据的处理过程。
<!--more-->
## Radarsat-2 数据格式

以 Radarsat-2 卫星为例，其所有数据产品均为 `GeoTIFF` 格式。产品一般由三大部分组成：

- 一个产品信息文件（Product Information File）
- 一至四个 `TIFF` 格式图像数据文件（Image Pixel Data File）
- 若干辅助文件或目录（Support File）

<img src="../assets/images/posts/2023-06-11/Obsidian202306111017909-c9a2e8c9.png" alt="RADARSAT-2卫星数据产品组成" style="zoom: 80%;" />

RADARSAT-2 卫星具体的数据产品文件组成，如下图所示：

![RADARSAT-2 卫星数据产品文件组成](../assets/images/posts/2023-06-11/Obsidian202306111032497-b6e90db8.png)

### 产品信息文件

产品信息文件内容采用 `ASCII` 码表示，利用 `XML` 语言组织，主要保存数据产品的各种参数信息，用户可以使用任意文本编辑软件查看其中的内容。文件内部的各种信息按相关程度分为若干层（layer）保存。

### 图像数据文件

RADARSAT-2 卫星产品当中的图像数据文件均为 `GeoTIFF` 图像，每种极化方式对应一个图像文件，因此每个数据产品最多包含 4 个文件。

在图像文件头部的 `TIFF Tag` 部分保存着图像数据文件的参数信息，如文件尺寸、数据类型，指向、投影方式等等。

目前大部分专业的遥感图像处理软件，如 PCI 和 ENVI，都支持 `GeoTIFF` 文件。

### 辅助文件

数据产品中的辅助文件包括一些版权说明或者 `XML` 格式解析文件，其中需要特别说明的是 `LUT` 文件。

除了 SSG 和 SPG 产品之外，所有 RADARSAT-2 卫星数据产品当中都包含有 3 个 `LUT` 文件，即：

- lutBeta.xml
- lutGamma.xml
- lutSigma.xml

借助这些文件，用户可以进行 RADARSAT-2 数据的辐射定标，将图像数据的 DN 值还原为 $\sigma^{0}$、$\beta^{0}$ 和 $\gamma^{0}$。

## Radarsat-2 数据处理

根据极化测量学（polarimetry）的知识，需要从 SAR 原始数据中提取出 S 矩阵，具体步骤如下：

1. 打开 PolSARpro 软件，进入到 PolSAR 数据处理工具集主界面，选择 "PolSARpro Bio"

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111104467-4e5f70e7.png" alt="image-20230611110445428" style="zoom:40%;" />

   接着，点击 "进入(Enter)"，来到 PolSARpro 工具界面

   ![image-20230611110739579](../assets/images/posts/2023-06-11/Obsidian202306111107623-3f258f19.png)

1. 点击"环境(Environment)"，选择"单一数据集(Single Data Set(Pol-SAR))"

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111121175-68a61693.png" alt="image-20230611112124126" style="zoom:80%;" />

2. 选择数据存放的路径，"保存&退出(Save & Exit)"，之后会弹出一个提示，点击"确定(yes)"

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111125095-2020d42b.png" alt="image-20230611112526044" style="zoom:80%;" />

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111128240-d444e1c1.png" alt="image-20230611112800189" style="zoom:80%;" />

3. 从"导入(import)"菜单中，找到 RadarSAT-2 全极化(根据要处理的数据的类型选择即可)

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111132547-de04a4d3.png" alt="image-20230611113213496" style="zoom: 50%;" />

4. 配置 product.xml 文件的路径

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111229332-a0ce22ca.png" alt="image-20230611122920284" style="zoom:50%;" />

5. 点击 "读取数据头文件(Read Header)"，在弹出的提示框中，点击"确认(OK)"

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111233770-8f3458c4.png" alt="image-20230611123356719" style="zoom: 40%;" />

6. 之后，在"输入数据文件(Input Data File)"选项区部分就会显示，四种极化方式(全极化)下对应的文件，点击"确认(OK)"，之后会再次弹出一个提示框，同样点击"确认(OK)"即可

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111241169-d920454c.png" alt="image-20230611124120108" style="zoom:50%;" />

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111244054-21484ad3.png" alt="image-20230611124426999" style="zoom:50%;" />

7. 点击 "import(导入)" 菜单，选择 "提取 PolSAR 图像(Extract PolSAR images)"

   <img src="../assets/images/posts/2023-06-11/Obsidian202306111247708-30e57f67.png" alt="image-20230611124706634" style="zoom: 67%;" />

8. 在 "Output Data Format" 选项区部分选择 "Sinclair Elements" - "[S2]"，点击 "运行(Run)"，并在弹出的提示框中点击 "确认(yes)"，即可提取出 S 矩阵

   ![](../assets/images/posts/2023-06-11/Obsidian202306111254308-670b090d.png)

9.  处理完成后，文件目录下会多出如下图所示的文件：

    <img src="../assets/images/posts/2023-06-11/Obsidian202306111336578-89f13039.png" alt="image-20230611133630514" style="zoom:50%;" />

    由红框标出的部分就是我们需要的 S 矩阵，可以进一步导入到 Matlab 或 Python 中处理。

    > 提示：重复步骤8～9，在步骤9中选择其它类型的输出格式，也可以得到 T 矩阵和 C 矩阵！

## 参考

- [074期用户简讯-CEODE](http://satsee.radi.ac.cn/cfdata/user/074%E6%9C%9F%E7%94%A8%E6%88%B7%E7%AE%80%E8%AE%AF.pdf)

- [RADARSAT-2 PRODUCT FORMAT DEFINITION](https://earth.esa.int/eogateway/documents/20142/0/Radarsat-2-Product-Format-Definition.pdf/1ca0cf1e-5a15-a29b-6187-9e5cb1650048)

  