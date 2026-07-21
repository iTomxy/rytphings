默認 26 鍵佈局在手機 (如 iOS 用 [1]) 上容易按錯相鄰鍵，
故想創建一個新鍵盤佈局，
合併一些相鄰鍵爲一個大鍵 (如 26 -> 14/17/18 鍵)，
減少按錯。

合併方案應：
1. 允許某些鍵保持獨立，但不能太多，否則依舊容易按錯。

2. 儘量少重碼 <- 基於完整碼表 (包括 derive) 統計分析，最好用上字頻
	- 碼表: rytphings.*.dict.yaml
	- 字/詞/句頻: 見 `C:/Users/<用戶名>/AppData/Roaming/Rime/rytphings.userdb/*.ldb`

3. 保障低重碼率時，若能兼顧 QWERTY 佈局就更好。若不能，寧願換個鍵盤佈局。

# 流程

## 0. 說明

- **list-clean（重碼率）**：打某碼時候選是否仍唯一。越高＝越少重碼。這是本文件開頭「儘量少重碼」的直接量度。

- **top-slot**：就算重碼，*更高頻* 的同碼字有沒有把你想要的字擠下第一位。~99% ＝ 幾乎無感（你要的字仍在最前）。合併方案通常 top-slot 都很高，真正拉開差距的是 list-clean。

- 分析預設 **排除 `abbrev` 首字母簡拼**（它本就大量重碼、與佈局無關）。

## 1. 相關文件

- **碼表（dict）**：[倉庫根目錄](../)的 `rytphings.*.dict.yaml`（`chars` 單字、`mod` 特殊、`greek` 希臘、`kana` 假名、`symbol` 符號、`phrase` 詞句）。`chars` 是主體；`greek/kana/symbol` 只要你會用就要一起算。

- **字頻（userdb）**：`%APPDATA%\Rime\rytphings.userdb\`（Windows Weasel）。這是 LevelDB（`*.ldb` + `*.log`），key 是你實際打過的拼式、value 內 `c=N` 就是提交次數＝真實字頻。iOS Hamster 的 userdb 在 App 沙盒/iCloud 同步夾，可經 Hamster「同步/備份」導出後同樣處理。

- **schema 的 derive 規則**：[rytphings.schema.yaml](../rytphings.schema.yaml) 的 `speller/algebra`。分析工具已把這串規則抄進 [analyze_layout_algebra.py](analyze_layout_algebra.py) 頂部的 `ALGEBRA`；**若改了 schema 的 algebra，要同步改那份 `ALGEBRA`**。

## 2. 從 userdb 導出字頻

```shell
python merge-keys/read_userdb.py \
	--db "%APPDATA%\Rime\rytphings.userdb" \
	--out merge-keys/freq.json
```
自寫的 LevelDB 讀取器，輸出 `freq.json`（每個拼式的使用次數；已 gitignore）。執行中的 `.log` 會被 RIME 鎖住而跳過，不影響大局（資料主要在 `.ldb`）。

## 3. 分析、比較各方案

```shell
# (a) 原始碼表、無 derive、無字頻（最粗略，僅作對照）
python merge-keys/analyze_layout.py --dir . --keys 18 17 14

# 下列皆用 analyze_layout_algebra.py
# （含 derive；加 --freq 用真實字頻；加 --tables 納入你會用的碼表）
COMMON="--freq merge-keys/freq.json --tables chars mod greek kana symbol"

# (b) 每條合併 xform 的邊際成本（找出「貴」的合併，如 s→a）
python merge-keys/analyze_layout_algebra.py --dir . --attribute $COMMON

# (c) 指定鍵數的 QWERTY-order 最優解（窮舉列內相鄰合併）
python merge-keys/analyze_layout_algebra.py --dir . --optimize 18 $COMMON

# (d) QWERTY-order vs 自由合併，14–19 鍵全面對比（核心決策表）
python merge-keys/analyze_layout_algebra.py --dir . --compare 14 15 16 17 18 19 $COMMON

