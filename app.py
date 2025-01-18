from flask import Flask, render_template, request, jsonify, send_file
import os
import re
import json
from typing import Dict, List, Tuple
from collections import defaultdict
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('config', exist_ok=True)

class FontFaceGenerator:
    DEFAULT_WEIGHT_MAPPINGS = {
        'Thin': '100',
        'ExtraLight': '200',
        'Light': '300',
        'Regular': '400',
        'Medium': '500',
        'SemiBold': '600',
        'Bold': '700',
        'ExtraBold': '800',
        'Black': '900'
    }

    def __init__(self, use_custom_weights: bool = False):
        self.font_files = defaultdict(list)
        self.weight_mappings = self.load_weight_mappings(use_custom_weights)

    def load_weight_mappings(self, use_custom_weights: bool = False) -> Dict[str, str]:
        """Load weight mappings from config file or use defaults."""
        if not use_custom_weights:
            return self.DEFAULT_WEIGHT_MAPPINGS

        config_path = os.path.join('config', 'weights.json')
        try:
            if not os.path.exists('config'):
                os.makedirs('config')
                
            if not os.path.exists(config_path):
                # Create default weights.json if it doesn't exist
                default_custom_weights = {
                    "Book": "350",
                    "Heavy": "850",
                    "ExtraBlack": "950",
                }
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_custom_weights, f, indent=2)
                print(f"Created default weights configuration at {config_path}")

            with open(config_path, 'r', encoding='utf-8') as f:
                custom_mappings = json.load(f)
            
            # Validate the custom mappings
            for value in custom_mappings.values():
                if not str(value).isdigit():
                    raise ValueError(f"Invalid weight value in config: {value}")
            
            # Merge with defaults, letting custom mappings take precedence
            merged_mappings = {**self.DEFAULT_WEIGHT_MAPPINGS, **custom_mappings}
            return merged_mappings
            
        except Exception as e:
            print(f"Error loading custom weights: {str(e)}. Using default weights.")
            return self.DEFAULT_WEIGHT_MAPPINGS

    def get_font_format(self, filename: str) -> str:
        """Determine the font format from the file extension."""
        ext = filename.lower().split('.')[-1]
        format_mapping = {
            'ttf': 'truetype',
            'woff': 'woff',
            'woff2': 'woff2',
            'eot': 'embedded-opentype'
        }
        return format_mapping.get(ext, '')

    def parse_weight_and_style(self, filename: str) -> Tuple[str, str]:
        """Extract font weight and style from filename."""
        # Remove file extension and split by hyphen or underscore
        base_name = os.path.splitext(filename)[0]
        parts = re.split('[-_]', base_name)
        
        # Check for style (italic)
        is_italic = any('italic' in part.lower() for part in parts)
        style = 'italic' if is_italic else 'normal'
        
        # Find weight
        weight = '400'  # default weight
        for part in parts:
            # First check for combined weight+italic patterns
            clean_part = part.lower().replace('italic', '')
            
            # Check for exact matches in weight_mappings
            for weight_name, weight_value in self.weight_mappings.items():
                if clean_part.lower() == weight_name.lower():
                    weight = weight_value
                    break
        
        return weight, style

    def process_directory(self, directory_path: str, base_url: str) -> None:
        """Process all font files in the given directory."""
        for filename in os.listdir(directory_path):
            if filename.lower().endswith(('.ttf', '.woff', '.woff2', '.eot')):
                weight, style = self.parse_weight_and_style(filename)
                font_format = self.get_font_format(filename)
                full_path = os.path.join(base_url.rstrip('/'), filename)
                key = f"{weight}-{style}"
                self.font_files[key].append((filename, font_format, full_path))

    def generate_css(self, font_family: str) -> str:
        """Generate CSS @font-face declarations."""
        css = []
        
        # Sort by weight and style (normal before italic)
        sorted_weights = sorted(self.font_files.items(), 
                              key=lambda x: (int(x[0].split('-')[0]), 
                                           0 if x[0].split('-')[1] == 'normal' else 1))
        
        for weight_style, files in sorted_weights:
            weight, style = weight_style.split('-')
            
            # Sort files to ensure consistent order (woff2, woff, ttf, eot)
            format_priority = {'woff2': 0, 'woff': 1, 'truetype': 2, 'embedded-opentype': 3}
            files.sort(key=lambda x: format_priority.get(x[1], 999))
            
            sources = []
            for _, fmt, path in files:
                if fmt == 'embedded-opentype':
                    sources.append(f"url('{path}?#iefix') format('{fmt}')")
                else:
                    sources.append(f"url('{path}') format('{fmt}')")
            
            declaration = f"""@font-face {{
    font-family: '{font_family}';
    font-style: {style};
    font-weight: {weight};
    font-display: swap;
    src: {','.join(sources)};
}}"""
            css.append(declaration)
        
        return '\n'.join(css)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {
        'ttf', 'woff', 'woff2', 'eot'
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/weights', methods=['GET'])
def get_weights():
    config_path = os.path.join('config', 'weights.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            custom_weights = json.load(f)
    else:
        custom_weights = {}
    
    # Combine with default weights
    generator = FontFaceGenerator(False)
    all_weights = {**generator.DEFAULT_WEIGHT_MAPPINGS, **custom_weights}
    
    # Return as ordered list of pairs
    weight_order = [
        'Thin', 'ExtraLight', 'Light', 'Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold', 'Black'
    ]
    
    ordered_weights = []
    # Add default weights in specific order
    for name in weight_order:
        if name in all_weights:
            ordered_weights.append([name, all_weights[name]])
    
    # Add any custom weights at the end
    for name, value in custom_weights.items():
        if name not in weight_order:
            ordered_weights.append([name, value])
    
    return jsonify(ordered_weights)

@app.route('/api/custom-weights', methods=['GET'])
def get_custom_weights():
    config_path = os.path.join('config', 'weights.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({})

@app.route('/api/custom-weights', methods=['POST'])
def save_custom_weights():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        custom_weights = request.get_json()
        if custom_weights is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Validate the weights
        for value in custom_weights.values():
            if not str(value).isdigit():
                return jsonify({'error': 'Invalid weight value'}), 400

        # Create config directory if it doesn't exist
        os.makedirs('config', exist_ok=True)
        
        # Save the weights
        config_path = os.path.join('config', 'weights.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(custom_weights, f, indent=2)
        
        return jsonify({'message': 'Custom weights saved successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_css():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files[]')
        font_family = request.form.get('fontFamily', '')
        base_url = request.form.get('baseUrl', '')
        use_custom_weights = request.form.get('useCustomWeights') == 'true'

        # Create temporary directory for uploaded files
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(font_family))
        os.makedirs(temp_dir, exist_ok=True)

        # Save uploaded files
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(temp_dir, filename))

        # Generate CSS
        generator = FontFaceGenerator(use_custom_weights)
        generator.process_directory(temp_dir, base_url)
        css = generator.generate_css(font_family)

        # Clean up
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)

        # Replace literal newlines with actual newlines
        css = css.replace('\\n', '\n')

        return jsonify({
            'css': css,
            'filename': f"{font_family.lower().replace(' ', '-')}.css"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_css():
    try:
        css_content = request.json.get('css', '')
        filename = request.json.get('filename', 'font-face.css')
        
        # Create temporary file
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/css'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)