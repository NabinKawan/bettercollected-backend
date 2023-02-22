from http import HTTPStatus
from typing import List

from pymongo.errors import (
    InvalidOperation,
    InvalidURI,
    NetworkTimeout,
    OperationFailure,
)

from backend.app.exceptions import HTTPException
from backend.app.schemas.standard_form_response import FormResponseDocument
from common.base.repo import BaseRepository, T, U
from common.constants import MESSAGE_DATABASE_EXCEPTION
from common.enums.form_provider import FormProvider
from common.models.standard_form import StandardFormResponseDto


# noinspection PyMethodOverriding
class FormResponseRepository(BaseRepository):
    async def list(self, form_id: str) -> List[StandardFormResponseDto]:
        try:
            document = (
                await FormResponseDocument.find({"form_id": form_id})
                .aggregate(
                    [
                        {
                            "$lookup": {
                                "from": "forms",
                                "localField": "form_id",
                                "foreignField": "form_id",
                                "as": "form",
                            },
                        },
                        {"$set": {"title": "$form.title"}},
                        {"$unwind": "$title"},
                        {"$sort": {"created_at": -1}},
                    ]
                )
                .to_list()
            )
            return [StandardFormResponseDto(**element.dict()) for element in document]
        except (InvalidURI, NetworkTimeout, OperationFailure, InvalidOperation):
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content=MESSAGE_DATABASE_EXCEPTION,
            )

    async def get(self, workspace_id: str, form_id: str) -> StandardFormResponseDto:
        try:
            # document = await FormResponseDocument
            return None
        except (InvalidURI, NetworkTimeout, OperationFailure, InvalidOperation):
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content=MESSAGE_DATABASE_EXCEPTION,
            )

    async def add(self, item: FormResponseDocument) -> StandardFormResponseDto:
        pass

    async def update(
        self, item_id: str, item: FormResponseDocument
    ) -> StandardFormResponseDto:
        pass

    async def delete(self, item_id: str, provider: FormProvider):
        pass
