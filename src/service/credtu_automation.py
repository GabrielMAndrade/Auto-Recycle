import os
import re
import time

from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from src.service.driver_service import criar_driver
from src.utils.helpers import log, tirar_print_debug


LOGIN_URL = "https://credtuasset.3c.plus/login"


# =========================================================
# XPATHS - LOGIN
# =========================================================

XPATH_EMAIL = (
    "/html/body/div[1]/div[2]/div/div[1]/div/div[1]/"
    "div/div/form/div[1]/input"
)

XPATH_SENHA = (
    "/html/body/div[1]/div[2]/div/div[1]/div/div[1]/"
    "div/div/form/div[2]/div[1]/input"
)

XPATH_BOTAO_ENTRAR = (
    "/html/body/div[1]/div[2]/div/div[1]/div/div[1]/"
    "div/div/form/button"
)


# =========================================================
# XPATHS - CAMPANHA / URA
# =========================================================

XPATH_ABA_URA = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[2]/"
    "div/div/div[1]/ul/li[2]/button"
)

XPATH_ABRIR_TODAS_LISTAS_URA = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[2]/"
    "div/div/div[2]/button"
)

XPATH_TBODY_LISTAS = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[2]/"
    "div/div/div[2]/table/tbody"
)


# =========================================================
# XPATHS - RECICLAGEM
# =========================================================

XPATH_NOME_LISTA_ATUAL = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[1]/h3/span"
)

XPATH_CHECKBOX_1 = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[2]/div[1]/div[1]/div/div[2]/div/div/div[1]/input"
)

XPATH_CHECKBOX_4 = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[2]/div[1]/div[1]/div/div[2]/div/div/div[4]/input"
)

XPATH_CHECKBOX_5 = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[2]/div[1]/div[1]/div/div[2]/div/div/div[5]/input"
)

XPATH_CHECKBOX_6 = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[2]/div[1]/div[1]/div/div[2]/div/div/div[6]/input"
)

CHECKBOXES_RECICLAGEM = [
    ("checkbox 1", XPATH_CHECKBOX_1),
    ("checkbox 4", XPATH_CHECKBOX_4),
    ("checkbox 5", XPATH_CHECKBOX_5),
    ("checkbox 6", XPATH_CHECKBOX_6),
]

XPATH_CAMPO_NOVO_NOME = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[2]/div[2]/input"
)

# Janela inesperada que pode aparecer após o primeiro clique em Reciclar.
XPATH_FECHAR_JANELA_EXCLUSAO = (
    "/html/body/div[2]/div[2]/div[3]/button[1]"
)

# Botão final que confirma a reciclagem.
XPATH_BOTAO_FINAL_RECICLAR = (
    "/html/body/div[1]/div[2]/div[1]/div[2]/div/div[4]/"
    "div/div/div[2]/div[4]/div[1]/button"
)


def _timeout():
    return int(os.getenv("SELENIUM_TIMEOUT", "30"))


def _sleep_final():
    return float(os.getenv("RECYCLE_SLEEP_SECONDS", "5"))


def esperar_elemento(driver, xpath, timeout=None, exigir_visivel=True):
    timeout = timeout or _timeout()

    def localizar(d):
        try:
            elementos = d.find_elements(By.XPATH, xpath)

            for elemento in elementos:
                try:
                    if not exigir_visivel or elemento.is_displayed():
                        return elemento
                except StaleElementReferenceException:
                    continue

        except Exception:
            pass

        return False

    return WebDriverWait(
        driver,
        timeout,
        poll_frequency=0.1,
        ignored_exceptions=(StaleElementReferenceException,),
    ).until(localizar)


def esperar_clicavel(driver, xpath, timeout=None):
    timeout = timeout or _timeout()

    def localizar(d):
        try:
            elementos = d.find_elements(By.XPATH, xpath)

            for elemento in elementos:
                try:
                    if elemento.is_displayed() and elemento.is_enabled():
                        return elemento
                except StaleElementReferenceException:
                    continue

        except Exception:
            pass

        return False

    return WebDriverWait(
        driver,
        timeout,
        poll_frequency=0.1,
        ignored_exceptions=(StaleElementReferenceException,),
    ).until(localizar)


