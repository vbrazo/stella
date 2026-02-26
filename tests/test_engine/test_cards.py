from app.engine.cards import build_card
from app.models.recommendation import Product


def test_build_membership_card():
    card = build_card(Product.MEMBERSHIP_HEAD_TECH)
    assert card.header_text == "Strides Membership Head de Tecnologia"
    assert "utm_source=whatsapp" in card.button_url
    assert "utm_medium=stella" in card.button_url
    assert card.button_text == "Ver detalhes"
    assert "MBA Tech" in card.body_text


def test_build_trilhas_card():
    card = build_card(Product.TRILHAS)
    assert card.header_text == "Trilhas Estratégicas para Líderes"
    assert "on demand" in card.body_text.lower()


def test_build_acervo_card():
    card = build_card(Product.ACERVO_ON_DEMAND)
    assert card.header_text == "Acervo Strides On Demand"
    assert "Flexibilidade" in card.body_text


def test_utm_campaign_custom():
    card = build_card(Product.PROGRAMA_HEAD_TECH, utm_campaign="hackathon_demo")
    assert "utm_campaign=hackathon_demo" in card.button_url


def test_all_products_have_cards():
    """Every product enum value should have a card template."""
    for product in Product:
        card = build_card(product)
        assert card.header_text
        assert card.body_text
        assert card.button_url
