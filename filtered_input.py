def filter_symbol(char):
    """
    过滤单个任意符号和空白字符

    参数:
    char: 要检查的字符

    返回:
    bool: 如果是单个符号或空白则返回False，否则返回True
    """
    if len(char) == 1 or char=='' or char==' ' or char==" " or char=="Yeah.":
        print('单个符号或空白返回的False')
        return False

    # 检查是否为空白字符（空格、制表符、换行等）
    if char.isspace():
        print('为空白字符（空格、制表符、换行等）返回的False')
        return False

    return True