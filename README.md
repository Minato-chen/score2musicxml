# score2musicxml

把单个管乐器的单声部乐谱（PDF或图片）识别成 MusicXML，方便直接拖进 MuseScore 编辑。

## 适用范围（V1）

- **优先**：电子化PDF（从Sibelius/Finale/MuseScore等软件导出的印刷体乐谱）
- **其次**：手写/拍照乐谱（准确率明显更低，仅作为兜底）
- 只支持**单个乐器的单声部**。总谱/指挥谱（一页多个乐器叠在一起）、固定多重奏、军鼓等无音高打击乐**暂不支持**。
- 只关注：调号、拍号、音高、音符时值、反复结构（反复记号/房子记号）、延音线（跟时值直接相关，算核心内容）。圆滑线（slur）能力所及也会保留，但不专门优化。
- 力度、速度、演奏技巧等标记会被直接从输出中剔除，不做识别优化（这些在MuseScore里自己加更快更准）。

## 环境要求

- Python 3.11–3.15
- macOS/Linux/Windows

## 安装

```bash
python3.13 -m venv .venv       # 或其他 3.11-3.15 版本
source .venv/bin/activate
pip install -e .
homr --init                    # 提前下载识别模型（几百MB），非必需但能避免首次运行卡住
```

## 用法

把要识别的PDF或照片放进项目根目录的 `input/` 文件夹（没有的话运行一次会自动创建），然后：

```bash
score2musicxml <文件名> --instrument <乐器id>
#批量处理input中的文件
score2musicxml --instrument trumpet_bb
```

示例：

```bash
score2musicxml my_part.pdf --instrument clarinet_bb
```

- `<文件名>` 默认去 `input/` 里找；也可以直接传绝对/相对路径，不一定非要放进 `input/`
- 输入文件支持 `.pdf` 或图片（`.png` `.jpg` `.jpeg` `.tif` `.tiff` `.bmp`）
- 输出自动写到 `output/<文件名>/<文件名>_<乐器id>.musicxml`（同时也是MusicXML里的曲目标题）；每页中间识别结果也存在同一个文件夹的 `work/` 子目录里，方便排查问题
- 如果 `output/<文件名>/` 已经存在（比如重新跑了一遍），会自动改成 `output/<文件名>_2/`、`_3/`……不会覆盖旧结果

### 可选参数

| 参数 | 说明 |
|---|---|
| `--dpi` | PDF转图片的分辨率，默认300 |
| `--debug` | 透传给homr的调试输出 |

### 支持的乐器

```
piccolo flute oboe clarinet_bb bass_clarinet bassoon
soprano_sax alto_sax tenor_sax bari_sax
trumpet_bb horn_f trombone bass_trombone euphonium_bc tuba
```

乐器选择决定输出MusicXML里的乐器名称/音色/移调信息（`<transpose>`），保证MuseScore打开后playback和乐器音色正确。**不会**对识别出的音符做二次移调——谱面上写的什么音，识别结果就是什么音。

## 输出

- 一个 `.musicxml` 文件，可直接用MuseScore打开编辑
- 终端会打印警告列表（如果有），标出哪些小节的时值、反复记号、调号看起来有问题，建议在MuseScore里重点复核这些地方。**没有警告不代表100%准确**，尤其是手写/照片输入。

## 已知限制

- 总谱（多乐器叠放）、固定多重奏、无音高打击乐（军鼓等）：暂不支持，需要单独开发
- 手写/照片乐谱：准确率明显低于电子PDF，字迹潦草、涂改、密集的力度/装饰记号会显著影响识别，建议识别后逐小节对照原谱复核
- 依赖的开源OMR引擎 [homr](https://github.com/liebharc/homr) 目前只支持高音谱号和低音谱号，长号等偶尔使用的次中音谱号可能识别不准

## 项目结构

```
score2musicxml/
  instruments.py     乐器元数据表（调号/移调/音色，基于music21）
  pdf_to_images.py   PDF转图片（PyMuPDF）
  recognize.py       调用homr识别单页
  merge.py           多页拼接成一个连续声部
  postprocess.py      剔除力度/速度/演奏技巧标记；校验调号/拍号/时值/反复；写入乐器信息
  pipeline.py         整体编排
  cli.py              命令行入口
```
