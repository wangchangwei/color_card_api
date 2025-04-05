from flask import Flask, request, jsonify, send_file
import os
from main import create_gradient_image
import json
import uuid
import traceback

app = Flask(__name__)

# 确保输出目录存在
OUTPUT_DIR = "gradient_images"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

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
        
        color_id = data['id']
        markdown_content = data['markdown']
        background_color = data.get('background_color', '#000000')  # 默认黑色
        direction = data.get('direction', 'vertical')  # 默认垂直方向
        
        # 验证背景色格式
        if not background_color.startswith('#') or len(background_color) != 7:
            return jsonify({
                'error': 'Invalid background_color format. Should be a hex color (e.g., #000000)'
            }), 400
        
        # 验证方向参数
        valid_directions = ['vertical', 'horizontal', 'diagonal']
        if direction not in valid_directions:
            return jsonify({
                'error': f'Invalid direction. Should be one of: {", ".join(valid_directions)}'
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
        
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())
        output_filename = f"gradient_{color_id}_{color_item['name']}_{unique_id}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # 创建渐变色图片
        create_gradient_image(1080, 1920, color_item['colors'], output_path, markdown_content, background_color, direction)
        
        # 返回图片文件
        return send_file(output_path, mimetype='image/png')
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error details:\n{error_details}")
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'details': error_details
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 