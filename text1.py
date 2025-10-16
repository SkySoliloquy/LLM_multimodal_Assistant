# 支持兼容 OpenAI Python SDK  终端运行：pip install OpenAI
from openai import OpenAI
import time
from chat_manager import ChatManager

# 读取系统提示词
with open("system_content.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# 初始化客户端
client = OpenAI(
    api_key= "YDHHpjDZwdGh7SBOgNGn50_LcNLnCpq84tjZ_fRECrs7wwoOG4SWNPyRPsX1Z7Zj7hFZgiJW2MqzDGIl98U-7Q",
    base_url= "https://www.sophnet.com/api/open-apis/v1"
)

# 初始化对话管理器
chat_manager = ChatManager(system_prompt, max_history=10)

def chat_with_stream(user_message):
    """
    发送消息并流式接收回复
    :param user_message: 用户消息
    :return: 助手的完整回复内容
    """
    # 添加用户消息到历史
    chat_manager.add_user_message(user_message)
    
    # 调用接口（流式输出）
    start_time = time.time()  # 记录开始时间
    response = client.chat.completions.create(
        #model="DeepSeek-V3.2-Exp:3vooDCUrblvDcowaNiisqQ",
        #model="DeepSeek-V3.1-Fast:6T3onQ5bZpslwZIiDptJTP",
        model="DeepSeek-V3-Fast:5HpV9XORBHupqPOgslPz2X",
        messages=chat_manager.get_messages(),
        stream=True  # 启用流式输出
    )
    
    # 性能指标
    first_token_time = None
    token_count = 0
    full_content = ""
    
    # 打印结果（流式逐块输出）
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            
            # 记录首个token时间
            if first_token_time is None:
                first_token_time = time.time()
                ttft = first_token_time - start_time
                #print(f"[首Token时间: {ttft:.3f}秒]\n")
            
            # 输出内容
            print(content, end="", flush=True)
            full_content += content
            token_count += 1
    
    # 计算总时间和速率
    end_time = time.time()
    total_time = end_time - start_time
    generation_time = end_time - (first_token_time if first_token_time else start_time)
    
    print("\n")
    print("-" * 50)
    print(f"首Token时间 (TTFT): {ttft:.3f}秒" if first_token_time else "未检测到token")
    print(f"总字符数: {len(full_content)}")
    #print(f"总数据块数: {token_count}")
    #print(f"总耗时: {total_time:.3f}秒")
    if generation_time > 0:
        #print(f"生成速度: {token_count / generation_time:.2f} 数据块/秒")
        print(f"字符速度: {len(full_content) / generation_time:.2f} tokens/秒")
    print("-" * 50)
    
    # 添加助手回复到历史
    chat_manager.add_assistant_message(full_content)
    
    return full_content

def main():
    """主函数：多轮对话循环"""
    print("=" * 50)
    print("多轮对话系统")
    print("=" * 50)
    print("输入 'exit' 或 'quit' 退出")
    print("输入 'clear' 清空对话历史")
    print("输入 'history' 查看对话历史")
    print("=" * 50)
    print()
    
    while True:
        # 获取用户输入
        user_input = input("\n你: ").strip()
        
        # 处理特殊命令
        if user_input.lower() in ['exit', 'quit']:
            print("\n再见！")
            break
        
        if user_input.lower() == 'clear':
            chat_manager.clear_history()
            print("\n✓ 对话历史已清空")
            continue
        
        if user_input.lower() == 'history':
            chat_manager.display_history()
            continue
        
        if not user_input:
            print("请输入有效内容")
            continue
        
        # 发送消息并获取回复
        print("\n助手: ", end="", flush=True)
        chat_with_stream(user_input)

if __name__ == "__main__":
    main()