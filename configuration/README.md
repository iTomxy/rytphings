本目錄爲本人 RIME 配置文件之備份，與 rytphings 方案無關。

- [default.custom.yaml](default.custom.yaml)：候選字數、方案列表（順序）、呼出方案選單快捷鍵。
- [weasel.custom.yaml](weasel.custom.yaml)：配色。
- [ctrl-space.bat](ctrl-space.bat)：0.16.2 及之後版本設置 ctrl + space 組合鍵效果。
- [ipa_yunlong.custom.yaml](ipa_yunlong.custom.yaml): 取消「-」、「=」、「.」鍵與翻頁快捷鍵之綁定，因它們亦用作雲龍國際音標之輸入編碼。此衝突由 [ipa_yunlong.schema.yaml](https://github.com/rime/rime-ipa/blob/master/ipa_yunlong.schema.yaml) 之 `speller/alphabet` 與 [key_bindings.yaml](https://github.com/rime/rime-prelude/blob/master/key_bindings.yaml)（或 *%APPDATA%\Rime\build\default.yaml* 內 `key_binder/bindings`）之重複可見。
