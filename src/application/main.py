import os
import secrets
import threading
import traceback

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from src.service.credtu_automation import (
    CredtuAutomationError,
    executar_reciclagem,
)


load_dotenv()

app = FastAPI(
    title="Credtu Auto Reciclagem",
    version="3.0.0",
    description=(
        "Recebe campaign_id do n8n e devolve "
        "status estruturado da execução."
    ),
)

# Como a automação usa Selenium/Chrome, somente uma
# execução deve acontecer por vez neste processo.
automation_lock = threading.Lock()


def log(mensagem):
    print(str(mensagem), flush=True)


def resposta_erro(
    status: str,
    stage: str,
    message: str,
    error_type: str | None = None,
    campaign_id: str | None = None,
):
    """
    Retorno padronizado para o n8n.

    Mantemos HTTP 200 para o node HTTP Request não parar o workflow.
    O n8n decide pelo campo "ok".
    """
    body = {
        "ok": False,
        "status": status,
        "stage": stage,
        "message": message,
    }

    if error_type:
        body["error_type"] = error_type

    if campaign_id:
        body["campaign_id"] = campaign_id

    return JSONResponse(
        content=body,
        status_code=200,
    )


def token_valido(
    authorization: str | None,
) -> bool:
    esperado = str(
        os.getenv(
            "N8N_API_TOKEN",
            "",
        )
    ).strip()

    if not esperado:
        log(
            "[ERRO API] N8N_API_TOKEN "
            "não configurado no .env."
        )
        return False

    recebido = ""

    if (
        authorization
        and authorization.lower().startswith(
            "bearer "
        )
    ):
        recebido = authorization[7:].strip()

    if not recebido:
        return False

    return secrets.compare_digest(
        recebido,
        esperado,
    )


@app.get("/health")
def health():
    return {
        "ok": True,
        "status": "online",
        "busy": automation_lock.locked(),
    }


@app.post("/api/recycle")
async def recycle(
    request: Request,
    authorization: str | None = Header(
        default=None
    ),
):
    """
    n8n -> 3C

    {
        "campaign_id": "282391"
    }

    3C -> n8n

    SUCESSO:
    {
        "ok": true,
        "status": "success",
        ...
    }

    ERRO:
    {
        "ok": false,
        "status": "...",
        "stage": "...",
        "error_type": "...",
        "message": "..."
    }
    """

    # =====================================================
    # 1. TOKEN
    # =====================================================

    if not token_valido(
        authorization
    ):
        log(
            "[ERRO API] Token inválido "
            "ou ausente."
        )

        return resposta_erro(
            status="unauthorized",
            stage="api_auth",
            message=(
                "Token inválido ou ausente."
            ),
        )

    # =====================================================
    # 2. JSON
    # =====================================================

    try:
        body = await request.json()

    except Exception as erro:
        log(
            "[ERRO API] Body inválido: "
            f"{type(erro).__name__}: {erro}"
        )

        return resposta_erro(
            status="invalid_json",
            stage="api_request",
            error_type=type(erro).__name__,
            message=(
                "Body inválido. "
                "Era esperado JSON com campaign_id."
            ),
        )

    if not isinstance(
        body,
        dict,
    ):
        return resposta_erro(
            status="invalid_body",
            stage="api_request",
            message=(
                "O body precisa ser "
                "um objeto JSON."
            ),
        )

    # =====================================================
    # 3. CAMPAIGN ID
    # =====================================================

    campaign_id = str(
        body.get(
            "campaign_id",
            "",
        )
    ).strip()

    if (
        not campaign_id
        or not campaign_id.isdigit()
    ):
        log(
            "[ERRO API] campaign_id "
            f"inválido: {campaign_id!r}"
        )

        return resposta_erro(
            status="invalid_campaign_id",
            stage="validation",
            message=(
                "campaign_id deve conter "
                "somente números."
            ),
            campaign_id=(
                campaign_id or None
            ),
        )

    # =====================================================
    # 4. LOCK
    # =====================================================

    if not automation_lock.acquire(
        blocking=False
    ):
        log(
            "[ERRO API] Já existe uma "
            "reciclagem em execução."
        )

        return resposta_erro(
            status="busy",
            stage="queue",
            message=(
                "Já existe uma reciclagem "
                "em execução."
            ),
            campaign_id=campaign_id,
        )

    # =====================================================
    # 5. EXECUTA CREDTU
    # =====================================================

    try:
        log("")
        log(
            "=============================================="
        )
        log(
            f"[N8N -> 3C] "
            f"campaign_id recebido: "
            f"{campaign_id}"
        )
        log(
            "=============================================="
        )

        resultado = executar_reciclagem(
            campaign_id
        )

        log(
            f"[3C -> N8N] "
            f"Campanha {campaign_id}: "
            f"{resultado}"
        )

        return JSONResponse(
            content=resultado,
            status_code=200,
        )

    except CredtuAutomationError as erro:
        log(
            "[ERRO AUTOMAÇÃO] "
            f"campaign_id={campaign_id} | "
            f"status={erro.status} | "
            f"stage={erro.stage} | "
            f"type={erro.error_type} | "
            f"message={erro.message}"
        )

        traceback.print_exc()

        body = erro.to_dict()
        body["campaign_id"] = (
            campaign_id
        )

        log(
            f"[3C -> N8N] "
            f"{body}"
        )

        return JSONResponse(
            content=body,
            status_code=200,
        )

    except Exception as erro:
        log(
            "[ERRO INESPERADO API] "
            f"{type(erro).__name__}: "
            f"{erro}"
        )

        traceback.print_exc()

        return resposta_erro(
            status="unexpected_error",
            stage="api_execution",
            error_type=type(erro).__name__,
            message=(
                str(erro)
                or type(erro).__name__
            ),
            campaign_id=campaign_id,
        )

    finally:
        automation_lock.release()


def main():
    host = str(
        os.getenv(
            "HOST",
            "0.0.0.0",
        )
    ).strip() or "0.0.0.0"

    port = int(
        os.getenv(
            "PORT",
            "6776",
        )
    )

    uvicorn.run(
        "src.application.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()