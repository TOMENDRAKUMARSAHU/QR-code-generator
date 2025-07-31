from flask import Flask, render_template, request, send_file, redirect, url_for
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap
from zipfile import ZipFile
import tempfile
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/generated_qr'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_qr():
    names = request.form.getlist("name[]")
    links = request.form.getlist("link[]")
    file = request.files.get("excel_file")

    # Create a fresh output folder
    temp_dir = tempfile.mkdtemp()
    output_folder = os.path.join(temp_dir, "qr_output")
    os.makedirs(output_folder, exist_ok=True)

    try:
        entries = []

        # Read from uploaded Excel
        if file and file.filename.endswith(".xlsx"):
            df = pd.read_excel(file, usecols="B:C", engine="openpyxl")
            df.columns = ['Name', 'Link']
            entries = df.dropna().values.tolist()
        else:
            # Use manual form entries
            for name, link in zip(names, links):
                if name.strip() and link.strip():
                    entries.append([name.strip(), link.strip()])

        # Font settings
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, size=60)

        image_files = []

        for name, link in entries:
            if not link.startswith("http"):
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

            # Wrap text
            wrapped_lines = []
            for line in textwrap.wrap(name, width=30):
                while font.getlength(line) > width - 40:
                    line = textwrap.wrap(line, width=len(line) // 2)[0]
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
            filename = f"{safe_name}.png"
            filepath = os.path.join(output_folder, filename)
            combined_img.save(filepath)
            image_files.append((filename, filepath))

        # Zip them
        zip_path = os.path.join(temp_dir, "qr_codes.zip")
        with ZipFile(zip_path, "w") as zipf:
            for filename, path in image_files:
                zipf.write(path, arcname=filename)

        # Copy files to static folder for web display
        web_output_folder = os.path.join(app.config['UPLOAD_FOLDER'])
        if os.path.exists(web_output_folder):
            shutil.rmtree(web_output_folder)
        os.makedirs(web_output_folder)

        image_urls = []
        for filename, path in image_files:
            static_path = os.path.join(web_output_folder, filename)
            shutil.copy2(path, static_path)
            image_urls.append(f"/static/generated_qr/{filename}")

        # Move zip
        zip_output_path = os.path.join(web_output_folder, "qr_codes.zip")
        shutil.copy2(zip_path, zip_output_path)

        return render_template("result.html", images=image_urls, zip_file="/static/generated_qr/qr_codes.zip")

    except Exception as e:
        return f"❌ Error: {str(e)}", 500
