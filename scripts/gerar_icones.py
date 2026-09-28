"""Gera os ícones PNG (192, 512, maskable) do EletroCharge — estilo "cartão em duas camadas"
(fundo escuro arredondado + card verde menor com o símbolo em branco), no mesmo padrão visual
usado no ícone do app CaixaPro.

Rode `python scripts/gerar_icones.py` sempre que precisar regenerar os ícones em
frontend/icons/ (ex.: se mudar a cor da marca ou o desenho do raio).
"""
from pathlib import Path

from PIL import Image, ImageDraw

FUNDO_ESCURO = (15, 23, 32, 255)  # #0f1720 (mesmo background_color do manifest.json)
VERDE = (22, 138, 85, 255)  # #168a55
BRANCO = (255, 255, 255, 255)

# Mesmo path do frontend/icons/icon.svg (viewBox 128x128):
# M70 16 L34 70 H58 L52 112 L96 54 H70 Z
BOLT = [(70, 16), (34, 70), (58, 70), (52, 112), (96, 54), (70, 54)]

PASTA_ICONES = Path(__file__).resolve().parent.parent / "frontend" / "icons"


def _bolt_escalado(tamanho: int, centro_x: float, centro_y: float, escala: float):
    fator = (tamanho / 128) * escala
    offset_x = centro_x - 128 * fator / 2
    offset_y = centro_y - 128 * fator / 2
    return [(offset_x + x * fator, offset_y + y * fator) for x, y in BOLT]


def _pintar_brilho(img: Image.Image, pad: float, largura: float, raio_card: float) -> None:
    """Desenha um brilho branco sutil no topo do card, como no ícone do CaixaPro."""
    altura_faixa = int(largura * 0.55)
    if altura_faixa <= 0:
        return

    faixa = Image.new("RGBA", (int(largura), altura_faixa), (0, 0, 0, 0))
    grad = ImageDraw.Draw(faixa)
    for linha in range(altura_faixa):
        alpha = max(0, int(50 * (1 - linha / altura_faixa)))
        grad.line([(0, linha), (faixa.width, linha)], fill=(255, 255, 255, alpha))

    mascara = Image.new("L", faixa.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        [0, 0, faixa.width, faixa.height * 2], radius=raio_card, fill=255
    )
    img.paste(faixa, (int(pad), int(pad)), Image.composite(faixa, Image.new("RGBA", faixa.size), mascara))


def gerar_normal(tamanho: int) -> Image.Image:
    img = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(img)

    # Fundo escuro arredondado (igual ao "outer background" do ícone do CaixaPro).
    desenho.rounded_rectangle([0, 0, tamanho, tamanho], radius=tamanho * 0.22, fill=FUNDO_ESCURO)

    # Card verde central, com brilho sutil no topo.
    pad = tamanho * 0.12
    largura_card = tamanho - pad * 2
    raio_card = largura_card * 0.14
    desenho.rounded_rectangle([pad, pad, tamanho - pad, tamanho - pad], radius=raio_card, fill=VERDE)
    _pintar_brilho(img, pad, largura_card, raio_card)

    # Raio branco centralizado dentro do card.
    centro = tamanho / 2
    desenho = ImageDraw.Draw(img)
    desenho.polygon(_bolt_escalado(tamanho, centro, centro, 0.62), fill=BRANCO)
    return img


def gerar_maskable(tamanho: int) -> Image.Image:
    # Fundo sólido preenchendo 100% do quadrado (sem cantos transparentes) — a máscara do
    # Android recorta a forma final. O card verde e o raio ficam na "safe zone" central.
    img = Image.new("RGBA", (tamanho, tamanho), FUNDO_ESCURO)
    desenho = ImageDraw.Draw(img)

    lado_card = tamanho * 0.56
    pad = (tamanho - lado_card) / 2
    desenho.rounded_rectangle(
        [pad, pad, tamanho - pad, tamanho - pad], radius=lado_card * 0.18, fill=VERDE
    )

    centro = tamanho / 2
    desenho.polygon(_bolt_escalado(tamanho, centro, centro, 0.38), fill=BRANCO)
    return img


if __name__ == "__main__":
    PASTA_ICONES.mkdir(parents=True, exist_ok=True)
    gerar_normal(512).save(PASTA_ICONES / "icon-512.png")
    gerar_normal(192).save(PASTA_ICONES / "icon-192.png")
    gerar_maskable(512).save(PASTA_ICONES / "icon-maskable.png")
    print("Ícones gerados em", PASTA_ICONES)
