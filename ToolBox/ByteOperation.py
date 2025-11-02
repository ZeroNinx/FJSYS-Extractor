import os
import struct


def _resolve_file(file_path, file_obj):
    # 返回可复用的文件句柄，并标记是否需要调用方关闭
    if file_obj is not None:
        return file_obj, False
    return open(file_path, 'rb'), True


def read_byte(file_path, start_offset, *, file_obj=None):
    # 读取指定偏移处的单字节，可复用现有文件句柄
    file_handle, should_close = _resolve_file(file_path, file_obj)
    try:
        file_handle.seek(start_offset)
        data = file_handle.read(1)
        if len(data) != 1:
            raise ValueError(f"Failed to read 1 byte at offset {start_offset}.")
        return data
    finally:
        if should_close:
            file_handle.close()


def read_int16(file_path, offset, *, signed=False, file_obj=None):
    # 读取 16 位整数，默认按无符号解析以匹配头部字段
    file_handle, should_close = _resolve_file(file_path, file_obj)
    try:
        file_handle.seek(offset)
        byte_data = file_handle.read(2)
        if len(byte_data) != 2:
            raise ValueError(f"Failed to read 2 bytes at offset {offset}.")
        fmt = '<h' if signed else '<H'
        return struct.unpack(fmt, byte_data)[0]
    finally:
        if should_close:
            file_handle.close()


def read_int32(file_path, offset, *, signed=False, file_obj=None):
    # 读取 32 位整数，默认按无符号解析以匹配归档元数据
    file_handle, should_close = _resolve_file(file_path, file_obj)
    try:
        file_handle.seek(offset)
        byte_data = file_handle.read(4)
        if len(byte_data) != 4:
            raise ValueError(f"Failed to read 4 bytes at offset {offset}.")
        fmt = '<i' if signed else '<I'
        return struct.unpack(fmt, byte_data)[0]
    finally:
        if should_close:
            file_handle.close()


def read_string(file_path, start_offset, length, *, file_obj=None):
    # 按指定长度读取字符串，使用 latin-1 保留高位字节
    file_handle, should_close = _resolve_file(file_path, file_obj)
    try:
        file_handle.seek(start_offset)
        byte_data = file_handle.read(length)
        if len(byte_data) != length:
            raise ValueError(f"Failed to read {length} bytes at offset {start_offset}.")
        return byte_data.decode('latin-1', errors='ignore')
    finally:
        if should_close:
            file_handle.close()


def read_string_until_null(file_path, start_offset, *, file_obj=None, max_length=4096):
    # 自偏移位置读取直到遇到空字符或 EOF，为防止损坏数据设置最大长度
    file_handle, should_close = _resolve_file(file_path, file_obj)
    try:
        file_handle.seek(start_offset)
        byte_data = bytearray()
        for _ in range(max_length):
            byte = file_handle.read(1)
            if not byte:
                break
            if byte == b'\0':
                break
            byte_data.extend(byte)
        else:
            raise ValueError(f"String read at offset {start_offset} exceeded maximum length {max_length}.")
        return byte_data.decode('latin-1', errors='ignore')
    finally:
        if should_close:
            file_handle.close()


def extract_bytes_to_file(input_file_path, output_file_path, start_offset, num_bytes):
    # 将指定字节区间写入新文件，确保父目录存在且读取完整
    with open(input_file_path, 'rb') as input_file:
        input_file.seek(start_offset)
        byte_data = input_file.read(num_bytes)
        if len(byte_data) != num_bytes:
            raise ValueError(f"Failed to read {num_bytes} bytes at offset {start_offset}.")
    parent_dir = os.path.dirname(output_file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(output_file_path, 'wb') as output_file:
        output_file.write(byte_data)
