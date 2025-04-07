import json
import os
import argparse
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
from typing import List, Tuple
import markdown2
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import emoji
from playwright.sync_api import sync_playwright
import tempfile
import base64
from flask import Flask, request, jsonify, send_file
import uuid
import traceback
import re

app = Flask(__name__)

# 确保输出目录存在
OUTPUT_DIR = "gradient_images"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """将十六进制颜色转换为RGB元组"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid color format: {hex_color}")
    
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError as e:
        raise ValueError(f"Invalid color value: {hex_color}") from e

def is_emoji(char: str) -> bool:
    """判断字符是否是emoji"""
    return any(ord(c) > 0x1F300 for c in char)

def create_gradient_image(width: int, height: int, colors: List[str], output_path: str = None, markdown_content: str = None, background_color: str = "#FFFFFF", direction: str = "bottom-right"):
    """创建渐变色图片
    
    Args:
        width: 图片宽度
        height: 图片高度
        colors: 渐变色列表
        output_path: 输出路径，如果为None则只返回图片字节流不保存文件
        markdown_content: markdown内容
        background_color: 中心矩形的背景色，默认为白色 (#FFFFFF)
        direction: 渐变方向，可选值：vertical（垂直）、horizontal（水平）、diagonal（对角线）、bottom-right（右下角），默认为 bottom-right
    
    Returns:
        BytesIO: 包含图片数据的字节流对象
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
        return None
    
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
    elif direction == "bottom-right":
        # 右下角渐变
        for y in range(height):
            for x in range(width):
                # 计算到右下角的距离比例
                dx = x / width
                dy = y / height
                t = (dx + dy) / 2
                color = get_gradient_color(rgb_colors, t)
                draw.point((x, y), fill=color)
    else:  # diagonal (默认对角线渐变)
        for y in range(height):
            for x in range(width):
                dx = x / width
                dy = y / height
                t = (dx + dy) / 2
                color = get_gradient_color(rgb_colors, t)
                draw.point((x, y), fill=color)

    # 计算圆角矩形的位置和大小
    rect_width = int(width * 0.8)
    rect_height = int(height * 0.8)  # 这个值将被动态调整
    rect_x = (width - rect_width) // 2
    rect_y = (height - rect_height) // 2
    radius = 50

    # 创建发光效果层
    glow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # 判断背景色是否为白色或接近白色
    is_light_background = sum(background_rgb) > 600  # 简单判断，RGB值之和大于600认为是浅色
    
    # 根据背景色设置文字颜色和边框颜色
    text_color = "#333333" if is_light_background else "#FFFFFF"
    border_color = (255, 255, 255, 100) if is_light_background else (0, 0, 0, 100)

    # 如果有markdown内容，使用Playwright生成图片
    if markdown_content:
        # 将markdown转换为HTML
        processed_content = markdown_content.replace('\\n', '\n')
        processed_content = processed_content.replace('\n', '  \n')
        
        # 识别并处理URL
        # 使用正则表达式匹配URL
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
        
        # 将URL替换为带有蓝色样式的HTML
        def replace_url(match):
            url = match.group(0)
            return f'<a href="{url}" style="color: #0066CC; text-decoration: none;">{url}</a>'
        
        processed_content = re.sub(url_pattern, replace_url, processed_content)
        
        # 使用markdown2转换，启用extras参数以支持更多markdown特性
        html_content = markdown2.markdown(processed_content, extras=['fenced-code-blocks', 'tables', 'break-on-newline'])
        
        # 创建HTML模板
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @font-face {{
                    font-family: 'JetBrainsMono';
                    src: url('data:font/ttf;base64,{base64.b64encode(open("JetBrainsMono-Regular-2.ttf", "rb").read()).decode()}') format('truetype');
                }}
                body {{
                    margin: 0;
                    padding: 0;
                    width: {rect_width - 2 * radius}px;
                    background-color: transparent;
                    color: {text_color};
                    font-family: 'JetBrainsMono', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                }}
                .content {{
                    padding: 20px;
                    box-sizing: border-box;
                    width: 100%;
                    background-color: {background_color};
                }}
                h1 {{ font-size: 72px; margin: 0 0 20px 0; }}
                h2 {{ font-size: 54px; margin: 0 0 15px 0; }}
                p {{ font-size: 36px; margin: 0 0 10px 0; }}
                ul, ol {{ font-size: 36px; margin: 0 0 10px 0; padding-left: 40px; }}
                li {{ margin-bottom: 10px; }}
                img {{ max-width: 100%; height: auto; }}
                a {{ color: #0066CC; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="content">
                {html_content}
            </div>
        </body>
        </html>
        """
        
        # 创建临时HTML文件
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_file.write(html_template.encode('utf-8'))
            temp_html_path = temp_file.name
        
        try:
            # 使用Playwright截图
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # 设置初始视口大小
                page.set_viewport_size({"width": rect_width - 2 * radius, "height": 1000})
                
                # 加载页面
                page.goto(f"file://{temp_html_path}")
                
                # 等待内容加载完成
                page.wait_for_load_state("networkidle")
                
                # 获取内容高度
                content_height = page.evaluate("""() => {
                    const content = document.querySelector('.content');
                    return Math.max(content.scrollHeight, content.offsetHeight);
                }""")
                
                # 设置视口大小为内容实际高度
                page.set_viewport_size({"width": rect_width - 2 * radius, "height": content_height})
                
                # 等待一下确保内容完全渲染
                page.wait_for_timeout(100)
                
                # 截图
                screenshot = page.screenshot(type="png", full_page=True)
                browser.close()
            
            # 将截图转换为PIL图像
            text_layer = Image.open(BytesIO(screenshot))
            
            # 更新矩形高度为内容高度加上圆角
            rect_height = content_height + 2 * radius
            
            # 重新计算矩形位置，使其垂直居中
            rect_y = (height - rect_height) // 2
            
            # 重新计算发光效果的位置和大小
            glow_rect_width = rect_width + 20
            glow_rect_height = rect_height + 20
            glow_rect_x = (width - glow_rect_width) // 2
            glow_rect_y = (height - glow_rect_height) // 2
            glow_radius = radius + 10
            
            # 绘制发光效果的四个圆角
            glow_draw.ellipse([glow_rect_x, glow_rect_y, glow_rect_x + glow_radius * 2, glow_rect_y + glow_radius * 2], fill=border_color)
            glow_draw.ellipse([glow_rect_x + glow_rect_width - glow_radius * 2, glow_rect_y, glow_rect_x + glow_rect_width, glow_rect_y + glow_radius * 2], fill=border_color)
            glow_draw.ellipse([glow_rect_x, glow_rect_y + glow_rect_height - glow_radius * 2, glow_rect_x + glow_radius * 2, glow_rect_y + glow_rect_height], fill=border_color)
            glow_draw.ellipse([glow_rect_x + glow_rect_width - glow_radius * 2, glow_rect_y + glow_rect_height - glow_radius * 2, glow_rect_x + glow_rect_width, glow_rect_y + glow_rect_height], fill=border_color)
            
            # 绘制发光效果的矩形主体
            glow_draw.rectangle([glow_rect_x + glow_radius, glow_rect_y, glow_rect_x + glow_rect_width - glow_radius, glow_rect_y + glow_rect_height], fill=border_color)
            glow_draw.rectangle([glow_rect_x, glow_rect_y + glow_radius, glow_rect_x + glow_rect_width, glow_rect_y + glow_rect_height - glow_radius], fill=border_color)
            
            # 应用模糊效果
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=10))
            
            # 绘制主圆角矩形
            draw.ellipse([rect_x, rect_y, rect_x + radius * 2, rect_y + radius * 2], fill=background_rgb)
            draw.ellipse([rect_x + rect_width - radius * 2, rect_y, rect_x + rect_width, rect_y + radius * 2], fill=background_rgb)
            draw.ellipse([rect_x, rect_y + rect_height - radius * 2, rect_x + radius * 2, rect_y + rect_height], fill=background_rgb)
            draw.ellipse([rect_x + rect_width - radius * 2, rect_y + rect_height - radius * 2, rect_x + rect_width, rect_y + rect_height], fill=background_rgb)
            
            # 绘制矩形主体
            draw.rectangle([rect_x + radius, rect_y, rect_x + rect_width - radius, rect_y + rect_height], fill=background_rgb)
            draw.rectangle([rect_x, rect_y + radius, rect_x + rect_width, rect_y + rect_height - radius], fill=background_rgb)
            
            # 合并发光效果
            image = Image.alpha_composite(image.convert('RGBA'), glow_layer)
            
            # 将文本层合并到主图片
            image.paste(text_layer, (rect_x + radius, rect_y + radius), text_layer)
            
        finally:
            # 清理临时文件
            os.unlink(temp_html_path)
    else:
        # 如果没有markdown内容，使用默认的矩形高度
        # 绘制发光效果的四个圆角
        glow_rect_width = rect_width + 20
        glow_rect_height = rect_height + 20
        glow_rect_x = (width - glow_rect_width) // 2
        glow_rect_y = (height - glow_rect_height) // 2
        glow_radius = radius + 10
        
        glow_draw.ellipse([glow_rect_x, glow_rect_y, glow_rect_x + glow_radius * 2, glow_rect_y + glow_radius * 2], fill=border_color)
        glow_draw.ellipse([glow_rect_x + glow_rect_width - glow_radius * 2, glow_rect_y, glow_rect_x + glow_rect_width, glow_rect_y + glow_radius * 2], fill=border_color)
        glow_draw.ellipse([glow_rect_x, glow_rect_y + glow_rect_height - glow_radius * 2, glow_rect_x + glow_radius * 2, glow_rect_y + glow_rect_height], fill=border_color)
        glow_draw.ellipse([glow_rect_x + glow_rect_width - glow_radius * 2, glow_rect_y + glow_rect_height - glow_radius * 2, glow_rect_x + glow_rect_width, glow_rect_y + glow_rect_height], fill=border_color)
        
        # 绘制发光效果的矩形主体
        glow_draw.rectangle([glow_rect_x + glow_radius, glow_rect_y, glow_rect_x + glow_rect_width - glow_radius, glow_rect_y + glow_rect_height], fill=border_color)
        glow_draw.rectangle([glow_rect_x, glow_rect_y + glow_radius, glow_rect_x + glow_rect_width, glow_rect_y + glow_rect_height - glow_radius], fill=border_color)
        
        # 应用模糊效果
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=10))
        
        # 绘制主圆角矩形
        draw.ellipse([rect_x, rect_y, rect_x + radius * 2, rect_y + radius * 2], fill=background_rgb)
        draw.ellipse([rect_x + rect_width - radius * 2, rect_y, rect_x + rect_width, rect_y + radius * 2], fill=background_rgb)
        draw.ellipse([rect_x, rect_y + rect_height - radius * 2, rect_x + radius * 2, rect_y + rect_height], fill=background_rgb)
        draw.ellipse([rect_x + rect_width - radius * 2, rect_y + rect_height - radius * 2, rect_x + rect_width, rect_y + rect_height], fill=background_rgb)
        
        # 绘制矩形主体
        draw.rectangle([rect_x + radius, rect_y, rect_x + rect_width - radius, rect_y + rect_height], fill=background_rgb)
        draw.rectangle([rect_x, rect_y + radius, rect_x + rect_width, rect_y + rect_height - radius], fill=background_rgb)
        
        # 合并发光效果
        image = Image.alpha_composite(image.convert('RGBA'), glow_layer)

    # 创建字节流对象保存图片数据
    img_byte_arr = BytesIO()
    image.convert('RGB').save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)  # 将指针移回开始位置
    
    # 如果提供了输出路径，则保存图片
    if output_path:
        image.convert('RGB').save(output_path)
        print(f"Image saved: {output_path}")
    
    # 返回字节流对象
    return img_byte_arr

def get_gradient_color(rgb_colors: List[Tuple[int, int, int]], t: float) -> Tuple[int, int, int]:
    """计算渐变颜色"""
    if len(rgb_colors) == 2:
        r = int(rgb_colors[0][0] * (1 - t) + rgb_colors[1][0] * t)
        g = int(rgb_colors[0][1] * (1 - t) + rgb_colors[1][1] * t)
        b = int(rgb_colors[0][2] * (1 - t) + rgb_colors[1][2] * t)
        return (r, g, b)
    else:
        segment = t * (len(rgb_colors) - 1)
        segment_index = int(segment)
        segment_t = segment - segment_index
        
        if segment_index >= len(rgb_colors) - 1:
            return rgb_colors[-1]
        
        r = int(rgb_colors[segment_index][0] * (1 - segment_t) + rgb_colors[segment_index + 1][0] * segment_t)
        g = int(rgb_colors[segment_index][1] * (1 - segment_t) + rgb_colors[segment_index + 1][1] * segment_t)
        b = int(rgb_colors[segment_index][2] * (1 - segment_t) + rgb_colors[segment_index + 1][2] * segment_t)
        return (r, g, b)

@app.route('/generate_color_picture', methods=['POST'])
def generate_image():
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 验证必要参数
        if not data or 'id' not in data or 'markdown' not in data:
            return jsonify({
                'error': 'Missing required parameters',
                'required': ['id', 'markdown']
            }), 400
        
        # 确保color_id是整数类型
        try:
            color_id = int(data['id'])
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Invalid id format. Must be an integer.'
            }), 400
            
        markdown_content = data['markdown']
        background_color = data.get('background_color', '#FFFFFF')  # 默认白色
        direction = data.get('direction', 'bottom-right')  # 默认右下角渐变
        
        # 验证背景色格式
        if not background_color.startswith('#') or len(background_color) != 7:
            return jsonify({
                'error': 'Invalid background_color format. Should be a hex color (e.g., #FFFFFF)'
            }), 400
        
        # 验证渐变方向
        valid_directions = ['vertical', 'horizontal', 'diagonal', 'bottom-right']
        if direction not in valid_directions:
            return jsonify({
                'error': f'Invalid direction. Must be one of: {", ".join(valid_directions)}'
            }), 400
        
        # 读取颜色数据
        try:
            with open("color_zh.json", "r", encoding="utf-8") as f:
                colors_data = json.load(f)
        except Exception as e:
            return jsonify({
                'error': f'Error reading color data: {str(e)}'
            }), 500
        
        # 查找指定ID的颜色
        color_item = next((item for item in colors_data if item["id"] == color_id), None)
        if not color_item:
            return jsonify({
                'error': f'No color found with ID {color_id}'
            }), 404
        
        # 确保输出目录存在
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())
        output_filename = f"gradient_{color_id}_{color_item['name']}_{unique_id}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # 创建渐变色图片，使用指定的渐变方向
        img_bytes = create_gradient_image(1080, 1920, color_item['colors'], output_path, markdown_content, background_color, direction)
        
        # 返回图片文件
        return send_file(img_bytes, mimetype='image/png')
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error details:\n{error_details}")
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'details': error_details
        }), 500

def main():
    parser = argparse.ArgumentParser(description='Generate gradient image for specific color ID')
    parser.add_argument('id', type=int, help='Color ID to generate image for')
    parser.add_argument('--markdown', type=str, help='Markdown content to display in the image. If the value starts with "@", it will be treated as a file path to read markdown content from.')
    parser.add_argument('--background-color', type=str, default='#FFFFFF', help='Background color for the rectangle in hex format (e.g., #FFFFFF for white)')
    parser.add_argument('--direction', type=str, default='bottom-right', choices=['vertical', 'horizontal', 'diagonal', 'bottom-right'], help='Gradient direction')
    parser.add_argument('--output', type=str, help='Output file path. If not provided, the image will be saved in the gradient_images directory.')
    args = parser.parse_args()

    output_dir = "gradient_images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        with open("color_zh.json", "r", encoding="utf-8") as f:
            colors_data = json.load(f)
    except Exception as e:
        print(f"Error reading color_zh.json: {e}")
        return
    
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
        
        # 处理 markdown 内容
        markdown_content = args.markdown
        if markdown_content and markdown_content.startswith('@'):
            # 从文件中读取 markdown 内容
            file_path = markdown_content[1:]  # 去掉 @ 符号
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                print(f"Read markdown content from file: {file_path}")
            except Exception as e:
                print(f"Error reading markdown file: {e}")
                return
        
        # 验证背景色格式
        background_color = args.background_color
        if not background_color.startswith('#') or len(background_color) != 7:
            print(f"Invalid background color format: {background_color}. Using default white (#FFFFFF)")
            background_color = '#FFFFFF'
        
        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            output_path = os.path.join(output_dir, f"gradient_{id}_{name}.png")
        
        # 创建渐变色图片并获取字节流
        img_bytes = create_gradient_image(1080, 1920, colors, output_path, markdown_content, background_color, args.direction)
        print(f"Generated image for {name} (ID: {id}) with background color {background_color} and direction {args.direction}")
        
        # 如果需要返回字节流供进一步处理，可以在这里使用 img_bytes
        
    except Exception as e:
        print(f"Error processing color item: {e}")

if __name__ == "__main__":
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 如果有命令行参数，执行命令行模式
        main()
    else:
        # 如果没有命令行参数，启动 Flask 服务器
        app.run(host='0.0.0.0', port=5001, debug=True) 