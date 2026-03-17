# ============================================================
# core/utils/visual_tables.py — Table Rendering Utility
#
# Converts Markdown/HTML tables to high-quality PNGs for mobile.
# ============================================================

import os
from html2image import Html2Image
from settings import settings as config
from skills.logger import log_app

# Force a headless flags for Docker/Linux compatibility
hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu'])

def render_table_to_image(markdown_table: str, output_name: str = "table.png") -> str:
    """
    Converts a Markdown table to a styled PNG image.
    """
    output_path = os.path.join(config.DATA_DIR, output_name)
    
    # 1. Convert Markdown Table to simple HTML structure
    # (Simplified: we'll wrap the markdown in a <pre> with CSS for a clean look)
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Courier New', Courier, monospace;
                padding: 20px;
                display: inline-block;
            }}
            pre {{
                border: 1px solid #30363d;
                padding: 15px;
                border-radius: 6px;
                background-color: #161b22;
                margin: 0;
            }}
            .title {{
                color: #58a6ff;
                font-weight: bold;
                margin-bottom: 10px;
                font-family: sans-serif;
            }}
        </style>
    </head>
    <body>
        <div class="title">📊 ASURA ARCHITECTURAL DATA</div>
        <pre>{markdown_table}</pre>
    </body>
    </html>
    """
    
    try:
        log_app(f"Rendering table to image: {output_name}")
        hti.screenshot(html_str=html_content, save_as=output_name)
        
        # html2image saves to current dir by default, move it if needed
        if os.path.exists(output_name):
            os.rename(output_name, output_path)
            return output_path
    except Exception as e:
        log_app(f"Table rendering failed: {e}")
        
    return ""
