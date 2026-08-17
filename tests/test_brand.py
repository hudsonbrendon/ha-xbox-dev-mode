"""As imagens de marca locais precisam existir e ser PNG do tamanho certo.

Desde o Home Assistant 2026.3 a integracao custom pode servir o proprio icone a partir
de `custom_components/<dominio>/brand/`, com prioridade sobre o CDN do repositorio
`home-assistant/brands`. Sem esses arquivos a interface mostra "icon not available".
Nao precisa de nada no manifest.
"""
import struct
from pathlib import Path

BRAND_DIR = Path(__file__).parent.parent / "custom_components" / "xbox_dev_mode" / "brand"

ESPERADOS = {
    "icon.png": 256,
    "icon@2x.png": 512,
    "dark_icon.png": 256,
    "dark_icon@2x.png": 512,
    "logo.png": 256,
    "logo@2x.png": 512,
    "dark_logo.png": 256,
    "dark_logo@2x.png": 512,
}


def _dimensoes_png(caminho: Path) -> tuple[int, int]:
    """Le largura e altura do cabecalho IHDR, sem depender de Pillow."""
    dados = caminho.read_bytes()
    assert dados[:8] == b"\x89PNG\r\n\x1a\n", f"{caminho.name} nao e PNG"
    largura, altura = struct.unpack(">II", dados[16:24])
    return largura, altura


def test_brand_dir_existe():
    assert BRAND_DIR.is_dir(), "falta custom_components/xbox_dev_mode/brand/"


def test_todas_as_imagens_existem_com_tamanho_correto():
    for nome, lado in ESPERADOS.items():
        arquivo = BRAND_DIR / nome
        assert arquivo.is_file(), f"falta {nome}"
        assert _dimensoes_png(arquivo) == (lado, lado), f"{nome} deveria ser {lado}x{lado}"


def test_variantes_dark_sao_diferentes_das_claras():
    """Se dark_icon for copia de icon, o tema escuro fica sem contraste."""
    assert (BRAND_DIR / "icon.png").read_bytes() != (BRAND_DIR / "dark_icon.png").read_bytes()