def clicar(driver, elemento):
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});",
            elemento,
        )
    except Exception:
        pass

    try:
        elemento.click()
    except Exception:
        driver.execute_script("arguments[0].click();", elemento)


def texto_elemento(elemento):
    return str(
        elemento.text
        or elemento.get_attribute("textContent")
        or elemento.get_attribute("innerText")
        or ""
    ).strip()


def fazer_login(driver):
    email = str(os.getenv("CREDTU_EMAIL", "")).strip()
    senha = str(os.getenv("CREDTU_PASSWORD", "")).strip()

    if not email or not senha:
        raise RuntimeError(
            "CREDTU_EMAIL e CREDTU_PASSWORD precisam estar preenchidos no .env."
        )

    log("[CREDTU] Abrindo tela de login...")
    driver.get(LOGIN_URL)

    try:
        campo_email = esperar_clicavel(driver, XPATH_EMAIL, timeout=10)
    except TimeoutException:
        # Caso futuramente seja usado um perfil persistente e já esteja logado.
        log("[CREDTU] Tela de login não apareceu; seguindo com a sessão atual.")
        return

    campo_email.clear()
    campo_email.send_keys(email)

    campo_senha = esperar_clicavel(driver, XPATH_SENHA)
    campo_senha.clear()
    campo_senha.send_keys(senha)

    botao_entrar = esperar_clicavel(driver, XPATH_BOTAO_ENTRAR)
    clicar(driver, botao_entrar)

    WebDriverWait(
        driver,
        _timeout(),
        poll_frequency=0.2,
    ).until(lambda d: "/login" not in str(d.current_url))

    log("[CREDTU] Login concluído.")


def abrir_campanha(driver, campaign_id: str):
    url = f"https://credtuasset.3c.plus/manager/campaign/{campaign_id}"

    log(f"[CREDTU] Abrindo campanha {campaign_id}...")
    driver.get(url)

    WebDriverWait(
        driver,
        _timeout(),
        poll_frequency=0.2,
    ).until(
        lambda d: f"/manager/campaign/{campaign_id}" in str(d.current_url)
    )


def abrir_ura(driver):
    log("[CREDTU] Abrindo aba URA...")
    clicar(driver, esperar_clicavel(driver, XPATH_ABA_URA))


def abrir_todas_listas(driver):
    log("[CREDTU] Abrindo todas as listas de URA...")
    clicar(
        driver,
        esperar_clicavel(driver, XPATH_ABRIR_TODAS_LISTAS_URA),
    )


def obter_linhas_visiveis(driver):
    tbody = esperar_elemento(driver, XPATH_TBODY_LISTAS)
    linhas = []

    for linha in tbody.find_elements(By.XPATH, "./tr"):
        try:
            if linha.is_displayed():
                linhas.append(linha)
        except StaleElementReferenceException:
            continue

    return linhas


def esperar_listas(driver):
    WebDriverWait(
        driver,
        _timeout(),
        poll_frequency=0.2,
    ).until(lambda d: len(obter_linhas_visiveis(d)) > 0)


def clicar_opcoes_da_ultima_lista(driver):
    esperar_listas(driver)

    linhas = obter_linhas_visiveis(driver)

    if not linhas:
        raise RuntimeError("Nenhuma lista de URA foi encontrada.")

    ultima_linha = linhas[-1]

    log(
        f"[CREDTU] {len(linhas)} listas visíveis. "
        "Selecionando a última, que é a mais atual."
    )

    try:
        texto = " | ".join(
            parte.strip()
            for parte in ultima_linha.text.splitlines()
            if parte.strip()
        )
        log(f"[CREDTU] Última lista: {texto[:300]}")
    except Exception:
        pass

    celula_opcoes = ultima_linha.find_element(By.XPATH, "./td[10]")

    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
        celula_opcoes,
    )

    botoes = celula_opcoes.find_elements(By.XPATH, ".//button")
    botao_opcoes = botoes[-1] if botoes else celula_opcoes

    clicar(driver, botao_opcoes)

    return ultima_linha


