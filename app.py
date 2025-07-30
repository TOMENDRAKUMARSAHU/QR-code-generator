from flask import Flask, render_template, request, send_file, url_for
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap
from zipfile import ZipFile
import tempfile
import shutil

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
        # Load Excel
        df = pd.read_excel(file, usecols="B:C", engine="openpyxl")
        df.columns = ['Name', 'Link']

        # Temporary storage
        temp_dir = tempfile.mkdtemp()
        output_folder = os.path.join(temp_dir, "qr_output")
        os.makedirs(output_folder, exist_ok=True)

        # Output for web display
        static_output = os.path.join("static", "qr_output")
        if os.path.exists(static_output):
            shutil.rmtree(static_output)
        os.makedirs(static_output, exist_ok=True)

        # Font settings
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_size = 60
        font = ImageFont.truetype(font_path, size=font_size)

        image_names = []

        for idx, row in df.iterrows():
            name = str(row["Name"]).strip()
            link = str(row["Link"]).strip()

            if pd.isna(link) or not link.startswith("http"):
                continue

            # Generate QR code
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

            # Wrap name
            max_text_width = width - 40
            wrapped_lines = []
            for line in textwrap.wrap(name, width=30):
                while font.getlength(line) > max_text_width:
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

            # Save image
            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            file_name = f"{safe_name}.png"
            save_path = os.path.join(static_output, file_name)
            combined_img.save(save_path)
            image_names.append(file_name)

        # Create ZIP
        zip_static_path = os.path.join("static", "qr_codes.zip")
        with ZipFile(zip_static_path, "w") as zipf:
            for img_name in image_names:
                zipf.write(os.path.join(static_output, img_name), arcname=img_name)

        return render_template("index.html", images=image_names)

    except Exception as e:
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
