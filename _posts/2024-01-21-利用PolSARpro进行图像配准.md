---
title: 利用PolSARpro进行图像配准
date: 2024-01-21 16:02:44 +0800
categories:
  - Research
tags: 
---
## 1. 引言

通常对于不同卫星拍摄的相同区域所得到的极化 SAR 数据图像之间会存在差异（比如：图像分辨率），在某些特定的应用场合下（比如：融合应用），可能需要用到这些彼此存在差异的数据，这时就需要对这些彼此存在差异的数据进行图像配准。

以两幅极化 SAR 图像为例，**图像配准**就是设法建立这两幅图像之间的对应关系，确定相应几何变换参数，对两幅图像中的一幅进行几何变换的方法[^1]。

> 注意区分**图像配准**和**几何校正**的区别，虽然二者处理过程类似，但是后者注重的是数据本身的处理，目的是为了对数据的一种真实性还原；而**图像配准**只要求一图像与另一幅图像配准，而不在乎该参考图像的几何精度高与否，只求两图像的对应位置坐标一致。
>
> 比如：之前 《极化 SAR 数据处理 — 地理编码》 一文中介绍的地理编码就属于**几何校正**。

<!--more-->

## 2. 利用 PolSARpro 进行图像配准

> 配准通常发生在不同卫星拍摄的相同地区的数据图像上，但是并不是对整幅图像进行配准，而是对这些图像中均存在的某一特定区域（即，感兴趣的研究区域）进行配准。

### 2.1 使用的数据

下面展示不同卫星（RADARSAT-2 和 ALOS-2）对同一地区（ San Francisco 地区）进行拍摄得到的两幅极化 SAR 数据图像进行配准。

与 《极化 SAR 数据处理 — 地理编码》一文中地理编码的过程类似，同样是使用到了 PolSARpro 中集成的 SNAP 工具模块（Utilities $$\rightarrow$$ SNAP - S1 TBX $$\rightarrow$$ Geocode [T3] matrix）。

### 2.2 统一图像分辨率

从下面两幅图中可以看出，ALOS-2 San Francisco 地区图像的空间分辨率[^2]（6.41152）明显高于 RADARSAT - 2 San Francisco 地区图像的空间分辨率（9.78673）。

![San Francisco Geocode（RS2 & ALOS2）](../assets/images/posts/2024-01-21/image-20240121160022763-ee333823.png)

现在想要将 ALOS-2 San Francisco 地区图像和 RADARSAT - 2 San Francisco 地区图像进行配准，按照实际应用对于分辨率的需求，分为以下两种情况：

- 如果对于分别率要求较高，就只能把分辨率低的图像强行拉高（比如：利用插值进行提升），即：把 RADARSAT - 2 San Francisco 的 Pixel Spacing (m) 由原来的 9.78673 直接变为 ALOS-2 San Francisco 的 Pixel Spacing (m) 6.41152，虽然这样做的话可能会使 RADARSAT - 2 San Francisco 的图像变得模糊
- 如果实际应用对于分辨率没有需求，可以进行折中处理，取 ALOS-2 San Francisco 的 Pixel Spacing (m) 和  RADARSAT - 2 San Francisco 的 Pixel Spacing (m) 的中间值 $$(6.41152 + 9.78673)/2 \approx 8$$ [^3]

下面，以第二种情况为例（即：折中处理），进行展示，

![Adjust resolution（RS2 & ALOS2）](../assets/images/posts/2024-01-21/image-20240121155553539-7beae6db.png)

![Resolution unification（RS2 & ALOS2）](../assets/images/posts/2024-01-21/image-20240121155705805-2776a63f.jpg)

### 2.3 裁剪研究区域

从要配准的数据中任选一个，并从中裁剪出感兴趣的研究区域，下面，以 ALOS-2 数据为例，用 GIMP  先框选出要裁剪的区域，并记录下相应的位置（2652, 7736）和大小（1528, 1724），

![Zone selection - GIMP](../assets/images/posts/2024-01-21/image-20231228095346858-7e3ba995.jpg)

接着，利用 PolSARpro 中的 Convert 对图像进行裁剪，

![Convert - PolSARpro](../assets/images/posts/2024-01-21/image-20231228094850997-d205768e.png)

用 GIMP 寻找感兴趣的区域时，需要注意 GIMP 中的位置以及大小，与 PolSARpro - Convert 中的 Row 和 Col 恰好是相反的，即：在这个例子中，Init Row = 7736，End Row = 7736+1724，Init Col = 2652，End Col = 2652+1528

![Crop Area - ALOS2](../assets/images/posts/2024-01-21/PauliRGB-72bc32e8.jpg)

### 2.4 寻找配准点进行配准

配准的关键在于，如何确定不同数据图像间剪裁的位置，如下图所示，虽然不同数据图像之间剪裁区域的大小是确定的，但是位置却是不同的，因为对于不同数据图像来说整体的大小是不一样的，需要通过寻找数据图像之间的配准点来确定。

![Zone selection - GIMP](../assets/images/posts/2024-01-21/image-20231228095346858-7e3ba995.jpg)

基于上面的思想，给出的配准步骤大致如下：

1. 在裁剪出来的区域中选择一个配准点[^4]（或者称为基准点，不动点，参考点等等），即：通过观察两个数据图像中的相应区域，在区域中找到一个对于两幅图像来说都不变的点（因为由于两幅图像拍摄时间，卫星入射角度等等的不同，虽然是同一区域，但是在很多细节部分还是有差别）
2. 利用找出来的配准点，计算出 RADARSAT-2 （未剪裁数据）中的相应剪裁区域的位置
3. 通过位置加上剪裁区域的大小，最终确定在 RADARSAT-2（未剪裁数据）上需要剪裁的区域

![Registration procedure diagram](../assets/images/posts/2024-01-21/image-20240121151431387-6668eb2f.png)

## 3. 小结

最后，简单展示一下，两幅数据（RADARSAT-2 和 ALOS-2）的配准结果：

![Registration result（RS2 & ALOS2）](../assets/images/posts/2024-01-21/image-20240121155454239-d10b0027.jpg)

## 参考

[^1]: ENVI图像处理（7）：图像配准_envi图像配准: https://blog.csdn.net/qq_48322523/article/details/117001706

[^2]:空间分辨率，是指遥感图像上能够详细区分的最小单元的尺寸或大小，是用来表征影像分辨地面目标细节的指标。

[^3]: 处理时可以直接对小数部分进行截断处理。

[^4]: 为了配准结果的准确，通常需要选择多个配准点，但是本例为了叙述上的简洁，仅选择一个点

