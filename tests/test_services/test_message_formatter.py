from app.services.message_formatter import split_message


def test_short_message_not_split():
    result = split_message("Oi, tudo bem?")
    assert result == ["Oi, tudo bem?"]


def test_long_message_split_on_sentences():
    text = (
        "Os programas da Strides variam entre R$ 1.000 e R$ 17.000. "
        "Essa diferença existe porque cada profissional está em um momento diferente. "
        "O investimento depende do seu momento atual."
    )
    result = split_message(text, max_chars=100)
    assert len(result) >= 2
    for chunk in result:
        assert len(chunk) <= 100


def test_exact_140_chars_not_split():
    text = "a" * 140
    result = split_message(text)
    assert len(result) == 1


def test_141_chars_split():
    text = "a" * 141
    result = split_message(text)
    assert len(result) >= 1
    for chunk in result:
        assert len(chunk) <= 140
