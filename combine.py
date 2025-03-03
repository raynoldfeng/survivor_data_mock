import os

# 获取当前脚本的文件名
current_script = os.path.basename(__file__)

# 定义输出文件的路径
output_file = "output.txt"

# 允许的文件扩展名列表
allowed_extensions = ['.py', '.csv']

# 打开输出文件以写入内容
with open(output_file, 'w', encoding='utf-8') as outfile:
    # 遍历当前目录及其子目录
    for root, dirs, files in os.walk('.'):
        for file in files:
            # 获取文件的扩展名
            file_extension = os.path.splitext(file)[1]
            # 跳过当前脚本文件、输出文件以及不在允许列表中的文件
            if file == current_script or file == output_file or file_extension not in allowed_extensions:
                continue
            # 获取文件的完整路径
            file_path = os.path.join(root, file)
            print(file_path)
            try:
                # 在输出文件中添加注释行，标识文件路径和文件名
                outfile.write(f"# File path: {file_path}\n")
                # 打开当前文件以读取内容
                with open(file_path, 'r', encoding='utf-8') as infile:
                    # 读取当前文件的内容
                    content = infile.read()
                    # 将当前文件的内容写入输出文件
                    outfile.write(content)
                    # 在每个文件内容后添加一个空行，以便区分不同文件
                    outfile.write('\n')
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

print(f"All .py and .csv files have been combined into {output_file}.")