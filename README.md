# rytphings

基于粤拼 <sup>[1,2]</sup> 的自改粤语拼音方案。
自制 Rime 输入方案、启用可以参考 [3,4]。

# 方案简述 / The Scheme

改编动机是将声调「还原」回由声母清浊、后缀派生表达的形式：
中古四声的来源是上古后缀 <sup>[5]</sup>，
阴阳调的来源是声母清浊。
所以总体的设计是：

1. `-q` 表示以前的 *-ʔ 后缀，标上声；
2. `-s` 表示以前的 *-s 后缀，标去声；
3. 阳入韵尾还是 `-p/t/k`，阴入用 `-p/t/k` 和 `-b/d/g` 的屈折区分上、下阴入。
（参考：[#1](https://github.com/iTomxy/rytphings/issues/1)、[9-11]）

阴阳调总体以清、浊音辅音区分，
加 `h` 表示送气。
但有些例外需要特别处理：

1. 晓母以前对应的浊音旧匣母在中古汉语拼音（*古韵罗马字*）<sup>[6]</sup>、切韵拼音 <sup>[7]</sup> 中都是 gh，
但 gh 已经用来表示阳调时的溪母，
所以参考赵元任先生的方案 <sup>[8]</sup>，
用 x 表示阳调时的晓母。

2. 明、泥、来、我四母也有阴调的辖字，
参考 [8]，
复用 `h` 标记阴调。
但我母在阴调时统一实现为零声母（亞母，清喉塞音 [ʔ]），
所以不用 ngh。

3. 为缩短符号，
舌音不分精照，
参考 [8]，
精、清二母阴调时写作 c、ch，
阳调时写作 j、jh。

4. 以、云在阴调时用 i、u；
阳调时因为 j 被舌音占了，
故以母改用 r 标，
~~直觉可以是 [ʒ] 音，~~
借来记 [j]；
云母就用 w。
当声母是 i/u，
韵母又是以 i/u 开头时，
就省略声母不写，
但注意此时**不**是零声母 /ʔ-/（即 q-）。

5. 也是贪短，
[y] 写作 y 而不是 yu，
并将 eoi 改成符合唇形的 eoy。

6. 对于古、困二母，
粤拼中分别写作 gw、kw，
在针对阴阳调屈折时，
只改 k/g，
不动 w。

## 声母 / Initials

| | | | |
| - | - | - | - |
| 兵 p / 並 b | 滂 ph / 旁 bh | 非 f / 肥 v | 媽 mh / 麻 m |
| 煅 t / 段 d | 偷 th / 頭 dh | 拉 lh / 來 l | 乸 nh / 那 n |
| 精照 c / 靜趙 j | 清穿 ch / 晴傳 jh | 修深 s / 愁岑 z |
| 見 k / 健 g | 崎 kh / 奇 gh | 口 h / 厚 x | 愛 (q) / 外 ng |
| 貴 kw / 櫃 gw | 昆 kwh / 羣 gwh |
| 衣 i / 移 r | 溫 u / 云 w |

## 韵母 / Finals

| | -ø | -i | -y | -u | -m | -n | -ng | -p/-b | -t/-d | -k/-g |
| - | - | - | - | - | - | - | - | - | - | - |
| aa | 啊 | 隘 | | 拗 | 監 | 慳 | 坑 | 匣/鴨 | 捺/壓 | 白/百 |
| a | | 矮 | | 嘔 | 庵 | 分 | 亨 | 恰/ | 乞/ | 黑/ |
| i | 衣 | | | 邀 | 淹 | 煙 | 英 | 鎳/妾 | 必/憋 | 益/ |
| y | 于 | | | | | 淵 | | | 粵/雪 |
| e | 些 | 希 | | *掉 | *舐 | | 病 | *夾 | | 石/尺 |
| eo | | | 虛 | | | 臻 | | | 卒 |
| oe | 靴 | | | | | | 香 | | * | 藥/葯 |
| o | 哦 | 哀 | | 奧 | | 安 | 康 | | 褐/喝 | 學/惡 |
| u | 污 | 煨 | | | | 碗 | 空 | | 活/潑 | 屋/捉 |
| m | 唔 |
| ng | 吳 |


## 声调 / Tones

| | 平 | 上 | 去 | 入 |
| - | - | - | - | - |
| 陰 | 巴 paa | 把 paaq | 霸 paas | 不 pat / 八 paad |
| 陽 | 麻 maa | 馬 maaq | 罵 maas | 襪 mat |


# 生成码表 / Dictionary Generation

码表（*\*.dict.yaml*）基于 [2] 的文件生成。
本仓有添加 [2] 做子模块，
可以用

```shell
git submodule update --init --recursive
git submodule update --remote
```

将子模块的内容拉下本地，
再用 [Python](https://www.python.org/) 运行转换代码：

```shell
python cvt-jyut6ping3-rytphings.py
```

或者另外下载 [2]，用 `--jyut6ping3-dir` 参数指定位置：

```shell
python cvt-jyut6ping3-rytphings.py --jyut6ping3-dir <某路径>/rime-cantonese
```

现时默认只会转换 [2] 中 *jyut6ping3.chars.dict.yaml* 这一个文件，
即单字的码表。
想转换更多，
可以用 `--dict-files` 指定：

```shell
python cvt-jyut6ping3-rytphings.py --dict-files \
    jyut6ping3.chars.dict.yaml \
    jyut6ping3.words.dict.yaml \
    jyut6ping3.phrase.dict.yaml \
    jyut6ping3.lettered.dict.yaml \
    jyut6ping3.maps.dict.yaml
```

# 更新 / Updates

## 2024.12.21

支持困母的合口、送气标记换位，
即：

- kwh = khw
- gwh = ghw

## 2024.12.1

显式亞母 `q-` 只适用于：

- a, e, o 开头
- uk, ung

而

- i 开头
- 其余 u 开头

是音调以母、云母，
不支持前加 `q-`。

## 2024.11.30

按《[A Chinese dictionary in the Cantonese dialect](https://www.google.com.hk/books/edition/A_Chinese_dictionary_in_the_Cantonese_di/mh8TAAAAYAAJ)》改 [cvt-jyut6ping3-rytphings.py](cvt-jyut6ping3-rytphings.py) 中四声英译：

- 平 even tone / monotone
- 上 ascending / rising
- 去 departing
- 入 abrupt / entering
- 仄 deflected

## 2024.11.26

支持单独出现的（即无韵尾的） aa 写作 a，
如：

- 巴 paa > pa
- 把 paaq > paq
- 霸 paas > pas

## 2024.11.24

支持 oi/ui 表示成 oy/uy（即以圆唇结尾）。

## 2024.10.10

阳入 -b/-d/-g 混同 -p/-t/-k 改由 [rytphings.schema.yaml](rytphings.schema.yaml)/speller/algebra 之 derive 命令实现，
[cvt-jyut6ping3-rytphings.py](./cvt-jyut6ping3-rytphings.py) 不再生成对应冗余拼写。

## 2023.9.20

1. 零声母支持显式加 `q`，
如「愛」：ois = qois。
~~修改在 [rytphings.schema.yaml](rytphings.schema.yaml)/speller/algebra，启用了 `derive/^([aeiou])/q$1/` 一行。~~

2. 支持阳入用 -b/-d/-g 混同 -p/-t/-k，
因为并无对立，
解除同声母的耦合。
由 [cvt-jyut6ping3-rytphings.py](./cvt-jyut6ping3-rytphings.py) 生成对应冗余拼写。

## 2023.3.29

现支持复韵尾表示入声的升调变调，如：
- 𠻘: zoet2 -> coet**q**
- 雀: zoek2 -> coek**q**

# 参考 / References

1. [rime/rime-jyutping](https://github.com/rime/rime-jyutping)
2. [rime/rime-cantonese](https://github.com/rime/rime-cantonese)
3. [Rime 輸入方案設計書](https://github.com/rime/home/wiki/RimeWithSchemata)
4. [自制Rime输入方案初步](https://zhuanlan.zhihu.com/p/576244701)
5. [中古漢語的聲調是如何從上古漢語演變成的？](https://www.zhihu.com/question/319038478/answer/1375097629)
6. [中古汉语拼音](https://zh.wikipedia.org/wiki/Wikipedia:%E4%B8%AD%E5%8F%A4%E6%BC%A2%E8%AA%9E%E6%8B%BC%E9%9F%B3)
7. [切韵拼音](https://zhuanlan.zhihu.com/p/478751152)
8. [趙元任粵語羅馬字](https://zh-yue.wikipedia.org/wiki/%E8%B6%99%E5%85%83%E4%BB%BB%E7%B2%B5%E8%AA%9E%E7%BE%85%E9%A6%AC%E5%AD%97)
9. [粤语广州话的十一元音音位与长短元音对立](https://zhuanlan.zhihu.com/p/265020710)
10. [为什么粤语的入声音调有三种，阴入要分成两种？](https://www.zhihu.com/question/36615633)
11. [粵語聲調](https://zh.m.wikipedia.org/zh/%E7%B2%B5%E8%AA%9E%E8%81%B2%E8%AA%BF)
12. [windows禁用输入法](https://blog.csdn.net/HackerTom/article/details/131114830)
13. [rime-japanese](https://github.com/gkovacs/rime-japanese)
14. [Rime Old Cantonese Input Scheme | 《分韻撮要》音系及輸入方案](https://github.com/leimaau/old-Cantonese)
15. [粵音資料集叢](https://github.com/jyutnet/cantonese-books-data)
16. [LEOYoon-Tsaw/Rime_collections](https://github.com/LEOYoon-Tsaw/Rime_collections)（其中[清代粵語](https://github.com/LEOYoon-Tsaw/Rime_collections/blob/master/Old_cantonese.markdown)有分韵时期粤语同当代粤语之间声、韵、调对应图）
