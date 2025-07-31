@app.route('/generate', methods=['POST'])
def generate_qr():
    try:
        names = request.form.getlist('name[]')
        links = request.form.getlist('link[]')

        if not names or not links or len(names) != len(links):
            return "❌ Name and Link mismatch or empty"

        temp_dir = tempfile.mkdtemp()
        output_folder = os.path.join(temp_dir, "qr_output")
        os.makedirs(output_folder, exist_ok=True)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, size=60)

        for name, link in zip(names, links):
            if not link.startswith("http"):
                continue
            qr = qrcode.QRCode(
                version=4, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=4
            )
            qr.add_data(link)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

            width, height = qr_img.size
            draw = ImageDraw.Draw(qr_img)
            text_width = font.getlength(name)
            new_img = Image.new("RGB", (width, height + 100), "white")
            new_img.paste(qr_img, (0, 0))
            draw = ImageDraw.Draw(new_img)
            draw.text(((width - text_width) // 2, height + 10), name, font=font, fill="black")

            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            new_img.save(os.path.join(output_folder, f"{safe_name}.png"))

        zip_path = os.path.join(temp_dir, "qr_codes.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in os.listdir(output_folder):
                zipf.write(os.path.join(output_folder, file), arcname=file)

        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"❌ Error: {str(e)}", 500
