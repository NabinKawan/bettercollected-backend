from http import HTTPStatus
from typing import List, Dict, Any

from pymongo.errors import (
    InvalidOperation,
    InvalidURI,
    NetworkTimeout,
    OperationFailure,
)

from backend.app.exceptions import HTTPException
from backend.app.models.response_dtos import StandardFormResponseCamelModel
from backend.app.schemas.standard_form_response import FormResponseDocument
from common.base.repo import BaseRepository, T, U
from common.constants import MESSAGE_DATABASE_EXCEPTION, MESSAGE_NOT_FOUND
from common.enums.form_provider import FormProvider
from common.models.standard_form import StandardFormResponse
from common.models.user import User


class FormResponseRepository(BaseRepository):

    @staticmethod
    async def get_form_responses(
            form_ids,
            request_for_deletion: bool,
            extra_find_query: Dict[str, Any] = None,
    ) -> List[StandardFormResponse]:
        try:
            find_query = {
                "form_id": {"$in": form_ids},
                "answers": {"$exists": not request_for_deletion}
            }
            if extra_find_query:
                find_query.update(extra_find_query)
            aggregate_query = [
                {
                    "$lookup": {
                        "from": "forms",
                        "localField": "form_id",
                        "foreignField": "form_id",
                        "as": "form",
                    },
                },
                {"$set": {"form_title": "$form.title"}},
                {"$unwind": "$form_title"},
            ]

            if request_for_deletion:
                aggregate_query.extend(
                    [
                        {
                            "$lookup": {
                                "from": "responses_deletion_requests",
                                "localField": "response_id",
                                "foreignField": "response_id",
                                "as": "deletion_request",
                            }
                        },
                        {"$set": {"deletion_status": "$deletion_request.status"}},
                        {"$unwind": "$deletion_status"},
                    ]
                )

            aggregate_query.append({"$sort": {"created_at": -1}})

            form_responses = (
                await FormResponseDocument.find(find_query)
                    .aggregate(aggregate_query)
                    .to_list()
            )
            return [
                StandardFormResponseCamelModel(**form_response)
                for form_response in form_responses
            ]
        except (InvalidURI, NetworkTimeout, OperationFailure, InvalidOperation):
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content=MESSAGE_DATABASE_EXCEPTION,
            )

    async def list(
            self, form_ids: List[str], request_for_deletion: bool
    ) -> List[StandardFormResponse]:

        form_responses = await self.get_form_responses(form_ids, request_for_deletion)
        return form_responses

    async def get_user_submissions(self,
                                   form_ids,
                                   user: User,
                                   request_for_deletion: bool = False):
        extra_find_query = {
            "dataOwnerIdentifier": user.sub,
        }
        form_responses = await self.get_form_responses(form_ids,
                                                       request_for_deletion,
                                                       extra_find_query)
        return form_responses

    async def get(self, form_id: str, response_id: str) -> StandardFormResponse:
        pass

    async def add(self, item: FormResponseDocument) -> StandardFormResponse:
        pass

    async def update(
            self, item_id: str, item: FormResponseDocument
    ) -> StandardFormResponse:
        pass

    async def delete(self, item_id: str, provider: FormProvider):
        pass
