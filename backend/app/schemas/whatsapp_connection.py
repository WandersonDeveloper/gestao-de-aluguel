from pydantic import BaseModel


class WhatsappStatusRead(BaseModel):
    existe: bool
    estado: str | None


class WhatsappConnectRead(BaseModel):
    estado: str | None
    qrcode_base64: str | None
