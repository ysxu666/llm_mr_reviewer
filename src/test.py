import httpx
import json
import os

# 设置 API URL 和 API Key
API_URL = "https://api.deepseek.com"
API_KEY = "sk"  # 替换为你的实际 API Key

# # 测试用的提示词
# # TEST_PROMPT = "请对以下代码进行 review：\nint main() { return 0; }"
# TEST_PROMPT ="hello"
# async def test_api_call():
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#         "Content-Type": "application/json"
#     }
    
#     # payload = {
#     #     "model": "deepseek-chat",
#     #     "messages": [{"role": "user", "content": TEST_PROMPT}]
#     # }
#     payload = {
#         "model": "deepseek-chat",
#         "messages": [
#             {"role": "system", "content": "You are a helpful assistant."},
#             {"role": "user", "content": TEST_PROMPT}
#         ],
#         "stream": False
#     }
    
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(API_URL, json=payload, headers=headers)
#             response.raise_for_status()  # 如果响应状态码不是 200，抛出异常
#             print("API 调用成功！")
#             print("响应内容：")
#             print(json.dumps(response.json(), indent=4))
#     except httpx.HTTPStatusError as e:
#         print(f"HTTP 错误：{e.response.status_code}")
#         print(f"响应内容：{e.response.text}")
#     except httpx.RequestError as e:
#         print(f"请求错误：{e}")
#     except Exception as e:
#         print(f"未知错误：{e}")

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(test_api_call())


# Please install OpenAI SDK first: `pip3 install openai`

# from openai import OpenAI

# client = OpenAI(api_key=f"{API_KEY}", base_url="https://api.deepseek.com")
# TEST_PROMPT = "你是一名经验丰富的计算机工程师，请从专业的角度，对以下代码进行review，对于不完善的地方，请提出针对性的优化建议。在给出意见时请保持语言的简洁，只需对可能导致程序严重错误的地方提出修改建议，无需给出示例代码。review 时不需要吹毛求疵，如果没有更好的优化建议，建议的内容可以为空\nint main() { return 0; }"
# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": TEST_PROMPT},
#     ],
#     stream=False
# )

# print(response.choices[0].message.content)

# from openai import OpenAI
# client = OpenAI(api_key="sk-b873afb5e2714d68870e8b8681458b40", base_url="https://api.deepseek.com")


# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": "Hello"},
#     ],
#     stream=False
# )

# print(response.choices[0].message.content)

# async def call_deepseek_async() :
#     # 步调用 DeepSeek API 并返回结果
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#         "Content-Type": "application/json"
#     }
    
#     payload = {
#         "model": "deepseek-r1-250120",
#         "messages": [{"role": "user", "content": TEST_PROMPT}]
#     }

#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(API_URL, json=payload, headers=headers)
#             response.raise_for_status()  # 如果响应状态码不是 200，抛出异常
#             print("API 调用成功！")
#             print("响应内容：")
#             print(json.dumps(response.json(), indent=4))
#     except httpx.HTTPStatusError as e:
#         print(f"HTTP 错误：{e.response.status_code}")
#         print(f"响应内容：{e.response.text}")
#     except httpx.RequestError as e:
#         print(f"请求错误：{e}")
#     except Exception as e:
#         print(f"未知错误：{e}")

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(call_deepseek_async())

from github_assistant import GithubAssistant
GITHUB_TOKEN = "ghp"
REPOSITORY_OWNER = "ysxu666"
REPOSITORY_NAME = "my-test-repo"
PULL_REQUEST_ID = 10  # 替换为你的拉取请求 ID

github_assistant = GithubAssistant(GITHUB_TOKEN, REPOSITORY_OWNER, REPOSITORY_NAME, PULL_REQUEST_ID)

# 测试发送评论
filename = "code4.py"  # 替换为实际文件名
position = 10  # 替换为实际行号
comment_text = "This is a test comment from the script."

try:
    github_assistant.add_comment(filename, position, comment_text)
    print("Comment added successfully!")
except Exception as e:
    print(f"Failed to add comment: {e}")