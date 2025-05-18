# 导入所需的模块
import tree_sitter_cpp  # C++ 语法树解析模块
import tree_sitter_python  # Python 语法树解析模块
import tree_sitter_java  # Java 语法树解析模块
import argparse  # 用于解析命令行参数
import os  # 操作系统相关功能
import asyncio  # 异步编程模块
import bisect  # 用于二分查找
import aiofiles  # 异步文件操作模块
import re  # 正则表达式模块
import common_function  # 自定义通用功能模块
import threading  # 多线程模块
from tree_sitter import Language, Parser  # 语法树解析器相关类
from ai_code_reviewer_logger import logger  # 日志记录模块
from ai_module import DeepSeek  # AI 模型模块
from github_assistant import GithubAssistant  # GitHub 辅助工具模块
from typing import Optional  # 类型提示模块

# 定义 C++ 代码分析器类
class CppCodeAnalyzer:
    # 定义所需的环境变量
    require_env_vars = (
        "LLM_API_KEY",  # AI 模型 API 密钥
        "LLM_API_URL",  # AI 模型 API 地址
        "GITHUB_TOKEN",  # GitHub 访问令牌
        "REPOSITORY_NAME",  # 仓库名称
        "REPOSITORY_OWNER",  # 仓库所有者
        "PROMPT_LEVEL"  # 提示级别
    )
    
    # 定义文件扩展名的正则表达式
    cpp_extensions = re.compile(r".*\.(cpp|hpp|h|tpp|cxx)$")  # C++ 文件扩展名
    python_extensions = re.compile(r".*\.py$")  # Python 文件扩展名
    java_extensions = re.compile(r".*\.java$")  # Java 文件扩展名
    
    # 定义线程锁
    lock = threading.Lock()
    
    # 定义信号量，用于控制并发数量
    semaphore = asyncio.Semaphore(os.cpu_count())
    
    # 构造函数，初始化分析器
    def __init__(self, pull_request_id: int):
        # 批量校验环境变量是否已设置
        missing_vars = [var for var in self.require_env_vars 
                       if not os.environ.get(var)]
        if missing_vars:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing_vars)}")
        
        # 初始化日志模块
        common_function.log_init_check()
        
        # 从环境变量中获取所需的参数
        llm_api_key = os.environ.get("LLM_API_KEY")
        llm_api_url = os.environ.get("LLM_API_URL")
        github_token = os.environ.get("GITHUB_TOKEN")
        repository_name = os.environ.get("REPOSITORY_NAME")
        repository_owner = os.environ.get("REPOSITORY_OWNER")
        
        try:
            # 初始化 AI 模型（目前只支持 DeepSeek）
            self.ai_module = DeepSeek(llm_api_url, llm_api_key)
            
            # 初始化 GitHub 辅助工具
            self.github_assistant = GithubAssistant(github_token, 
                                                    repository_owner, 
                                                    repository_name, pull_request_id)
        except Exception as e:
            # 记录异常日志
            logger.exception(f"Init ai_code_reviewer failed: {e}")
            raise
        
        # 初始化语法树解析器
        self._cpp_parser = None
        self._py_parser = None
        self._java_parser = None
        logger.info("Init ai_code_reviewer success")

    # C++ 语法树解析器的属性
    @property
    def cpp_parser(self) -> Parser:
        try:
            with self.lock:  # 确保多线程安全
                if self._cpp_parser is None:
                    self._cpp_parser = Parser(Language(tree_sitter_cpp.language()))
        except Exception as e:
            raise RuntimeError(f"Failed to initialize C++ parser:{e}") from e
        return self._cpp_parser
    
    # Python 语法树解析器的属性
    @property
    def py_parser(self) -> Parser:
        try:
            with self.lock:
                if self._py_parser is None:
                    self._py_parser = Parser(Language(tree_sitter_python.language()))
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Python parser:{e}") from e
        return self._py_parser
    
    # Java 语法树解析器的属性
    @property
    def java_parser(self) -> Parser:
        try:
            with self.lock:
                if self._java_parser is None:
                    self._java_parser = Parser(Language(tree_sitter_java.language()))
        except Exception as e:
            raise RuntimeError(f"Failed to initialize JAVA parser:{e}") from e
        return self._java_parser
    
    # 异步关闭资源
    async def close(self):
        # 释放 AI 模型和 GitHub 辅助工具的资源
        await asyncio.gather(self.ai_module.close(), self.github_assistant.close())
    
    # 分析函数的异步方法
    async def analyze_functions(self, node, lines, file_name):
        new_lines = lines  # 复制行号列表
        
        # 根据文件类型确定函数节点名称
        function_node_name = "function_definition"
        if file_name.endswith(".java"):
            function_node_name = "method_declaration"

        # 检查当前节点是否为函数定义
        if node.type == function_node_name:
            # 获取函数的开始和结束行
            func_start_line = node.start_point[0] + 1  # start_point 是 (行, 列)，索引从 0 开始
            func_end_line = node.end_point[0] + 1

            # 使用二分查找快速定位范围
            left = bisect.bisect_left(new_lines, func_start_line)
            right = bisect.bisect_right(new_lines, func_end_line)
            lines_to_process = new_lines[left:right]
            
            if lines_to_process:
                try:
                    # 提取函数体
                    function_body = self.extract_function_body(node)
                    # 调用 AI 模型处理函数体
                    response = await self.ai_module.call_ai_model(function_body)
                    # 将评论添加到函数变更的第一行
                    self.github_assistant.add_comment(file_name, next(iter(lines_to_process), None), response)
                except Exception as e:
                    # 记录异常日志
                    logger.exception(f"AI processing failed:{e}")
                    raise

            # 批量移除已处理行（维护有序性）
            new_lines = lines[:left] + lines[right:]
                
        # 递归地遍历子节点
        for child in node.children:
            await self.analyze_functions(child, new_lines, file_name)
    
    # 提取函数体的方法
    def extract_function_body(self, node):
        function_body = []  # 初始化函数体列表
        # 递归遍历子节点，提取函数体的语法内容
        for child in node.children:
            text = getattr(child, "text", None)
            if text is None:
                continue  # 跳过无 text 属性的子节点
            try:
                # 统一处理字节类型或字符串类型
                decoded = text.decode("utf-8", errors="replace") if isinstance(text, bytes) else str(text)
                function_body.append(decoded)
            except Exception as e:
                # 跳过解码失败的项
                continue  # FIXME: 简单的跳过可能导致函数提取不完整
        
        return "\n".join(function_body)  # 返回函数体字符串

    # 分析单个文件的异步方法
    async def analyze(self, diff_file_struct):
        async with self.semaphore:  # 控制并发数量
            try:
                # 进行文件过滤
                file_name = diff_file_struct.file_name
                if self.cpp_extensions.match(file_name):
                    parser = self.cpp_parser
                elif self.python_extensions.match(file_name):
                    parser = self.py_parser
                elif self.java_extensions.match(file_name):
                    parser = self.java_parser
                else:
                    return  # 如果文件类型不支持，则直接返回
                
                # 统一处理逻辑
                try:
                    logger.info(f"Start review file:{file_name}")
                    
                    # 异步读取文件
                    async with aiofiles.open(diff_file_struct.file_path, 'r') as f:
                        code = await f.read()
                    
                    # 语法树解析
                    tree = parser.parse(bytes(code, 'utf-8'))
                    root_node = tree.root_node
                    
                    # AST 遍历
                    lines = diff_file_struct.diff_position
                    lines.sort()
                    await self.analyze_functions(
                        root_node, 
                        lines,
                        file_name
                    )
                    
                except IOError as e:
                    # 记录文件读取异常
                    logger.exception(f"File read error:{file_name}, error: {e}")
                except ValueError as e:
                    # 记录解析异常
                    logger.exception(f"Parsing error{file_name}, error: {e}")                    
            except Exception as e:
                # 记录未知异常
                logger.exception(f"Unknown error: error: {file_name}, error: {e}")
    
    # 分析代码的异步方法
    async def analyze_code(self, diff_file_struct_list):
        # 并发执行文件分析
        await asyncio.gather(*[self.analyze(f) for f in diff_file_struct_list], return_exceptions=True)

