"""As imagens de marca locais precisam existir e ser PNG do tamanho certo.

Desde o Home Assistant 2026.3 a integracao custom pode servir o proprio icone a partir
de `custom_components/<dominio>/brand/`, com prioridade sobre o CDN do repositorio
`home-assistant/brands`. Sem esses arquivos a interface mostra "icon not available".
Nao precisa de nada no manifest.
"""
import struct
from pathlib import Path

BRAND_DIR = Path(__file__).parent.parent / "custom_components" / "xbox_dev_mode" / "brand"

# Icone e quadrado (avatar); logo e faixa horizontal. A altura e o que o HA usa para
# escalar, entao e o que vale checar — nao a largura, que varia com o desenho.
ICONES = ("icon.png", "dark_icon.png", "icon@2x.png", "dark_icon@2x.png")
LOGOS = ("logo.png", "dark_logo.png", "logo@2x.png", "dark_logo@2x.png")
ALTURA = {"icon.png": 256, "dark_icon.png": 256, "icon@2x.png": 512, "dark_icon@2x.png": 512,
          "logo.png": 256, "dark_logo.png": 256, "logo@2x.png": 512, "dark_logo@2x.png": 512}


def _dimensoes_png(caminho: Path) -> tuple[int, int]:
    """Le largura e altura do cabecalho IHDR, sem depender de Pillow."""
    dados = caminho.read_bytes()
    assert dados[:8] == b"\x89PNG\r\n\x1a\n", f"{caminho.name} nao e PNG"
    largura, altura = struct.unpack(">II", dados[16:24])
    return largura, altura


def test_brand_dir_existe():
    assert BRAND_DIR.is_dir(), "falta custom_components/xbox_dev_mode/brand/"


def test_todas_as_imagens_existem_com_altura_correta():
    for nome, altura_esperada in ALTURA.items():
        arquivo = BRAND_DIR / nome
        assert arquivo.is_file(), f"falta {nome}"
        _, altura = _dimensoes_png(arquivo)
        assert altura == altura_esperada, f"{nome} deveria ter {altura_esperada}px de altura"


def test_icones_sao_quadrados():
    """O icone e usado como avatar; retangular deforma no card da integracao."""
    for nome in ICONES:
        largura, altura = _dimensoes_png(BRAND_DIR / nome)
        assert largura == altura, f"{nome} deveria ser quadrado, e {largura}x{altura}"


def test_logos_sao_faixas_horizontais():
    for nome in LOGOS:
        largura, altura = _dimensoes_png(BRAND_DIR / nome)
        assert largura > altura, f"{nome} deveria ser horizontal, e {largura}x{altura}"
