# 说明
这里包含了[ellye](https://github.com/watermellye/)编写的AutoPCR（下称“本项目”）模块，实现了装备农场以及自动清日常的功能。

其中，BCR登录模块使用了[冲冲](https://github.com/cc004)的[仓库](https://github.com/cc004/pcrjjc2/)中的部分代码。

# 部署方式
`pip install -r requirements.txt`

注意是`hoshino/modules`下的`requirements.txt`，根目录下的是HoshinoBot原版所需的。

清日常模块建议额外安装`Firefox浏览器`和`Chrome浏览器`，否则将使用`matplotlib`模块绘制结果。若不安装，请参考下方模块中的说明解决`matplotlib`模块的中文渲染问题。

建议使用 Windows 10 及以上，或Windows Server 2019及以上。如果遇到各种dll缺失问题，建议直接安装 Visual Studio 2019 及其C++桌面开发模块。

建议在“本地组策略编辑器”中，在左侧栏内依次进入“计算机配置”-“管理模板”-“系统”-“文件系统”，在右侧栏中对“启用Win32长路径”设置项设置为“已启用”。

# 装备农场模块
装备农场涉及其中的`autopcr_db`, `farm`, `query`文件夹。

新版装备农场支持在一个插件中管理多个公会，仅支持免费模式。

请把农场号信息放入`/data/account.json`中，在启动Hoshino时会自动加载。详细说明请见`/data/account.json.example`

请确保`/data/account.json`中包含你的各农场公会的会长账密。请将农场公会的加入模式置为邀请模式。

支持的指令请见`farm.py`开头，或发送`农场帮助`。

# 清日常模块
清日常模块涉及其中的`autopcr_db`, `priconne/pcr_secert`, `priconne/myweb`, `query`, `autobox`文件夹。

清日常模块于2022年初开始，最初功能为刷取心碎和星球杯的300体，以便早班刀手代刀。随后逐渐扩充出账号管理，box管理，以及完整的清日常功能。由于作者编程水平很菜，该模块中的`priconne/pcr_secert`, `priconne/myweb`, `autobox`部分代码未遵循任何python开发规范，且已堆成“屎山”，即使作者难以阅读、修改，将逐渐重构。

## 解决`matplotlib`模块的中文渲染问题
1. 通过运行以下代码来获取路径。路径应形如：`...\Lib\site-packages\matplotlib\mpl-data\matplotlibrc`。
```
import matplotlib
print(matplotlib.matplotlib_fname())
```
2. 打开路径对应的文件，在最下方加入：
```
font.family  : sans-serif
font.sans-serif : SimHei, DejaVu Sans, Bitstream Vera Sans, Computer Modern Sans Serif, Lucida Grande, Verdana, Geneva, Lucid, Arial, Helvetica, Avant Garde, sans-serif
```
3. 如果你的操作系统没有黑体字体，请下载`simhei.ttf`，加入`...\Lib\site-packages\matplotlib\mpl-data\fonts\`下。
4. 删除`C:\Users\<你的用户名>\.matplotlib\`文件夹，随后重启HoshinoBot。

另，已知`dataframe_image`模块在某些实例上存在输出图片过度裁剪问题。基本不影响使用，若感兴趣可自行尝试进入源码debug并修复。

## 重构计划
新版AutoPCR已进入开发。部分新版AutoPCR的改进和新特性列举如下：
- 清日常模块：
    - 可以完全通过网页端操作（含账号绑定）。
    - 支持绑定多个pcr账号。
    - 每个pcr账号可以查询最后10次清日常触发历史与结果。
    - 使用网页端触发清日常时，将实时推送当前工作进度与结果。
    - 更清晰的配置页面。配置项按照功能分类。
    - 更灵活的配置选择（例如：当且仅当在n2n3时购买3管体力并自动清空体力至n图）（接入PCR Calendar模块）。
    - 允许录入多套自定义配置并随时切换。提供多套预设配置。
- 其他：
    - 帮助页面。
    - 好感相关：查询各角色好感度、剧情阅读情况、属性值（接入PCR Wiki模块）。
    - 好感相关：对指定角色升好感、阅读好感剧情。
    - 支援相关：新增上号调星功能。
    
改进和功能将逐渐实装。