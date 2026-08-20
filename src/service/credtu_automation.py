def gerar_nome_proxima_reciclagem(nome_atual: str) -> str:
    nome = str(nome_atual or "").strip()

    if not nome:
        raise RuntimeError("O nome atual da lista está vazio.")

    # Remove AUTO.R anterior para não duplicar em novas reciclagens.
    nome_base = re.sub(
        r"\s*\|\s*AUTO\.R\s*$",
        "",
        nome,
        flags=re.IGNORECASE,
    ).strip()

    match = re.search(
        r"\bREC\s*(\d+)\b",
        nome_base,
        flags=re.IGNORECASE,
    )

    if not match:
        novo_nome = f"REC1 - {nome_base}".strip()
        return f"{novo_nome} | AUTO.R"

    numero_atual = int(match.group(1))
    proximo_numero = numero_atual + 1

    novo_nome = (
        nome_base[:match.start()]
        + f"REC{proximo_numero}"
        + nome_base[match.end():]
    ).strip()

    return f"{novo_nome} | AUTO.R"