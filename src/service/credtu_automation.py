def fazer_login(driver):
    email = str(
        os.getenv("CREDTU_EMAIL", "")
    ).strip()

    senha = str(
        os.getenv("CREDTU_PASSWORD", "")
    ).strip()

    if not email or not senha:
        raise RuntimeError(
            "CREDTU_EMAIL ou CREDTU_PASSWORD "
            "não estão preenchidos no .env."
        )

    log("[LOGIN] Abrindo página da Credtu...")

    driver.get(LOGIN_URL)

    log(
        f"[LOGIN] URL inicial: "
        f"{driver.current_url}"
    )

    # =====================================================
    # EMAIL
    # =====================================================

    campo_email = esperar_clicavel(
        driver,
        XPATH_EMAIL,
        timeout=15,
    )

    campo_email.clear()
    campo_email.send_keys(email)

    valor_email = str(
        campo_email.get_attribute("value")
        or ""
    ).strip()

    log(
        f"[LOGIN] Email preenchido: "
        f"{valor_email!r}"
    )

    if valor_email != email:
        raise RuntimeError(
            "O email não permaneceu corretamente "
            "no campo de login."
        )

    # =====================================================
    # SENHA
    # =====================================================

    campo_senha = esperar_clicavel(
        driver,
        XPATH_SENHA,
        timeout=15,
    )

    campo_senha.clear()
    campo_senha.send_keys(senha)

    tamanho_senha_campo = len(
        str(
            campo_senha.get_attribute("value")
            or ""
        )
    )

    log(
        f"[LOGIN] Senha preenchida. "
        f"Tamanho no campo: "
        f"{tamanho_senha_campo}"
    )

    if tamanho_senha_campo == 0:
        raise RuntimeError(
            "A senha não permaneceu no campo."
        )

    # =====================================================
    # BOTÃO ENTRAR
    # =====================================================

    botao_entrar = esperar_clicavel(
        driver,
        XPATH_BOTAO_ENTRAR,
        timeout=15,
    )

    log("[LOGIN] Clicando em Entrar...")

    clicar(
        driver,
        botao_entrar,
    )

    # =====================================================
    # ESPERA LOGIN OU IDENTIFICA ERRO
    # =====================================================

    limite = time.monotonic() + _timeout()

    while time.monotonic() < limite:

        url_atual = str(
            driver.current_url
            or ""
        )

        # Login realmente concluído.
        if "/login" not in url_atual:
            log(
                "[OK LOGIN] Login concluído."
            )

            log(
                f"[OK LOGIN] URL atual: "
                f"{url_atual}"
            )

            return

        # Captura textos visíveis da página para descobrir
        # mensagens de erro, captcha, bloqueio etc.
        try:
            texto_pagina = str(
                driver.find_element(
                    By.TAG_NAME,
                    "body",
                ).text
                or ""
            ).strip()

            texto_lower = (
                texto_pagina.lower()
            )

            sinais_erro = [
                "senha incorreta",
                "senha inválida",
                "credenciais inválidas",
                "email ou senha",
                "e-mail ou senha",
                "usuário ou senha",
                "login inválido",
                "acesso negado",
                "não autorizado",
                "captcha",
                "recaptcha",
                "verifique que você é humano",
                "verifique que voce e humano",
                "too many",
                "muitas tentativas",
            ]

            for sinal in sinais_erro:
                if sinal in texto_lower:

                    log(
                        "[ERRO LOGIN] Mensagem "
                        f"detectada na página: "
                        f"{sinal}"
                    )

                    raise RuntimeError(
                        "Login recusado pela página. "
                        f"Mensagem detectada: {sinal}"
                    )

        except RuntimeError:
            raise

        except Exception:
            pass

        time.sleep(0.25)

    # =====================================================
    # LOGIN NÃO SAIU DE /login
    # =====================================================

    log(
        "[ERRO LOGIN] A página permaneceu "
        f"em: {driver.current_url}"
    )

    try:
        texto_final = str(
            driver.find_element(
                By.TAG_NAME,
                "body",
            ).text
            or ""
        ).strip()

        log(
            "[ERRO LOGIN] TEXTO DA PÁGINA:"
        )

        log(
            texto_final[:5000]
        )

    except Exception as erro:
        log(
            "[ERRO LOGIN] Não consegui "
            f"capturar texto: {erro}"
        )

    # Screenshot específico do login.
    try:
        caminho_print = (
            PASTA_SCREENSHOTS
            / "erro_login.png"
        )

        driver.save_screenshot(
            str(caminho_print)
        )

        log(
            "[ERRO LOGIN] Screenshot salvo: "
            f"{caminho_print}"
        )

    except Exception as erro:
        log(
            "[ERRO LOGIN] Falha ao salvar "
            f"screenshot: {erro}"
        )

    raise RuntimeError(
        "Após clicar em Entrar, a Credtu "
        "permaneceu na página /login. "
        "Verifique o texto e screenshot "
        "registrados no log."
    )