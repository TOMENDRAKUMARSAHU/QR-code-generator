from flask import Flask, render_template, request, send_file
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap
import zipfile
import tempfile

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_qr():
    try:
        names = request.form.getlist('name[]')
        links = request.form.getlist('link[]')
        file = request.files.get('excel_file')

        # Load Excel if uploaded
        if file and file.filename:
            df = pd.read_excel(file, usecols="B:C", engine="openpyxl")
            df.columns = ['Name', 'Link']
            names += df['Name'].astype(str).tolist()
            links += df['Link'].astype(str).tolist()

        # Filter valid entries
        entries = [(n.strip(), l.strip()) for n, l in zip(names, links) if n.strip() and l.strip() and l.startswith("http")]
        if not entries:
            return "❌ No valid name-link pairs found", 400

        temp_dir = tempfile.mkdtemp()
        output_folder = os.path.join(temp_dir, "qr_output")
        os.makedirs(output_folder, exist_ok=True)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, size=60)

        for name, link in entries:
            qr = qrcode.QRCode(
                version=4, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=4
            )
            qr.add_data(link)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            width, height = qr_img.size

            # Add name as caption
            wrapped_lines = textwrap.wrap(name, width=30)
            line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 10
            total_text_height = len(wrapped_lines) * line_height + 20
            combined_img = Image.new("RGB", (width, height + total_text_height), "white")
            combined_img.paste(qr_img, (0, 0))

            draw = ImageDraw.Draw(combined_img)
            y_text = height + 10
            for line in wrapped_lines:
                text_width = font.getlength(line)
                draw.text(((width - text_width) // 2, y_text), line, font=font, fill="black")
                y_text += line_height

            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            combined_img.save(os.path.join(output_folder, f"{safe_name}.png"))

        zip_path = os.path.join(temp_dir, "qr_codes.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in os.listdir(output_folder):
                zipf.write(os.path.join(output_folder, file), arcname=file)

        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"❌ Error: {str(e)}", 500
