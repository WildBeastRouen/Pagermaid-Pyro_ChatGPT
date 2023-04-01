[中文說明](https://github.com/WildBeastRouen/Pagermaid-Pyro_ChatGPT/blob/main/README_CN.md)

[Readme](https://github.com/WildBeastRouen/Pagermaid-Pyro_ChatGPT/blob/main/README.md)

基於 Pagermaid-Pyro 的 telegram openaichat 腳本，進行幾項改進。

* 將模型升級為 gpt-3.5-turbo
* 解決執行緒死鎖問題
* 加上直接回覆他人對話來對 AI 提問的功能

如何使用？

* 將 ai.py 文件置於 pagermaid plugins 文件夾內，並使用 ,reload 命令重新載入
* 在 telegram 對話方塊中輸入 ,ai "你的問題" 來與 ChatGPT 聊天
