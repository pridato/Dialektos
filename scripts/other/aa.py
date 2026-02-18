from PIL import Image, ImageDraw, ImageFont
import os


def crear_miniatura_linkedin():
    # 1. Configuración de dimensiones (Ratio ideal LinkedIn 1.91:1 o cercano a 16:9)
    width, height = 1200, 627

    # 2. Colores
    # Azul oscuro tipo "Navy/Tech" (profesional) o Gris Carbón
    bg_color = (10, 25, 47)  # Un azul muy oscuro estilo "IDE theme"
    text_color = (255, 255, 255)  # Blanco
    accent_color = (100, 255, 218)  # Un cian tipo "código" para detalles

    # 3. Crear lienzo
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)

    # 4. Intentar cargar una fuente monoespaciada (para el toque "code")
    # Si no tienes estas fuentes, usará la por defecto.
    try:
        # Rutas comunes en Windows/Linux - Ajusta según tu SO si es necesario
        # Buscamos Consolas, Courier New, o Arial como fallback
        font_path = "arial.ttf"
        try:
            font = ImageFont.truetype("consola.ttf", 80)  # Windows
        except:
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)  # Linux
            except:
                font = ImageFont.truetype("arial.ttf", 80)  # Mac/General
    except:
        font = ImageFont.load_default()  # Fallback final

    # 5. Texto
    text_main = "Portafolio & Código"
    text_sub = "< David Arroyo / >"

    # 6. Calcular posición para centrar el texto principal
    bbox_main = d.textbbox((0, 0), text_main, font=font)
    w_text, h_text = bbox_main[2] - bbox_main[0], bbox_main[3] - bbox_main[1]
    position_main = ((width - w_text) / 2, (height - h_text) / 2 - 20)

    # 7. Dibujar
    # Marco estilo "terminal"
    d.rectangle([(20, 20), (width-20, height-20)],
                outline=accent_color, width=5)

    # Texto principal
    d.text(position_main, text_main, fill=text_color, font=font)

    # Texto secundario (Nombre) - Un poco más pequeño si es posible, o igual
    font_small = font  # Simplificación para el script
    bbox_sub = d.textbbox((0, 0), text_sub, font=font_small)
    w_sub = bbox_sub[2] - bbox_sub[0]
    position_sub = ((width - w_sub) / 2, (height - h_text) / 2 + 80)

    d.text(position_sub, text_sub, fill=accent_color, font=font_small)

    # 8. Guardar
    filename = "miniatura_linkedin_david.png"
    img.save(filename)
    print(f"Imagen generada con éxito: {filename}")


if __name__ == "__main__":
    crear_miniatura_linkedin()
