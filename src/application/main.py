import os
import secrets
import threading
import traceback

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from src.service.credtu_automation import executar_reciclagem


load_dotenv()

app = FastAPI(
    title="Credtu Auto Reciclagem",
    version="2.0.0",
    description=(
        "Recebe somente o campaign_id do n8n e retorna "
        "somente true ou false."
    ),
)

# Impede duas automações Selenium ao mesmo tempo.
automation_lock = threading.Lock()


def log(mensagem):
    print(str(mensagem), flush=True)


def token_valido(authorization: str | None) -> bool:
    """
    Valida o Bearer Token enviado pelo n8n.

    O token esperado fica apenas no .env:
        N8N_API_TOKEN=...
    """
    esperado = str(
        os.getenv("N8N_API_TOKEN", "")
    ).strip()

    if not esperado:
        log(
            "[ERRO API] N8N_API_TOKEN não está "
            "configurado no .env."
        )
        return False

    recebido = ""

    if (
        authorization
        and authorization.lower().startswith("bearer ")
    ):
        recebido = authorization[7:].strip()

    if not recebido:
        log("[ERRO API] Bearer Token não enviado.")
        return False

    return secrets.compare_digest(
        recebido,
        esperado,
    )


@app.get("/health")
def health():
    """
    Endpoint apenas para verificar se o serviço está no ar.
    Não faz parte do fluxo de reciclagem.
    """
    return {
        "ok": True,
        "busy": automation_lock.locked(),
    }


@app.post("/api/recycle")
async def recycle(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """
    CONTRATO N8N -> 3C

    Entrada:
        {
            "campaign_id": "282391"
        }

    O campaign_id deve vir do node n8n:
        Infos. Campanha -> idCampanha

    CONTRATO 3C -> N8N

    Sucesso:
        true

    Qualquer erro:
        false

    Nenhum detalhe interno do Selenium é devolvido ao n8n.
    Os detalhes ficam somente no log da VPS.
    """

    # -----------------------------------------------------
    # 1. AUTORIZAÇÃO
    # -----------------------------------------------------

    if not token_valido(authorization):
        return JSONResponse(
            content=False,
            status_code=200,
        )

    # -----------------------------------------------------
    # 2. LÊ SOMENTE O campaign_id
    # -----------------------------------------------------

    try:
        body = await request.json()
    except Exception:
        log(
            "[ERRO API] Body inválido. "
            "Era esperado JSON com campaign_id."
        )

        return JSONResponse(
            content=False,
            status_code=200,
        )

    if not isinstance(body, dict):
        log(
            "[ERRO API] Body precisa ser um objeto JSON."
        )

        return JSONResponse(
            content=False,
            status_code=200,
        )

    campaign_id = str(
        body.get("campaign_id", "")
    ).strip()

    if (
        not campaign_id
        or not campaign_id.isdigit()
    ):
        log(
            "[ERRO API] campaign_id inválido: "
            f"{campaign_id!r}"
        )

        return JSONResponse(
            content=False,
            status_code=200,
        )

    # -----------------------------------------------------
    # 3. EVITA EXECUÇÕES SIMULTÂNEAS
    # -----------------------------------------------------

    if not automation_lock.acquire(
        blocking=False
    ):
        log(
            "[ERRO API] Já existe uma reciclagem "
            "em execução."
        )

        return JSONResponse(
            content=False,
            status_code=200,
        )

    # -----------------------------------------------------
    # 4. EXECUTA AUTOMAÇÃO CREDTU
    # -----------------------------------------------------

    try:
        log("")
        log(
            "=============================================="
        )
        log(
            f"[N8N -> 3C] campaign_id recebido: "
            f"{campaign_id}"
        )
        log(
            "=============================================="
        )

        resultado = executar_reciclagem(
            campaign_id
        )

        if resultado is True:
            log(
                f"[3C -> N8N] Campanha {campaign_id}: "
                "true"
            )

            return JSONResponse(
                content=True,
                status_code=200,
            )

        log(
            f"[3C -> N8N] Campanha {campaign_id}: "
            "false"
        )

        return JSONResponse(
            content=False,
            status_code=200,
        )

    except Exception as erro:
        # O n8n recebe SOMENTE false.
        # O detalhe fica somente no terminal/journalctl.
        log(
            f"[ERRO AUTOMAÇÃO] Campanha "
            f"{campaign_id}: "
            f"{type(erro).__name__}: {erro}"
        )

        traceback.print_exc()

        log(
            f"[3C -> N8N] Campanha {campaign_id}: "
            "false"
        )

        return JSONResponse(
            content=False,
            status_code=200,
        )

    finally:
        automation_lock.release()


def main():
    host = str(
        os.getenv("HOST", "0.0.0.0")
    ).strip() or "0.0.0.0"

    port = int(
        os.getenv("PORT", "8080")
    )

    uvicorn.run(
        "src.application.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
