from enum import StrEnum

from pydantic import BaseModel


class Product(StrEnum):
    MEMBERSHIP_HEAD_TECH = "membership_head_tech"
    MEMBERSHIP_HEAD_DATA = "membership_head_data"
    PROGRAMA_HEAD_TECH = "programa_head_tech"
    PROGRAMA_HEAD_DATA = "programa_head_data"
    PROGRAMA_TECH_MANAGER = "programa_tech_manager"
    PROGRAMA_DATA_MANAGER = "programa_data_manager"
    PROGRAMA_AI_TECH = "programa_ai_tech"
    PROGRAMA_AI_BUSINESS = "programa_ai_business"
    TRILHAS = "trilhas"
    ACERVO_ON_DEMAND = "acervo_on_demand"


class ProductRecommendation(BaseModel):
    primary: Product
    alternative: Product | None = None
    reasoning: str = ""


class CardTemplate(BaseModel):
    product: Product
    title: str
    subtitle: str
    bullets: list[str]
    investment_line: str = "Investimento disponível na página."
    cta_text: str = "Ver detalhes"
    cta_url: str


CARD_TEMPLATES: dict[Product, CardTemplate] = {
    Product.MEMBERSHIP_HEAD_TECH: CardTemplate(
        product=Product.MEMBERSHIP_HEAD_TECH,
        title="Strides Membership Head de Tecnologia",
        subtitle="O que um MBA Tech deveria ser: jornada completa",
        bullets=[
            "100% ao vivo e online: encontros estratégicos ao longo do ano",
            "Troca qualificada em Programas Executivos combinados",
            "Comunidade: grupo seleto de líderes no mesmo nível",
        ],
        cta_url="https://strides.com.br/membership-head-tech",
    ),
    Product.MEMBERSHIP_HEAD_DATA: CardTemplate(
        product=Product.MEMBERSHIP_HEAD_DATA,
        title="Strides Membership Head de Dados",
        subtitle="O que um MBA Data deveria ser: jornada completa",
        bullets=[
            "100% ao vivo e online: encontros estratégicos ao longo do ano",
            "Troca qualificada em Programas Executivos combinados",
            "Comunidade: grupo seleto de líderes no mesmo nível",
        ],
        cta_url="https://strides.com.br/membership-head-data",
    ),
    Product.PROGRAMA_HEAD_TECH: CardTemplate(
        product=Product.PROGRAMA_HEAD_TECH,
        title="Programa Executivo para Heads de Tecnologia",
        subtitle="Profundidade prática em gestão e liderança em desafios estratégicos como Head.",
        bullets=[
            "4 semanas: 100% ao vivo e online",
            "Foco em competências e benchmarks críticos",
            "Curadoria focada em decisões críticas de liderança",
        ],
        cta_url="https://strides.com.br/programa-head-tech",
    ),
    Product.PROGRAMA_HEAD_DATA: CardTemplate(
        product=Product.PROGRAMA_HEAD_DATA,
        title="Programa Executivo para Heads de Dados",
        subtitle="Profundidade prática em gestão e liderança em desafios estratégicos de dados.",
        bullets=[
            "4 semanas: 100% ao vivo e online",
            "Foco em competências e benchmarks críticos",
            "Curadoria focada em decisões de liderança data-driven",
        ],
        cta_url="https://strides.com.br/programa-head-data",
    ),
    Product.PROGRAMA_TECH_MANAGER: CardTemplate(
        product=Product.PROGRAMA_TECH_MANAGER,
        title="Programa Executivo Tech Manager",
        subtitle="Transição para gestão com profundidade prática.",
        bullets=[
            "4 semanas: 100% ao vivo e online",
            "Foco em liderança de times de tecnologia",
            "Casos reais e benchmarks de mercado",
        ],
        cta_url="https://strides.com.br/programa-tech-manager",
    ),
    Product.PROGRAMA_DATA_MANAGER: CardTemplate(
        product=Product.PROGRAMA_DATA_MANAGER,
        title="Programa Executivo Data Manager",
        subtitle="Transição para gestão de dados com profundidade prática.",
        bullets=[
            "4 semanas: 100% ao vivo e online",
            "Foco em liderança de times de dados",
            "Casos reais e benchmarks de mercado",
        ],
        cta_url="https://strides.com.br/programa-data-manager",
    ),
    Product.PROGRAMA_AI_TECH: CardTemplate(
        product=Product.PROGRAMA_AI_TECH,
        title="AI for Tech Leaders",
        subtitle="Lidere iniciativas de IA com base técnica sólida.",
        bullets=[
            "Aplicações práticas de IA com foco em arquitetura e implementação",
            "Frameworks para gerenciar times que desenvolvem soluções de IA",
            "Ponte entre áreas técnicas e stakeholders estratégicos",
        ],
        cta_url="https://strides.com.br/ai-tech-leaders",
    ),
    Product.PROGRAMA_AI_BUSINESS: CardTemplate(
        product=Product.PROGRAMA_AI_BUSINESS,
        title="AI for Business Leaders",
        subtitle="Entenda IA para liderar iniciativas na sua área.",
        bullets=[
            "Fundamentos de IA para líderes sem formação técnica",
            "Casos de uso aplicáveis em seu departamento",
            "Decisões estratégicas baseadas em dados e IA",
        ],
        cta_url="https://strides.com.br/ai-business-leaders",
    ),
    Product.TRILHAS: CardTemplate(
        product=Product.TRILHAS,
        title="Trilhas Estratégicas para Líderes",
        subtitle="Comece por um desafio ou uma competência essencial e avance com clareza.",
        bullets=[
            "100% on demand e online: siga no seu ritmo",
            "Aplicação imediata no dia a dia",
            "Porta de entrada para evolução estruturada",
        ],
        cta_url="https://strides.com.br/#trilhas",
    ),
    Product.ACERVO_ON_DEMAND: CardTemplate(
        product=Product.ACERVO_ON_DEMAND,
        title="Acervo Strides On Demand",
        subtitle="Acesse os principais conteúdos da Strides no seu ritmo.",
        bullets=[
            "Flexibilidade total de agenda",
            "Casos reais e discussões estratégicas gravadas",
            "Atualização contínua de conteúdo",
        ],
        cta_url="https://strides.com.br/#acervo",
    ),
}
