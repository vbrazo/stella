"""Build WhatsApp interactive card payloads from product templates."""

from app.integrations.whatsapp.models import InteractiveCard
from app.models.recommendation import CARD_TEMPLATES, Product


def build_card(product: Product, utm_campaign: str = "") -> InteractiveCard:
    """Build a WhatsApp CTA card for a product."""
    template = CARD_TEMPLATES.get(product)
    if not template:
        raise ValueError(f"No card template for product: {product}")

    # Build body text: subtitle + bullets + investment line
    bullets_text = "\n".join(f"- {b}" for b in template.bullets)
    body = f"{template.subtitle}\n\n{bullets_text}\n\n{template.investment_line}"

    # Add UTM params to URL
    url = template.cta_url
    separator = "&" if "?" in url else "?"
    utm_params = f"utm_source=whatsapp&utm_medium=stella&utm_campaign={utm_campaign or product.value}"
    url = f"{url}{separator}{utm_params}"

    return InteractiveCard(
        header_text=template.title,
        body_text=body,
        footer_text=None,
        button_text=template.cta_text,
        button_url=url,
    )
