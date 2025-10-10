import struct

def read_byte(file_path, start_offset):
    # 打开文件并读取指定的字节
    with open(file_path, 'rb') as file:
        file.seek(start_offset)
        byte = file.read(1)
        return byte

def read_int32(file_path, offset):
    # 打开文件并读取指定的字节
    with open(file_path, 'rb') as file:
        # 跳过前面54个字节
        file.seek(offset)
        
        # 读取接下来的 num_ints * 4 字节（每个 int 占 4 字节）
        byte_data = file.read(4)
        
        # 输出每4 字节的整数值
        # 使用 struct 解包按小端格式（<i表示4字节的有符号int）
        value = struct.unpack('<i', byte_data[0:4])[0]
        return value

def read_string(file_path, start_offset, length):
    with open(file_path, 'rb') as file:
        # 跳过前面 start_offset 个字节
        file.seek(start_offset)
        
        # 读取接下来的 `length` 字节
        byte_data = file.read(length)
        
        # 将字节转换为字符串
        string_data = byte_data.decode('ASCII', errors='ignore')  # 选择适合的解码方式
        
        return string_data

def read_string_until_null(file_path, start_offset):
    with open(file_path, 'rb') as file:
        # 跳到指定的偏移位置
        file.seek(start_offset)
        
        # 读取字节直到遇到 null 字符（\0）
        byte_data = bytearray()
        while True:
            byte = file.read(1)
            if not byte:  # 文件末尾或读取失败
                break
            if byte == b'\0':  # 遇到 null 字符，停止读取
                break
            byte_data.extend(byte)  # 将字节添加到 byte_data 中
        
        # 将字节转换为字符串
        result_string = byte_data.decode('ASCII', errors='ignore')  # 忽略无法解码的字节
        
        return result_string

def extract_bytes_to_file(input_file_path, output_file_path, start_offset, num_bytes):
    # 打开输入文件并读取指定的字节
    with open(input_file_path, 'rb') as input_file:
        # 跳过前面 start_offset 个字节
        input_file.seek(start_offset)
        
        # 读取接下来的 num_bytes 个字节
        byte_data = input_file.read(num_bytes)
        
        # 将读取的字节写入输出文件
        with open(output_file_path, 'wb') as output_file:
            output_file.write(byte_data)
    
    print(f"Extracted {num_bytes} bytes from {input_file_path} starting at offset {start_offset} and saved to {output_file_path}")

# 文件路径
file_path = 'MGD.BAK'

class file_item:
    def __init__(self, filename_offset, file_size, file_offset):
        self.filename_offset = filename_offset
        self.file_size = file_size
        self.file_offset = file_offset

file_list = []

def parse_header():
    filelist_offset = 84
    item_index = 0
    item_offset = filelist_offset + item_index * (4*4)
    item_tail = item_offset + 3*4 #4字节一组，以0结尾 
    while read_int32(file_path, item_tail) == 0:
        filename_offset = read_int32(file_path, item_offset)
        file_size = read_int32(file_path, item_offset + 4)
        file_offset = read_int32(file_path, item_offset + 2*4)

        print("---")
        print(f"Item = {item_index}")
        print(f"filename_offset = {filename_offset}")
        print(f"file_size = {file_size}")
        print(f"file_offset = {file_offset}")
        print("---")
        file_list.append(file_item(filename_offset, file_size, file_offset))

        item_index = item_index + 1
        item_offset = filelist_offset + item_index * (4*4)
        item_tail = item_offset + 3*4 #4字节一组，以0结尾 

    # 文件列表结束，开始读取文件名
    filename_list_offset = item_offset
    for index, item in enumerate(file_list):
        filename = ""
        char_offset = filename_list_offset + item.filename_offset
        filename = read_string_until_null(file_path, char_offset)
        print(f"File {index}: {filename}, size: {item.file_size}, offset: {item.file_offset}")
        extract_bytes_to_file(file_path, filename + ".png", item.file_offset+96, item.file_size-96)
        

parse_header()
