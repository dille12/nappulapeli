import qrcode
import pygame

def make_qr_surface(url, scale=10):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=scale,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    w, h = img.size
    data = img.tobytes()
    surface = pygame.image.fromstring(data, (w, h), "RGB")
    return surface