# 异步主函数
async def async_main(pull_request_id: int):
    analyzer = CppCodeAnalyzer(pull_request_id)  # 初始化代码分析器
    try:
        # 获取差异文件结构
        diff_files = analyzer.github_assistant.get_diff_file_structs()
        if not diff_files:
            logger.warning(f"No files available for review")
            return
        # 分析代码
        await analyzer.analyze_code(diff_files)
    except Exception as e:
        logger.exception(f"Unknown error:{e}")
        raise
    finally:
        # 释放资源
        await analyzer.close()

# 参数验证函数
def validate_args(args) -> int:
    # 验证 pull_request_id 参数
    if hasattr(args, 'pull_request_id'):
        if args.pull_request_id <= 0:
            raise ValueError("Pull request id must be greater than 0")
        return args.pull_request_id
    else:
        raise Exception("Error: Missing pull_request_id parameter")

# 主函数
def main():
    parser = argparse.ArgumentParser()  # 创建命令行参数解析器
    parser.add_argument("pull_request_id", type=int, help="pull request id")  # 添加 pull_request_id 参数
    parser.add_argument("--debug", type=bool, help="debug mode", required=False)  # 添加 debug 参数（可选）
    
    try:
        args = parser.parse_args()  # 解析命令行参数
        if (pr_id := validate_args(args)) is None:  # 验证参数
            return
            
        logger.info(f"Start review pull request {pr_id}'s code")  # 记录日志
        
        # 根据 debug 参数决定是否启用调试模式
        if hasattr(args, 'debug') and args.debug:
            asyncio.run(async_main(pr_id), debug=True)
        else:
            asyncio.run(async_main(pr_id))
        
    except (ValueError, argparse.ArgumentError) as e:
        logger.exception(f"parameter error:{e}")  # 记录参数错误
        raise
    except Exception as e:
        logger.exception(f"processing error:{e}")  # 记录处理错误
        raise

# 程序入口
if __name__ == "__main__":
    main()