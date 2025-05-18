import httpx
import json
import os
import aiohttp
import common_function
from ai_code_reviewer_logger import logger
from httpx import AsyncClient
from openai import OpenAI

def read_json_file(file_path : str) -> dict: 
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        logger.info("JSON file loaded successfully:")
        return data
        
    except FileNotFoundError:
        logger.exception(f"Error: File {file_path} not found. Please check if the path is correct.")
        raise
    except json.JSONDecodeError as e:
        logger.exception(f"Error: Invalid JSON format, unable to parse:{e}, file path:{file_path}")
        raise
    except PermissionError:
        logger.exception(f"Error: No permission to read the file {file_path}. Please check file permissions.")
        raise
    except Exception as e:
        logger.exception(f"An unknown error occurred:{e}, file path:{file_path}")
        raise


class DeepSeek:
    
    # 默认提示词为lever_0
    DEFAULT_PROMPT = """你是一名经验丰富的计算机工程师，请从专业的角度，对以下代码进行review，对于不完善的地方，请提出针对性的优化建议。
                                  在给出意见时请保持语言的简洁，只需对可能导致程序严重错误的地方提出修改建议，无需给出示例代码。
                                  review 时不需要吹毛求疵，如果没有更好的优化建议，建议的内容可以为空"""
    
    def __init__(self, url:str, key:str):
        # 参数校验
        common_function.parameter_check(url, "url")
        common_function.parameter_check(key, "api key")
        
        common_function.log_init_check()
        
        # 安全赋值
        self.api_url = url.strip()
        # 私有变量保护敏感数据
        self._api_key = key.strip()
        
        # 这个超时时间给的比较长是因为LLM的应答速度可能较慢
        try: 
            self.client = AsyncClient(trust_env=False, proxy=None, timeout=1000)
        except Exception as e:
            logger.exception(f"Init async client error:{e}")
            raise RuntimeError("Init async client error") from e
        
        self.prompt = read_json_file("./prompt_level_configure.json")
        

        logger.info("Init ai model deepseek success")
        
        
    # 这个函数貌似没真正生效
    @property
    def api_key(self):
        # 对api key进行隐藏
        if len(self._api_key) > 10:
            return f"****{self._api_key[-4:]}" if self._api_key else None
        return None
    
    async def close(self):
        # 释放api key，防止其在内存中驻留
        self._api_key = None  # 主动清除敏感数据
        await self.client.aclose() # 主动释放链接
        self.client = None
        

    
    async def call_deepseek_async2(self, prompt: str) -> any:
        # 步调用 DeepSeek API 并返回结果
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-r1-250120",
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            response = await self.client.post(
                self.api_url,
                json=payload,
                headers=headers)
    
            response.raise_for_status()  # 自动触发HTTPError 
            response_json = response.json()     # FIXME:相应体较大未考虑   
            # await response.close()
            return response_json
        
        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error:{e}")
            raise
        except httpx.RequestError as e:
            logger.exception(f"Network error:{e}")
            raise
        except json.JSONDecodeError as e:
            logger.exception(f"Invalid JSON response:{e}")
            raise
        except Exception as e:
            logger.exception(f"Unknown Error:{e}")
            raise
        finally:
            if response:
                await response.aclose()
    # 修改的地方：将 call_deepseek_async 方法改为使用 OpenAI 客户端
    async def call_deepseek_async(self, prompt: str) -> any:
        # 初始化 OpenAI 客户端
        openai_client = OpenAI(api_key=self._api_key, base_url=self.api_url)

        # 构造请求负载
        payload = {
            "model": "deepseek-chat",  # 修改模型名称以匹配官方示例
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},  # 添加系统角色的消息
                {"role": "user", "content": prompt}  # 用户的消息
            ],
            "stream": False  # 添加 stream 参数
        }

        try:
            # 使用 OpenAI 客户端发送请求
            response = openai_client.chat.completions.create(**payload)
            # 返回响应内容
            return response.choices[0].message.content

        except Exception as e:
            # 捕获并记录异常
            logger.exception(f"Error calling DeepSeek API: {e}")
            raise


    async def call_ai_model(self, code_content):
        logger.info("Start call ai model")
        
        #主函数，调用 DeepSeek 并输出结果
        prompt_level = os.environ.get("PROMPT_LEVEL")
        if isinstance(prompt_level, str) and prompt_level in self.prompt:
            full_prompt = f"{self.prompt[prompt_level]}\n{code_content}"
        else:
            full_prompt = f"{self.DEFAULT_PROMPT}\n{code_content}"
        
        logger.debug(f"Request content:{full_prompt}")
        
        try:
            response = await self.call_deepseek_async(full_prompt)
            logger.debug(f"DeepSeek Response:{response}")
        except httpx.HTTPError as e:
            logger.exception(f"Call ai model error:{e}")
            raise
        except Exception as e:
            logger.exception(f"Unknown Error:{e}")
            raise
        
        
        if isinstance(response, dict) and ("choices" in response and response["choices"]):
            if len(response["choices"]) > 0:
                response_str = response["choices"][0]["message"]["content"]
                return response_str
            else:
                return "AI model response error1: No choices found in response"
        elif isinstance(response, str):
            # 如果响应是字符串，直接返回
            return response
        else:
            return "AI model response error2: Unexpected response type"
        
# import asyncio

# async def test_call_deepseek_async():
#     API_URL = "https://api.deepseek.com"  # 替换为你的实际 API URL
#     API_KEY = ""  # 替换为你的实际 API Key

#     deepseek = DeepSeek(API_URL, API_KEY)
#     TEST_PROMPT = "你是一名经验丰富的计算机工程师，请从专业的角度，对以下代码进行review，对于不完善的地方，请提出针对性的优化建议。在给出意见时请保持语言的简洁，只需对可能导致程序严重错误的地方提出修改建议，无需给出示例代码。review 时不需要吹毛求疵，如果没有更好的优化建议，建议的内容可以为空\nint main() { return 0; }"

#     result = await deepseek.call_deepseek_async(TEST_PROMPT)
#     print("Response from DeepSeek API:")
#     print(result)

# if __name__ == "__main__":
#     asyncio.run(test_call_deepseek_async())