def fechar_janela_exclusao_se_aparecer(driver):
    try:
        botao_fechar = WebDriverWait(
            driver,
            2,
            poll_frequency=0.05,
        ).until(
            lambda d: next(
                (
                    el
                    for el in d.find_elements(
                        By.XPATH,
                        XPATH_FECHAR_JANELA_EXCLUSAO,
                    )
                    if el.is_displayed() and el.is_enabled()
                ),
                False,
            )
        )

        log("[CREDTU] Janela de exclusão detectada. Fechando...")
        clicar(driver, botao_fechar)

        WebDriverWait(
            driver,
            5,
            poll_frequency=0.05,
        ).until(
            lambda d: not any(
                el.is_displayed()
                for el in d.find_elements(
                    By.XPATH,
                    XPATH_FECHAR_JANELA_EXCLUSAO,
                )
            )
        )

        return True

    except TimeoutException:
        return False


def clicar_reciclar(driver, ultima_linha):
    log("[CREDTU] Abrindo reciclagem da última lista...")

    try:
        botao_reciclar = WebDriverWait(
            driver,
            5,
            poll_frequency=0.1,
        ).until(
            lambda d: ultima_linha.find_element(
                By.XPATH,
                "./td[10]/div/div/div/div[1]/button",
            )
        )

        clicar(driver, botao_reciclar)

    except Exception:
        xpath_fallback = (
            "//button[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÂÃÉÊÍÓÔÕÚÇ',"
            "'abcdefghijklmnopqrstuvwxyzáàâãéêíóôõúç'),"
            "'reciclar')]"
        )

        clicar(
            driver,
            esperar_clicavel(driver, xpath_fallback, timeout=10),
        )

    fechar_janela_exclusao_se_aparecer(driver)

    esperar_elemento(
        driver,
        XPATH_NOME_LISTA_ATUAL,
        timeout=_timeout(),
    )


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
        raise RuntimeError(
            f"Não encontrei o número REC no nome da lista: {nome_atual!r}"
        )

    numero_atual = int(match.group(1))
    proximo_numero = numero_atual + 1

    novo_nome = (
        nome_base[:match.start()]
        + f"REC{proximo_numero}"
        + nome_base[match.end():]
    ).strip()

    return f"{novo_nome} | AUTO.R"


def obter_nome_atual_e_novo(driver):
    elemento = esperar_elemento(
        driver,
        XPATH_NOME_LISTA_ATUAL,
        timeout=_timeout(),
    )

    nome_atual = texto_elemento(elemento)

    if not nome_atual:
        raise RuntimeError("Não consegui ler o nome atual da lista.")

    novo_nome = gerar_nome_proxima_reciclagem(nome_atual)

    log(f"[CREDTU] Nome atual: {nome_atual}")
    log(f"[CREDTU] Novo nome:  {novo_nome}")

    return nome_atual, novo_nome


def checkbox_esta_marcado(driver, elemento):
    try:
        if elemento.is_selected():
            return True
    except Exception:
        pass

    try:
        return bool(
            driver.execute_script(
                "return arguments[0].checked === true;",
                elemento,
            )
        )
    except Exception:
        return False


def marcar_checkbox(driver, nome, xpath):
    checkbox = esperar_elemento(
        driver,
        xpath,
        timeout=_timeout(),
        exigir_visivel=False,
    )

    if checkbox_esta_marcado(driver, checkbox):
        log(f"[CREDTU] {nome} já estava marcado.")
        return

    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});",
            checkbox,
        )
    except Exception:
        pass

    try:
        checkbox.click()
    except Exception:
        driver.execute_script("arguments[0].click();", checkbox)

    WebDriverWait(
        driver,
        5,
        poll_frequency=0.05,
    ).until(lambda d: checkbox_esta_marcado(d, checkbox))

    log(f"[CREDTU] {nome} marcado.")


