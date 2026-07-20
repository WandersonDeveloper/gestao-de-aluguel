from pydantic import BaseModel


class EquipmentPhotoRead(BaseModel):
    key: str
    url: str
