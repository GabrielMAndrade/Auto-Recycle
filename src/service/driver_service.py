import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def _env_bool(nome: str, padrao: bool = False) -> bool:
    valor = str(os.getenv(nome, str(padrao))).strip().lower()
    return valor in {"1", "true", "yes", "sim", "on"}


def criar_driver():
    """
    Cria uma instância exclusiva do Chrome para cada execução.

    Na VPS:
        HEADLESS=true

    Para depuração local vendo o navegador:
        HEADLESS=false
    """
    options = Options()

    headless = _env_bool("HEADLESS", True)

    if headless:
        options.add_argument("--headless=new")
    else:
        options.add_argument("--start-maximized")

    # Mantém o navegador headless o mais próximo possível da execução local.
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--force-device-scale-factor=1")

    # Flags importantes para execução estável em VPS/Linux.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")

    # Reduz diferenças desnecessárias entre Chrome visível e headless.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Evita throttling quando estiver sem foco/minimizado em execução local.
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")

    chrome_binary = str(os.getenv("CHROME_BINARY", "")).strip()
    if chrome_binary:
        options.binary_location = chrome_binary

    chromedriver_path = str(os.getenv("CHROMEDRIVER_PATH", "")).strip()

    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Selenium Manager resolve o driver quando possível.
        driver = webdriver.Chrome(options=options)

    # navigator.webdriver é uma diferença comum entre execução local e headless.
    # Aplicado antes de qualquer navegação feita pela automação.
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": (
                    "Object.defineProperty(navigator, 'webdriver', "
                    "{get: () => undefined});"
                )
            },
        )
    except Exception:
        # Não impede a automação caso a versão do Chrome não aceite o comando.
        pass

    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)

    return driver