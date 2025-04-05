import json
import os
import argparse
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
from typing import List, Tuple
import markdown2
from io import BytesIO
import requests
from bs4 import BeautifulSoup

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """将十六进制颜色转换为RGB元组"""
    # 移除#号并确保长度为6
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid color format: {hex_color}")
    
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError as e:
        raise ValueError(f"Invalid color value: {hex_color}") from e

def create_gradient_image(width: int, height: int, colors: List[str], output_path: str, markdown_content: str = None, background_color: str = "#000000", direction: str = "vertical"):
    """创建渐变色图片
    
    Args:
        width: 图片宽度
        height: 图片高度
        colors: 渐变色列表
        output_path: 输出路径
        markdown_content: markdown内容
        background_color: 中心矩形的背景色，默认为黑色 (#000000)
        direction: 渐变方向，可选值：vertical（垂直）、horizontal（水平）、diagonal（对角线），默认为 vertical
    """
    if not colors:
        raise ValueError("No colors provided")
    
    # 创建新图片
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    try:
        # 将十六进制颜色转换为RGB
        rgb_colors = [hex_to_rgb(color) for color in colors]
        # 转换背景色为RGB
        background_rgb = hex_to_rgb(background_color)
    except ValueError as e:
        print(f"Error processing colors: {e}")
        return
    
    # 根据方向创建渐变
    if direction == "vertical":
        steps = height
        for y in range(height):
            t = y / (height - 1)
            color = get_gradient_color(rgb_colors, t)
            draw.line([(0, y), (width, y)], fill=color)
    elif direction == "horizontal":
        steps = width
        for x in range(width):
            t = x / (width - 1)
            color = get_gradient_color(rgb_colors, t)
            draw.line([(x, 0), (x, height)], fill=color)
    else:  # diagonal
        # 使用新的对角线渐变实现
        for y in range(height):
            for x in range(width):
                # 计算对角线位置的比例（从左上到右下）
                # 使用欧几里得距离来创建更平滑的渐变
                dx = x / width
                dy = y / height
                t = (dx + dy) / 2  # 使用平均值来创建更均匀的渐变
                color = get_gradient_color(rgb_colors, t)
                draw.point((x, y), fill=color)

    # 计算圆角矩形的位置和大小
    rect_width = int(width * 0.8)
    rect_height = int(height * 0.8)
    rect_x = (width - rect_width) // 2
    rect_y = (height - rect_height) // 2
    radius = 50  # 增加圆角半径

    # 创建发光效果层
    glow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # 绘制发光效果的圆角矩形（稍大一些）
    glow_rect_width = rect_width + 20
    glow_rect_height = rect_height + 20
    glow_rect_x = (width - glow_rect_width) // 2
    glow_rect_y = (height - glow_rect_height) // 2
    glow_radius = radius + 10

    # 绘制发光效果的四个圆角
    glow_draw.ellipse([glow_rect_x, glow_rect_y, glow_rect_x + glow_radius * 2, glow_rect_y + glow_radius * 2], fill=(0, 0, 0, 100))  # 左上角
    glow_draw.ellipse([glow_rect_x + glow_rect_width - glow_radius * 2, glow_rect_y, glow_rect_x + glow_rect_width, glow_rect_y + glow_radius * 2], fill=(0, 0, 0, 100))  # 右上角
    glow_draw.ellipse([glow_rect_x, glow_rect_y + glow_rect_height - glow_radius * 2, glow_rect_x + glow_radius * 2, glow_rect_y + glow_rect_height], fill=(0, 0, 0, 100))  # 左下角
    glow_draw.ellipse([glow_rect_x + glow_rect_width - glow_radius * 2, glow_rect_y + glow_rect_height - glow_radius * 2, glow_rect_x + glow_rect_width, glow_rect_y + glow_rect_height], fill=(0, 0, 0, 100))  # 右下角

    # 绘制发光效果的矩形主体
    glow_draw.rectangle([glow_rect_x + glow_radius, glow_rect_y, glow_rect_x + glow_rect_width - glow_radius, glow_rect_y + glow_rect_height], fill=(0, 0, 0, 100))  # 中间部分
    glow_draw.rectangle([glow_rect_x, glow_rect_y + glow_radius, glow_rect_x + glow_rect_width, glow_rect_y + glow_rect_height - glow_radius], fill=(0, 0, 0, 100))  # 两侧部分

    # 应用模糊效果
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=10))

    # 绘制主圆角矩形
    # 绘制四个圆角
    draw.ellipse([rect_x, rect_y, rect_x + radius * 2, rect_y + radius * 2], fill=background_rgb)  # 左上角
    draw.ellipse([rect_x + rect_width - radius * 2, rect_y, rect_x + rect_width, rect_y + radius * 2], fill=background_rgb)  # 右上角
    draw.ellipse([rect_x, rect_y + rect_height - radius * 2, rect_x + radius * 2, rect_y + rect_height], fill=background_rgb)  # 左下角
    draw.ellipse([rect_x + rect_width - radius * 2, rect_y + rect_height - radius * 2, rect_x + rect_width, rect_y + rect_height], fill=background_rgb)  # 右下角

    # 绘制矩形主体
    draw.rectangle([rect_x + radius, rect_y, rect_x + rect_width - radius, rect_y + rect_height], fill=background_rgb)  # 中间部分
    draw.rectangle([rect_x, rect_y + radius, rect_x + rect_width, rect_y + rect_height - radius], fill=background_rgb)  # 两侧部分

    # 合并发光效果
    image = Image.alpha_composite(image.convert('RGBA'), glow_layer)

    # 如果有markdown内容，渲染并添加到图片中
    if markdown_content:
        # 设置字体
        try:
            # 尝试使用系统自带的中文字体
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/System/Library/Fonts/STHeiti Light.ttc",  # macOS
                "C:\\Windows\\Fonts\\msyh.ttc",  # Windows
                "C:\\Windows\\Fonts\\simsun.ttc",  # Windows
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
            ]
            
            # 创建不同大小的字体用于不同级别的文本
            fonts = {}
            for font_path in font_paths:
                if os.path.exists(font_path):
                    fonts['h1'] = ImageFont.truetype(font_path, 72)  # 标题字体
                    fonts['h2'] = ImageFont.truetype(font_path, 54)  # 二级标题
                    fonts['normal'] = ImageFont.truetype(font_path, 36)  # 正文字体
                    break
            
            if not fonts:
                fonts = {
                    'h1': ImageFont.load_default(),
                    'h2': ImageFont.load_default(),
                    'normal': ImageFont.load_default()
                }
                print("Warning: Could not find a suitable font for Chinese characters. Text may not display correctly.")
        except Exception as e:
            print(f"Warning: Font loading error: {e}")
            fonts = {
                'h1': ImageFont.load_default(),
                'h2': ImageFont.load_default(),
                'normal': ImageFont.load_default()
            }
        
        # 创建文本层
        text_layer = Image.new('RGBA', (rect_width - 2 * radius, rect_height - 2 * radius), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        
        # 计算文本区域
        text_x = 50  # 增加左边距
        text_y = 50  # 增加上边距
        line_spacing = {
            'h1': 100,  # 标题行间距
            'h2': 80,   # 二级标题行间距
            'normal': 50,  # 正文行间距
            'paragraph': 70  # 段落间距
        }
        text_width = rect_width - 2 * radius - 100  # 减少宽度，留出边距
        text_height = rect_height - 2 * radius - 100  # 减少高度，留出边距
        
        # 将markdown转换为HTML并解析
        # 先处理换行符，将\n替换为HTML的<br>标签
        processed_content = markdown_content.replace('\\n', '\n')  # 处理转义的\n
        processed_content = processed_content.replace('\n', '  \n')  # 在markdown中，两个空格加换行表示换行
        html = markdown2.markdown(processed_content)
        soup = BeautifulSoup(html, 'html.parser')
        
        current_y = text_y
        
        # 遍历HTML元素并渲染
        for element in soup.children:
            if element.name == 'h1':
                # 渲染标题
                text_draw.text((text_x, current_y), element.get_text(), fill=(255, 255, 255), font=fonts['h1'])
                current_y += line_spacing['h1']
            elif element.name == 'h2':
                # 渲染二级标题
                text_draw.text((text_x, current_y), element.get_text(), fill=(255, 255, 255), font=fonts['h2'])
                current_y += line_spacing['h2']
            elif element.name == 'p':
                # 渲染段落，处理段落内的换行
                text = element.get_text()
                lines = text.split('\n')
                for line in lines:
                    if line.strip():  # 如果不是空行
                        text_draw.text((text_x, current_y), line.strip(), fill=(255, 255, 255), font=fonts['normal'])
                        current_y += line_spacing['normal']
                current_y += line_spacing['paragraph'] - line_spacing['normal']  # 添加段落间距
            elif element.name == 'ul':
                # 渲染列表
                for li in element.find_all('li'):
                    # 处理列表项内的换行
                    text = li.get_text()
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip():  # 如果不是空行
                            if i == 0:  # 第一行显示项目符号
                                text_draw.text((text_x + 30, current_y), '•', fill=(255, 255, 255), font=fonts['normal'])
                                text_draw.text((text_x + 60, current_y), line.strip(), fill=(255, 255, 255), font=fonts['normal'])
                            else:  # 后续行缩进对齐
                                text_draw.text((text_x + 60, current_y), line.strip(), fill=(255, 255, 255), font=fonts['normal'])
                            current_y += line_spacing['normal']
                current_y += line_spacing['paragraph'] - line_spacing['normal']  # 列表后添加额外间距
            elif element.name == 'ol':
                # 渲染有序列表
                for i, li in enumerate(element.find_all('li'), 1):
                    # 处理列表项内的换行
                    text = li.get_text()
                    lines = text.split('\n')
                    for j, line in enumerate(lines):
                        if line.strip():  # 如果不是空行
                            if j == 0:  # 第一行显示序号
                                number_text = f"{i}."
                                text_draw.text((text_x + 30, current_y), number_text, fill=(255, 255, 255), font=fonts['normal'])
                                text_draw.text((text_x + 60, current_y), line.strip(), fill=(255, 255, 255), font=fonts['normal'])
                            else:  # 后续行缩进对齐
                                text_draw.text((text_x + 60, current_y), line.strip(), fill=(255, 255, 255), font=fonts['normal'])
                            current_y += line_spacing['normal']
                current_y += line_spacing['paragraph'] - line_spacing['normal']  # 列表后添加额外间距
        
        # 将文本层合并到主图片
        image.paste(text_layer, (rect_x + radius, rect_y + radius), text_layer)

    # 保存图片
    image.save(output_path)
    print(f"Image saved: {output_path}")

def get_gradient_color(rgb_colors: List[Tuple[int, int, int]], t: float) -> Tuple[int, int, int]:
    """计算渐变颜色
    
    Args:
        rgb_colors: RGB颜色列表
        t: 渐变位置（0-1）
    
    Returns:
        RGB颜色元组
    """
    if len(rgb_colors) == 2:
        # 两个颜色的渐变
        r = int(rgb_colors[0][0] * (1 - t) + rgb_colors[1][0] * t)
        g = int(rgb_colors[0][1] * (1 - t) + rgb_colors[1][1] * t)
        b = int(rgb_colors[0][2] * (1 - t) + rgb_colors[1][2] * t)
        return (r, g, b)
    else:
        # 多个颜色的渐变
        segment = t * (len(rgb_colors) - 1)
        segment_index = int(segment)
        segment_t = segment - segment_index
        
        if segment_index >= len(rgb_colors) - 1:
            return rgb_colors[-1]
        
        r = int(rgb_colors[segment_index][0] * (1 - segment_t) + rgb_colors[segment_index + 1][0] * segment_t)
        g = int(rgb_colors[segment_index][1] * (1 - segment_t) + rgb_colors[segment_index + 1][1] * segment_t)
        b = int(rgb_colors[segment_index][2] * (1 - segment_t) + rgb_colors[segment_index + 1][2] * segment_t)
        return (r, g, b)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Generate gradient image for specific color ID')
    parser.add_argument('id', type=int, help='Color ID to generate image for')
    parser.add_argument('--markdown', type=str, help='Markdown content to display in the image')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = "gradient_images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # 读取颜色数据
        with open("../color_zh.json", "r", encoding="utf-8") as f:
            colors_data = json.load(f)
    except Exception as e:
        print(f"Error reading color_zh.json: {e}")
        return
    
    # 查找指定ID的颜色
    color_item = next((item for item in colors_data if item["id"] == args.id), None)
    if not color_item:
        print(f"No color found with ID {args.id}")
        return
    
    try:
        id = color_item["id"]
        name = color_item["name"]
        colors = color_item["colors"]
        
        if not colors:
            print(f"Skipping {name} (ID: {id}) - no colors provided")
            return
        
        # 生成输出文件名
        output_path = os.path.join(output_dir, f"gradient_{id}_{name}.png")
        
        # 创建渐变色图片
        create_gradient_image(1080, 1920, colors, output_path, args.markdown)
        print(f"Generated image for {name} (ID: {id})")
    except Exception as e:
        print(f"Error processing color item: {e}")

if __name__ == "__main__":
    main() 