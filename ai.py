import contextlib
import threading
import re

from collections import defaultdict

from pagermaid.services import sqlite
from pagermaid.enums import Message
from pagermaid.listener import listener
from pagermaid.utils import pip_install

pip_install("openai", "==0.27.2")

import openai

async def get_chat_response(prompt: str) -> str:
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "I'm cat BOT! Miao!"},
                  {"role": "user", "content": prompt}],
        max_tokens=3072,
        n=1,
        temperature=0.9,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.6,
    ).choices[0].message["content"]

chat_bot_session = defaultdict(dict)

def set_api_key(api_key: str) -> None:
    sqlite["openaichat_api_key"] = api_key
    openai.api_key = api_key


def get_api_key() -> str:
    return sqlite.get("openaichat_api_key", None)


def del_api_key():
    del sqlite["openaichat_api_key"]


def set_template(template: str) -> None:
    sqlite["default_template"] = template


def get_template() -> str:
    return sqlite.get("default_template", None)


def formatted_response(prompt: str, message: str) -> str:
    if not get_template():
        set_template(default_template)
    message = re.sub(r'^\s+', r'', message)
    try:
        return get_template().format(prompt, message)
    except Exception:
        return default_template.format(prompt, message)


default_template = "{0}\n====\n{1}"
openai.api_key = get_api_key()
chat_bot_help = "使用 OpenAI Chat 聊天\n" \
                "基于 gpt-3.5-turbo 模型，与 ChatGPT 的效果有些许不同\n" \
                "代码参考了原先的 ChatGPT 插件\n\n" \
                "参数：\n\n- 问题：询问 ai\n" \
                "- reset：重置聊天话题\n" \
                "- thread：获取已记录的聊天话题\n" \
                "- set <api_key>：设置 OpenAI API Key，获取 API Key： https://beta.openai.com/account/api-keys \n" \
                "- del：删除 OpenAI API Key\n" \
                "- template {set|get|reset} <template>: 设置/获取/重置回应模板。回应模板中的 {0} 将替换为问题，{1} 将替换为回答"


@listener(
    command="ai",
    description=chat_bot_help,
)

async def chat_bot_func(message: Message):
    if not message.arguments:
        if message.reply_to_message:
            message.arguments = message.reply_to_message.text
        elif message.parameter:
            message.arguments = await message.edit(message.arguments)
        else:
            return await message.edit(chat_bot_help)
    from_id = message.from_user.id if message.from_user else 0
    from_id = message.sender_chat.id if message.sender_chat else from_id
    if not from_id:
        from_id = message.chat.id
    if len(message.parameter) >= 2:
        if message.parameter[0] == "set":
            token = message.parameter[1]
            if not token.startswith("sk-"):
                return await message.edit("无效的 API Key。")
            set_api_key(message.parameter[1])
            try:
                openai.Model.list()
            except Exception as e:
                return await message.edit(f"设置失败：{repr(e)}")
            return await message.edit("设置 API Key 成功，可以开始使用了。")
        elif message.parameter[0] == "template":
            arg = message.parameter[1]
            if arg == "get":
                return await message.edit(get_template())
            elif arg == "reset":
                set_template(default_template)
                return await message.edit("重置回应模板成功。")
            elif arg == "set" and len(message.parameter) >= 3:
                set_template(message.parameter[2] or "")
                return await message.edit("设置回应模板成功。")
    elif message.arguments == "reset":
        with contextlib.suppress(KeyError):
            del chat_bot_session[from_id]
        return await message.edit("已重置聊天话题。")
    elif message.arguments == "thread":
        return await message.edit(chat_bot_session.get(from_id, {}).get("chat_thread", "没有已记录的聊天话题。"))
    elif message.arguments == "del":
        if not get_api_key():
            return await message.edit("没有设置 API Key。")
        del_api_key()
        return await message.edit("已删除 API Key。")
    if not get_api_key():
        return await message.edit("请先通过参数 `set [api_key]` 设置 OpenAI API Key。")
    with contextlib.suppress(Exception):
        message: Message = await message.edit(formatted_response(message.arguments, "请稍等..."))
    try:
        chat_thread = chat_bot_session.get(from_id, {}).get("chat_thread", "")
        prompt = f"{chat_thread}\nHuman: {message.arguments}\nAI: "[-96:]  # 4096 - 150(max_tokens)
        msg = await get_chat_response(prompt)
        chat_bot_session[from_id]["chat_thread"] = prompt + msg
    except Exception as e:
        msg = f"可能是 API Key 过期或网络/输入错误，请重新设置。\n{repr(e)}"
    if not msg:
        msg = "无法获取到回复，可能是网络波动，请稍后再试。"
    with contextlib.suppress(Exception):
        await message.edit(formatted_response(message.arguments, msg))
