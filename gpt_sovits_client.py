"""
GPT-SoVITS API 客户端
用于在另一个Python环境中调用GPT-SoVITS的语音合成API
"""

import requests
import os
from pathlib import Path


class GPTSoVITSClient:
    """GPT-SoVITS API 客户端"""
    
    def __init__(self, api_url="http://127.0.0.1:9880"):
        """
        初始化客户端
        
        Args:
            api_url: API服务地址，默认为 http://127.0.0.1:9880
        """
        self.api_url = api_url
        self.tts_endpoint = f"{api_url}/tts"
        self.set_gpt_weights_endpoint = f"{api_url}/set_gpt_weights"
        self.set_sovits_weights_endpoint = f"{api_url}/set_sovits_weights"
        
    def text_to_speech(
        self,
        text,
        ref_audio_path,
        output_path="output.wav",
        text_lang="zh",
        prompt_text="",
        prompt_lang="zh",
        top_k=5,
        top_p=1.0,
        temperature=1.0,
        text_split_method="cut4",
        batch_size=1,
        speed_factor=1.0,
        streaming_mode=False,
        media_type="wav",
        sample_steps=4,
    ):
        """
        文字转语音
        
        Args:
            text: 要合成的文本（必填）
            ref_audio_path: 参考音频路径（必填）
            output_path: 输出音频文件路径，默认为 output.wav
            text_lang: 文本语言，支持: zh/中文, en/英文, ja/日文, ko/韩文, yue/粤语, auto/自动
            prompt_text: 参考音频的文本内容（可选）
            prompt_lang: 参考音频的语言（必填）
            top_k: top_k采样参数
            top_p: top_p采样参数
            temperature: 温度参数，控制随机性
            text_split_method: 文本切分方法，可选: cut0, cut1, cut2, cut3, cut4, cut5
            batch_size: 批处理大小
            speed_factor: 语速控制，1.0为正常速度
            streaming_mode: 是否使用流式模式
            media_type: 音频格式，支持: wav, ogg, aac
            sample_steps: 采样步数（v3/v4模型使用）
            
        Returns:
            bool: 是否成功
        """
        
        # 检查参考音频是否存在
        if not os.path.exists(ref_audio_path):
            print(f"❌ 错误: 参考音频文件不存在: {ref_audio_path}")
            return False
        
        # 构建请求参数
        params = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "top_k": top_k,
            "top_p": top_p,
            "temperature": temperature,
            "text_split_method": text_split_method,
            "batch_size": batch_size,
            "speed_factor": speed_factor,
            "streaming_mode": streaming_mode,
            "media_type": media_type,
            "sample_steps": sample_steps,
        }
        
        try:
            print(f"🎙️ 正在合成语音...")
            print(f"   文本: {text[:50]}..." if len(text) > 50 else f"   文本: {text}")
            print(f"   参考音频: {ref_audio_path}")
            
            # 发送POST请求
            response = requests.post(
                self.tts_endpoint,
                json=params,
                timeout=300  # 5分钟超时
            )
            
            # 检查响应状态
            if response.status_code == 200:
                # 保存音频文件
                with open(output_path, "wb") as f:
                    f.write(response.content)
                #print(f"✅ 成功! 音频已保存到: {output_path}")
                return True
            else:
                print(f"❌ 失败! HTTP状态码: {response.status_code}")
                try:
                    error_info = response.json()
                    print(f"   错误信息: {error_info}")
                except:
                    print(f"   错误信息: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ 错误: 无法连接到API服务 {self.api_url}")
            print("   请确保GPT-SoVITS API服务已经启动!")
            return False
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return False
    
    def change_gpt_weights(self, weights_path):
        """
        切换GPT模型权重
        
        Args:
            weights_path: GPT模型权重路径
            
        Returns:
            bool: 是否成功
        """
        try:
            response = requests.get(
                self.set_gpt_weights_endpoint,
                params={"weights_path": weights_path},
                timeout=60
            )
            if response.status_code == 200:
                print(f"✅ GPT模型已切换到: {weights_path}")
                return True
            else:
                print(f"❌ 切换GPT模型失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return False
    
    def change_sovits_weights(self, weights_path):
        """
        切换SoVITS模型权重
        
        Args:
            weights_path: SoVITS模型权重路径
            
        Returns:
            bool: 是否成功
        """
        try:
            response = requests.get(
                self.set_sovits_weights_endpoint,
                params={"weights_path": weights_path},
                timeout=60
            )
            if response.status_code == 200:
                print(f"✅ SoVITS模型已切换到: {weights_path}")
                return True
            else:
                print(f"❌ 切换SoVITS模型失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return False


# ========== 使用示例 ==========

def example_basic():
    """基础使用示例"""
    print("=" * 60)
    print("示例1: 基础文字转语音")
    print("=" * 60)
    
    # 创建客户端
    client = GPTSoVITSClient(api_url="http://127.0.0.1:9880")
    
    # 准备参数
    text = "你好，我是基于GPT-SoVITS训练的语音合成模型。"
    ref_audio_path = "参考音频.wav"  # 替换为你的参考音频路径
    output_path = "输出语音.wav"
    
    # 调用API进行语音合成
    success = client.text_to_speech(
        text=text,
        ref_audio_path=ref_audio_path,
        output_path=output_path,
        text_lang="zh",  # 中文
        prompt_lang="zh",
        prompt_text="这是参考音频的文本内容",  # 参考音频说的内容
    )
    
    if success:
        print(f"\n🎉 语音合成成功!")
    else:
        print(f"\n❌ 语音合成失败!")


def example_advanced():
    """高级使用示例 - 使用更多参数"""
    print("=" * 60)
    print("示例2: 高级参数设置")
    print("=" * 60)
    
    client = GPTSoVITSClient()
    
    # 使用更多参数进行精细控制
    success = client.text_to_speech(
        text="这是一段需要合成的长文本。可以包含多个句子。系统会自动进行切分处理。",
        ref_audio_path="参考音频.wav",
        output_path="高级输出.wav",
        text_lang="zh",
        prompt_lang="zh",
        prompt_text="参考音频文本",
        top_k=10,           # 更大的采样范围
        top_p=0.9,          # 控制采样概率
        temperature=1.2,    # 更高的随机性
        speed_factor=1.1,   # 加快10%语速
        text_split_method="cut5",  # 使用cut5切分方法
        batch_size=4,       # 增大批处理
        sample_steps=32,    # v4模型采样步数
    )


def example_batch_processing():
    """批量处理示例"""
    print("=" * 60)
    print("示例3: 批量文字转语音")
    print("=" * 60)
    
    client = GPTSoVITSClient()
    
    # 要合成的文本列表
    texts = [
        "第一句话要合成的内容。",
        "第二句话要合成的内容。",
        "第三句话要合成的内容。",
    ]
    
    ref_audio_path = "参考音频.wav"
    
    # 批量处理
    for i, text in enumerate(texts, 1):
        output_path = f"输出_{i}.wav"
        print(f"\n正在处理第 {i}/{len(texts)} 条...")
        
        client.text_to_speech(
            text=text,
            ref_audio_path=ref_audio_path,
            output_path=output_path,
            text_lang="zh",
            prompt_lang="zh",
        )


def example_change_model():
    """切换模型示例"""
    print("=" * 60)
    print("示例4: 动态切换模型")
    print("=" * 60)
    
    client = GPTSoVITSClient()
    
    # 切换到其他训练好的模型
    client.change_gpt_weights("GPT_weights_v4/另一个模型.ckpt")
    client.change_sovits_weights("SoVITS_weights_v4/另一个模型.pth")
    
    # 使用新模型进行合成
    client.text_to_speech(
        text="使用新模型合成的语音。",
        ref_audio_path="参考音频.wav",
        output_path="新模型输出.wav",
        text_lang="zh",
        prompt_lang="zh",
    )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GPT-SoVITS API 客户端")
    print("=" * 60)
    print("\n⚠️  使用前请确保:")
    print("1. GPT-SoVITS API服务已经启动 (运行 start_api_server.bat)")
    print("2. 参考音频文件路径正确")
    print("3. 参考音频是清晰的人声，时长3-10秒最佳")
    print("\n")
    
    # 运行示例（取消注释你想运行的示例）
    # example_basic()           # 基础示例
    # example_advanced()        # 高级示例
    # example_batch_processing() # 批量处理示例
    # example_change_model()    # 切换模型示例
    
    print("\n💡 提示: 请编辑此文件，取消注释相应的示例函数来运行测试")

