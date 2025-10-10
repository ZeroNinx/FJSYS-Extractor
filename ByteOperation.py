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
        # 使用 latin-1 解码可以保留 0-255 原始字节到对应字符，不会丢失高位字节
        string_data = byte_data.decode('latin-1', errors='ignore')  # 保留原始字节映射
        
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
        # 对文件名使用 latin-1 解码以避免丢失非 ASCII 字节
        result_string = byte_data.decode('latin-1', errors='ignore')  # 忽略无法解码的字节
        
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