# (e) 驗證某個具名方案，看兩個指標＋最重的重碼字對
python merge-keys/analyze_layout_algebra.py --dir . --fold 18freq $COMMON --show 20
```
結論（本倉庫實測）：QWERTY-order 在 17 鍵以下急速崩壞（14 鍵僅 45%），自由合併則平緩（14 鍵仍 85%）。少於 17 鍵就別強求 QWERTY。

## 4. 選定並生成佈局

1. 由第 3(d) 步的對比表決定 **鍵數** 與 **QWERTY / 自由**。
2. **自由合併**：用 [finalize.py](finalize.py) `--keys N`（預設 16）。它由 N 鍵貪心分組起步，做 local-search + 多次隨機重啟，鎖定最優分組、挑代表字母 (各鍵發送的字元＝組內最高頻字母)、擺回 QWERTY 家位，輸出：
	- `merge-keys/layoutN.json`（分組、代表、fold、指標；已 gitignore）
	- N→26 的 `xform` 合併規則
	```shell
	python merge-keys/finalize.py --keys 18
	```
	(代表字母只影響鍵面與 xform 寫法，不影響重碼率——重碼只看「分組」本身。)

3. **QWERTY 合併**：直接用第 3(c) 步 `--optimize K` 印出的 fold 即可。

## 5. 產出可部署檔案

- [rytphings18.schema.yaml](rytphings18.schema.yaml)：獨立 schema，共用 `rytphings` 詞典（連 userdb），只在 `speller/algebra` 末尾加那 8 條 `xform`。**用獨立 schema 而非改主 schema**，這樣 26 鍵的 rytphings（如 Windows Weasel）不受影響。合併 xform 具破壞性、必須放最後。純粵拼、已移除反查（iPhone Hamster 反查不顯示拼式，無用）。

- [hamster_keyboards.yaml](hamster_keyboards.yaml)：對應的 18 鍵鍵盤，每鍵 `character` 發送代表字母，`label` 顯示合併的字母組；另有 `繁簡`（#简繁切换）與 `換行`（#换行）功能鍵。佈局見 [layout18.txt](layout18.txt)。

## 6. 部署與測試

1. 把 [rytphings18.schema.yaml](rytphings18.schema.yaml) 與各 `rytphings.*.dict.yaml` 放進 RIME/Hamster 用戶目錄，重新部署。参考 [Wi-Fi 上传方案](https://ihsiao.com/apps/hamster/docs/guides/input_schema/)。
	- 或者自己將文件傳入手機，放到 Files -> On My iPhone -> Hamster -> Rime 目錄下。

2. Hamster 匯入 [hamster_keyboards.yaml](hamster_keyboards.yaml)，参考 [如何使用定义好的键盘](https://ihsiao.com/apps/hamster/docs/guides/custom_keyboard/)，有兩種方式：
	- 將 [hamster_keyboards.yaml](hamster_keyboards.yaml) 傳上 iphone 後，在 hamster 輸入法 [1] 軟件界面 -> 鍵盤設定 -> 鍵盤佈局 -> 右上角「+」-> 選那個上傳的 yaml 文件。
	- 自己將 [hamster_keyboards.yaml](hamster_keyboards.yaml) 的內容附加到 Files -> On My iPhone -> Hamster -> ShardSupport -> hamster_keyboards.yaml 中去；再檢查同目錄下的 hamster.yaml 中 `keyboards` 一項，有無條目 `__include: hamster_keyboards:/keyboards`，有則不用動，無則自己加上（注意縮進）。

3. RIME 部署。

重點測試第 3(e) 步印出的高頻重碼字對，尤其跨聲調的最小對立 (如 `-s` 去聲與 `aa→a` 的交互)。想在 Windows 先試，可把獨立 schema 也部署到 Weasel 驗證合併是否如預期。

文件都可在 iOS -> Files -> On My iPhone -> Hamster 目錄下找到，如：
- schema 文件放在其下 Rime/ 子目錄下；
- 鍵盤佈局相關文件 hamster.yaml、hamster_keyboards.yaml 都在其下 ShardSupport/ 子目錄下。

# References

1. [「仓」输入法](https://github.com/imfuxiao/Hamster)
2. [自定义键盘](https://ihsiao.com/apps/hamster/docs/guides/custom_keyboard/) , [自定义布局](https://github.com/imfuxiao/Hamster/wiki/%E8%87%AA%E5%AE%9A%E4%B9%89%E5%B8%83%E5%B1%80)
3. [倉輸入法·工具](https://lost-melody.github.io/hamster-tools/)
4. [键盘皮肤](https://ihsiao.com/apps/hamster/docs/guides/keyboard_skins/)
5. [导入自定义双键布局后无法正常使用#694](https://github.com/imfuxiao/Hamster/issues/694)
6. [forfudan/rime-clover-flypy](https://github.com/forfudan/rime-clover-flypy)
