"""Backend de correo que envia via Microsoft Graph API (OAuth2 app-only).

Alternativa a SMTP para Office 365 cuando no se pueden usar contrasenas de
aplicacion ni Basic Auth (Security Defaults / SMTP AUTH bloqueado).
Autenticacion client-credentials: la app se autentica a si misma con
client_id + client_secret contra Azure AD; no depende de MFA ni de la
contrasena del buzon, y no la afectan las politicas de Basic Auth.

Requiere una app registrada en Azure AD (Entra ID) con permiso de
aplicacion Mail.Send y consentimiento de administrador. Config por .env:

    DJANGO_EMAIL_BACKEND=core.email_graph.GraphEmailBackend
    MS_GRAPH_TENANT_ID=...
    MS_GRAPH_CLIENT_ID=...
    MS_GRAPH_CLIENT_SECRET=...
    DJANGO_FROM_EMAIL=Auxiliar Contable <apoyo@learnway.co>

El remitente (buzon desde el que se envia) sale de DEFAULT_FROM_EMAIL.
"""

import base64
import os
import threading

import requests
from django.core.mail.backends.base import BaseEmailBackend

_AUTORIDAD = "https://login.microsoftonline.com"
_GRAPH = "https://graph.microsoft.com/v1.0"
_SCOPE = "https://graph.microsoft.com/.default"


class GraphEmailError(Exception):
    """Falla al obtener token o al enviar por Graph."""


class GraphEmailBackend(BaseEmailBackend):
    """Envia EmailMessage de Django a traves de Microsoft Graph sendMail."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.tenant_id = os.environ.get("MS_GRAPH_TENANT_ID", "")
        self.client_id = os.environ.get("MS_GRAPH_CLIENT_ID", "")
        self.client_secret = os.environ.get("MS_GRAPH_CLIENT_SECRET", "")
        self.timeout = int(os.environ.get("MS_GRAPH_TIMEOUT", "30"))
        self._token = None
        self._lock = threading.Lock()

    # -- token ------------------------------------------------------------
    def _obtener_token(self):
        if not (self.tenant_id and self.client_id and self.client_secret):
            raise GraphEmailError(
                "Faltan MS_GRAPH_TENANT_ID / MS_GRAPH_CLIENT_ID / "
                "MS_GRAPH_CLIENT_SECRET en el entorno."
            )
        url = f"{_AUTORIDAD}/{self.tenant_id}/oauth2/v2.0/token"
        datos = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": _SCOPE,
        }
        resp = requests.post(url, data=datos, timeout=self.timeout)
        if resp.status_code != 200:
            raise GraphEmailError(
                f"Azure AD nego el token ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.json()["access_token"]

    def _token_valido(self):
        # El token dura ~60 min; para el volumen de esta app pedir uno por
        # tanda de envio es suficiente y evita cachear secretos en memoria.
        if self._token is None:
            self._token = self._obtener_token()
        return self._token

    # -- envio ------------------------------------------------------------
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        with self._lock:
            try:
                token = self._token_valido()
            except GraphEmailError:
                if self.fail_silently:
                    return 0
                raise
            enviados = 0
            for mensaje in email_messages:
                if self._enviar_uno(mensaje, token):
                    enviados += 1
        return enviados

    def _enviar_uno(self, mensaje, token):
        nombre, remitente = _remitente(mensaje.from_email)
        cuerpo_html = _es_html(mensaje)
        # from y sender identicos: si difieren, Exchange rellena sender con el
        # display name real del buzon (compartido entre apps) y el cliente lo
        # muestra como "en nombre de / via". Igualarlos evita ese texto.
        buzon = {"emailAddress": {"name": nombre, "address": remitente}}
        graph_msg = {
            "message": {
                "subject": mensaje.subject,
                "body": {
                    "contentType": "HTML" if cuerpo_html else "Text",
                    "content": mensaje.body,
                },
                "from": buzon,
                "sender": buzon,
                "toRecipients": _destinatarios(mensaje.to),
                "ccRecipients": _destinatarios(mensaje.cc),
                "bccRecipients": _destinatarios(mensaje.bcc),
                "attachments": _adjuntos(mensaje),
            },
            "saveToSentItems": True,
        }
        url = f"{_GRAPH}/users/{remitente}/sendMail"
        cabeceras = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            url, json=graph_msg, headers=cabeceras, timeout=self.timeout
        )
        if resp.status_code in (200, 202):
            return True
        if self.fail_silently:
            return False
        raise GraphEmailError(
            f"Graph rechazo el envio a {mensaje.to} ({resp.status_code}): "
            f"{resp.text[:300]}"
        )


def _remitente(from_email):
    """Separa 'Nombre <correo>' en (nombre, direccion).

    Sin nombre explicito devuelve ('', direccion) y Graph usa el display
    name del buzon.
    """
    if not from_email:
        raise GraphEmailError("from_email vacio; configura DJANGO_FROM_EMAIL.")
    if "<" in from_email and ">" in from_email:
        nombre = from_email.split("<", 1)[0].strip().strip('"')
        direccion = from_email.split("<", 1)[1].split(">", 1)[0].strip()
        return nombre, direccion
    return "", from_email.strip()


def _destinatarios(direcciones):
    return [{"emailAddress": {"address": d}} for d in (direcciones or [])]


def _es_html(mensaje):
    if getattr(mensaje, "content_subtype", "plain") == "html":
        return True
    for contenido, mimetype in getattr(mensaje, "alternatives", []) or []:
        if mimetype == "text/html":
            # Usa el cuerpo HTML alternativo como contenido principal.
            mensaje.body = contenido
            return True
    return False


def _adjuntos(mensaje):
    salida = []
    for adj in getattr(mensaje, "attachments", []) or []:
        # Django guarda (filename, content, mimetype) o un objeto MIME.
        if isinstance(adj, tuple):
            nombre, contenido, mimetype = adj
        else:
            nombre = adj.get_filename() or "adjunto"
            contenido = adj.get_payload(decode=True) or b""
            mimetype = adj.get_content_type()
        if isinstance(contenido, str):
            contenido = contenido.encode("utf-8")
        salida.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": nombre,
            "contentType": mimetype or "application/octet-stream",
            "contentBytes": base64.b64encode(contenido).decode("ascii"),
        })
    return salida
