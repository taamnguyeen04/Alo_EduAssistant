import qrcode
from PIL import Image

links = [
    ("qr_cloudflare.png", "https://associate-lewis-arbitration-cause.trycloudflare.com"),
    ("qr_ngrok.png", "https://nonchromatic-nonliterally-jacklyn.ngrok-free.dev/"),
]

for filename, url in links:
    qr = qrcode.QRCode(
        version=None,  # tu dong chon kich thuoc
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # chiu loi 15%
        box_size=12,   # kich thuoc moi o vuong
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(filename)
    print(f"Da tao: {filename} -> {url}")

print("Xong! 2 file QR da duoc sinh ra.")
