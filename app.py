from flask import Flask, render_template, request, send_file
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap
from zipfile import ZipFile
import tempfile

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_qr():
    if 'file' not in request.files:
        return "❌ No file uploaded", 400

    file = request.files['file']
    if file.filename == '':
        return "❌ Empty filename", 400

    try:
        df = pd.read_excel(file, usecols="B:C", engine="openpyxl")
        df.columns = ['Name', 'Link']

        temp_dir = tempfile.mkdtemp()
        output_folder = os.path.join(temp_dir, "qr_output")
        os.makedirs(output_folder, exist_ok=True)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_size = 60
        font = ImageFont.truetype(font_path, size=font_size)

        for idx, row in df.iterrows():
            name = str(row["Name"]).strip()
            link = str(row["Link"]).strip()

            if pd.isna(link) or not link.startswith("http"):
                continue

            qr = qrcode.QRCode(
                version=4,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=20,
                border=4,
            )
            qr.add_data(link)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            width, height = qr_img.size

            max_text_width = width - 40
            wrapped_lines = []
            for line in textwrap.wrap(name, width=30):
                while font.getlength(line) > max_text_width:
                    line = textwrap.wrap(line, width=len(line)//2)[0]
                wrapped_lines.append(line)

            line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 10
            total_text_height = len(wrapped_lines) * line_height
            new_height = height + total_text_height + 40

            combined_img = Image.new("RGB", (width, new_height), "white")
            combined_img.paste(qr_img, (0, 0))

            draw = ImageDraw.Draw(combined_img)
            y_text = height + 20
            for line in wrapped_lines:
                text_width = font.getlength(line)
                x_text = (width - text_width) // 2
                draw.text((x_text, y_text), line, fill="black", font=font)
                y_text += line_height

            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            combined_img.save(os.path.join(output_folder, f"{safe_name}.png"))

        zip_path = os.path.join(temp_dir, "qr_codes.zip")
        with ZipFile(zip_path, "w") as zipf:
            for file in os.listdir(output_folder):
                zipf.write(os.path.join(output_folder, file), arcname=file)

        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"❌ Error: {str(e)}", 500