def marcar_boxes_reciclagem(driver):
    for nome, xpath in CHECKBOXES_RECICLAGEM:
        marcar_checkbox(driver, nome, xpath)


def preencher_novo_nome(driver, novo_nome):
    campo = esperar_clicavel(
        driver,
        XPATH_CAMPO_NOVO_NOME,
        timeout=_timeout(),
    )

    campo.click()
    campo.send_keys(Keys.CONTROL, "a")
    campo.send_keys(Keys.BACKSPACE)
    campo.send_keys(novo_nome)

    WebDriverWait(
        driver,
        5,
        poll_frequency=0.05,
    ).until(
        lambda d: str(campo.get_attribute("value") or "").strip() == novo_nome
    )

    log(f"[CREDTU] Novo nome preenchido: {novo_nome}")


def finalizar_reciclagem(driver):
    log("[CREDTU] Confirmando reciclagem...")

    botao = esperar_clicavel(
        driver,
        XPATH_BOTAO_FINAL_RECICLAR,
        timeout=_timeout(),
    )

    clicar(driver, botao)

    log(
        f"[CREDTU] Reciclagem confirmada. "
        f"Aguardando {_sleep_final():g}s antes de fechar o Chrome..."
    )

    time.sleep(_sleep_final())


def executar_reciclagem(campaign_id: str) -> bool:
    """
    Executa toda a reciclagem da campanha.

    Retorno interno:
        True = todas as etapas foram concluídas.

    Em qualquer erro:
        levanta a exceção para a API capturar e
        responder somente false ao n8n.
    """
    campaign_id = str(
        campaign_id or ""
    ).strip()

    if (
        not campaign_id
        or not campaign_id.isdigit()
    ):
        raise ValueError(
            "campaign_id inválido. "
            "Envie somente o ID numérico da campanha."
        )

    driver = None

    try:
        log("===================================================")
        log(
            f" CREDTU AUTO RECICLAGEM | "
            f"CAMPANHA {campaign_id}"
        )
        log("===================================================")

        # 1. Abre Chrome
        driver = criar_driver()

        # 2. Login
        fazer_login(driver)

        # 3. Entra na campanha recebida pelo n8n
        abrir_campanha(
            driver,
            campaign_id,
        )

        # 4. URA
        abrir_ura(driver)

        # 5. Abre todas as listas
        abrir_todas_listas(driver)

        # 6. Pega a lista mais abaixo/mais atual
        ultima_linha = (
            clicar_opcoes_da_ultima_lista(
                driver
            )
        )

        # 7. Abre reciclagem
        clicar_reciclar(
            driver,
            ultima_linha,
        )

        # 8. Lê nome atual e gera REC + 1 | AUTO.R
        nome_atual, novo_nome = (
            obter_nome_atual_e_novo(
                driver
            )
        )

        # 9. Marca as quatro boxes configuradas
        marcar_boxes_reciclagem(driver)

        # 10. Preenche novo nome
        preencher_novo_nome(
            driver,
            novo_nome,
        )

        # 11. Confirma reciclagem
        # Essa função já aguarda 5 segundos após o clique.
        finalizar_reciclagem(driver)

        log(
            "[CREDTU] Reciclagem concluída "
            "com sucesso."
        )
        log(
            f"[CREDTU] {nome_atual} "
            f"-> {novo_nome}"
        )

        return True

    except Exception:
        # Salva evidência local para depuração.
        # Nada disso é enviado ao n8n.
        if driver is not None:
            tirar_print_debug(
                driver,
                prefixo=(
                    f"erro_campaign_"
                    f"{campaign_id}"
                ),
            )

        raise

    finally:
        # Sempre fecha o Chrome no final,
        # tanto em sucesso quanto em erro.
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
