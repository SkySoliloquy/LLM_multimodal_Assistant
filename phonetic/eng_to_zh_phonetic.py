"""
英文转中文谐音预处理模块
功能：将文本中的英文单词/字母转换为中文谐音，保持中文和其他文本不变
"""

import re
from typing import Dict, List, Tuple


class EngToZhPhonetic:
    """英文转中文谐音转换器"""
    
    def __init__(self, mapping_file: str = None):
        """
        初始化转换器
        
        Args:
            mapping_file: 热词映射文件路径（必需，用于加载热词映射）
                          如果不提供，则只使用基础字母发音替换
        """
        # 单个字母到中文谐音的映射（基础发音替换）
        self.letter_map = {
            'A': '诶', 'B': '比', 'C': '西', 'D': '地', 'E': '伊',
            'F': '艾夫', 'G': '基', 'H': '艾尺', 'I': '艾', 'J': '杰',
            'K': '开', 'L': '艾勒', 'M': '艾姆', 'N': '艾恩', 'O': '哦',
            'P': '皮', 'Q': '丘', 'R': '阿尔', 'S': '艾斯', 'T': '提',
            'U': '由', 'V': '维', 'W': '达不溜', 'X': '艾克斯', 'Y': '外', 'Z': '贼',
            'a': '诶', 'b': '比', 'c': '西', 'd': '地', 'e': '伊',
            'f': '艾夫', 'g': '基', 'h': '艾尺', 'i': '艾', 'j': '杰',
            'k': '开', 'l': '艾勒', 'm': '艾姆', 'n': '艾恩', 'o': '哦',
            'p': '皮', 'q': '丘', 'r': '阿尔', 's': '艾斯', 't': '提',
            'u': '由', 'v': '维', 'w': '达不溜', 'x': '艾克斯', 'y': '外', 'z': '贼'
        }
        
        # 热词到中文谐音的映射（从文件加载，支持大小写不敏感匹配）
        # 键为大写版本，值存储原始大小写版本和对应的谐音
        self.word_map = {}  # 格式: {大写键: {'phonetic': 谐音, 'original': 原始大小写}}
        
        # 如果提供了映射文件，加载它
        if mapping_file:
            self.load_custom_mapping(mapping_file)
    
    def load_custom_mapping(self, file_path: str):
        """
        从文件加载自定义热词映射
        
        文件格式：
        AI=诶艾
        ML=艾姆艾勒
        ai=诶艾  (支持小写)
        或
        AI 诶艾
        ML 艾姆艾勒
        
        注意：加载的热词支持大小写不敏感匹配
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # 支持两种格式：KEY=VALUE 或 KEY VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                    else:
                        parts = line.split(None, 1)
                        if len(parts) >= 2:
                            key, value = parts[0], parts[1]
                        else:
                            continue
                    
                    original_key = key.strip()  # 保留原始大小写
                    key_upper = original_key.upper()  # 用于索引
                    value = value.strip()
                    
                    if key_upper and value:
                        # 存储原始大小写和对应的谐音
                        self.word_map[key_upper] = {
                            'phonetic': value,
                            'original': original_key
                        }
        except FileNotFoundError:
            print(f"警告: 映射文件 {file_path} 不存在，将只使用基础字母发音替换")
        except Exception as e:
            print(f"警告: 加载映射文件时出错: {e}")
    
    def is_english_word(self, text: str) -> bool:
        """判断文本是否为纯英文单词"""
        # 匹配纯英文单词（可能包含数字和常见符号）
        pattern = r'^[A-Za-z0-9\-_\.]+$'
        return bool(re.match(pattern, text)) and any(c.isalpha() for c in text)
    
    def convert_word_to_phonetic(self, word: str) -> str:
        """
        将单个英文单词转换为中文谐音
        
        Args:
            word: 英文单词
            
        Returns:
            中文谐音字符串
        """
        # 先检查是否在热词映射表中（不区分大小写）
        word_upper = word.upper()
        if word_upper in self.word_map:
            return self.word_map[word_upper]['phonetic']
        
        # 如果不在映射表中，按字母逐个转换
        result = []
        for char in word:
            if char in self.letter_map:
                result.append(self.letter_map[char])
            elif char.isdigit():
                # 数字保持原样或转换为中文数字（可选）
                result.append(char)
            else:
                # 其他字符（如标点）保持原样
                result.append(char)
        
        return ''.join(result)
    
    def convert_text(self, text: str, convert_mode: str = 'smart') -> str:
        """
        将文本中的英文转换为中文谐音
        
        Args:
            text: 原始文本
            convert_mode: 转换模式
                - 'smart': 智能模式，只转换全大写的英文单词或自定义热词（支持大小写），直接替换
                - 'all': 转换所有英文（包括单词中的字母）
                - 'preserve': 保留原文本，在英文后添加谐音（格式：英文(谐音)），仅全大写或热词
        
        Returns:
            转换后的文本
        """
        if convert_mode == 'smart':
            return self._convert_smart(text)
        elif convert_mode == 'all':
            return self._convert_all(text)
        elif convert_mode == 'preserve':
            return self._convert_preserve(text)
        else:
            raise ValueError(f"不支持的转换模式: {convert_mode}")
    
    def _convert_smart(self, text: str) -> str:
        """智能模式：只转换全大写的英文单词或自定义热词（支持大小写）"""
        # 使用正则表达式匹配英文单词（包括缩写）
        # 匹配：前面是中文、标点、空格或字符串开头，后面是中文、标点、空格或字符串结尾
        # 这样可以匹配中文文本中的英文单词（支持大小写）
        pattern = r'(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9_\-\.]*(?![A-Za-z0-9])'
        
        def replace_word(match):
            word = match.group(0)
            word_upper = word.upper()
            
            # 检查是否在自定义热词映射表中（支持大小写不敏感匹配）
            if word_upper in self.word_map:
                return self.word_map[word_upper]['phonetic']
            
            # 检查是否全大写（至少1个字符，且包含字母）
            if len(word) >= 1 and word.isupper() and any(c.isalpha() for c in word):
                # 按字母逐个转换
                result = []
                for char in word:
                    if char in self.letter_map:
                        result.append(self.letter_map[char])
                    elif char.isdigit():
                        result.append(char)
                    else:
                        result.append(char)
                return ''.join(result)
            
            # 其他情况不转换
            return word
        
        result = re.sub(pattern, replace_word, text)
        return result
    
    def _convert_all(self, text: str) -> str:
        """全部转换模式：转换所有英文字母"""
        result = []
        for char in text:
            if char in self.letter_map:
                result.append(self.letter_map[char])
            else:
                result.append(char)
        return ''.join(result)
    
    def _convert_preserve(self, text: str) -> str:
        """保留模式：在英文后添加谐音（仅全大写或热词，支持大小写）"""
        # 匹配英文单词（支持大小写）
        pattern = r'(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9_\-\.]*(?![A-Za-z0-9])'
        
        def replace_word(match):
            word = match.group(0)
            word_upper = word.upper()
            
            # 检查是否在自定义热词映射表中（支持大小写不敏感匹配）
            if word_upper in self.word_map:
                return f"{word}({self.word_map[word_upper]['phonetic']})"
            
            # 检查是否全大写（至少1个字符，且包含字母）
            if len(word) >= 1 and word.isupper() and any(c.isalpha() for c in word):
                # 按字母逐个转换
                result = []
                for char in word:
                    if char in self.letter_map:
                        result.append(self.letter_map[char])
                    elif char.isdigit():
                        result.append(char)
                    else:
                        result.append(char)
                phonetic = ''.join(result)
                return f"{word}({phonetic})"
            
            # 其他情况不转换
            return word
        
        result = re.sub(pattern, replace_word, text)
        return result
    
    def add_word_mapping(self, word: str, phonetic: str):
        """添加自定义单词映射（支持大小写不敏感匹配）"""
        word_upper = word.upper()
        self.word_map[word_upper] = {
            'phonetic': phonetic,
            'original': word
        }
    
    def add_letter_mapping(self, letter: str, phonetic: str):
        """添加自定义字母映射"""
        self.letter_map[letter] = phonetic
        if letter.isupper():
            self.letter_map[letter.lower()] = phonetic
        elif letter.islower():
            self.letter_map[letter.upper()] = phonetic


# 便捷函数
def convert_eng_to_zh_phonetic(text: str, mapping_file: str = None, convert_mode: str = 'smart') -> str:
    """
    便捷函数：将文本中的英文转换为中文谐音
    
    Args:
        text: 原始文本
        mapping_file: 热词映射文件路径（可选，如果不提供则只使用基础字母发音替换）
        convert_mode: 转换模式 ('smart', 'all', 'preserve')
    
    Returns:
        转换后的文本
    
    Example:
        >>> convert_eng_to_zh_phonetic("我使用AI技术", mapping_file='mapping.txt', convert_mode='smart')
        '我使用诶艾技术'
        
        >>> convert_eng_to_zh_phonetic("AI is great", mapping_file='mapping.txt', convert_mode='preserve')
        'AI(诶艾) is great'
    """
    converter = EngToZhPhonetic(mapping_file)
    return converter.convert_text(text, convert_mode)


if __name__ == "__main__":
    # 测试示例
    # 注意：需要提供映射文件才能测试热词转换
    import os
    
    mapping_file = 'eng_to_zh_phonetic_mapping.txt'
    if os.path.exists(mapping_file):
        converter = EngToZhPhonetic(mapping_file)
    else:
        print("警告: 未找到映射文件，将只使用基础字母发音替换")
        converter = EngToZhPhonetic()
    
    test_texts = [
        "我使用AI技术进行机器学习",
        "The AI model is trained on GPU",
        "访问 https://example.com 获取API",
        "使用ML和DL算法",
        "CPU和GPU的性能对比",
        "我使用ai技术",  # 测试小写热词
        "使用gpu加速",   # 测试小写热词
    ]
    
    print("=" * 60)
    print("英文转中文谐音测试")
    print("=" * 60)
    
    for text in test_texts:
        print(f"\n原文: {text}")
        print(f"智能模式: {converter.convert_text(text, 'smart')}")
        print(f"保留模式: {converter.convert_text(text, 'preserve')}")
        print("-" * 60)

