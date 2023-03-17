from http import HTTPStatus
from typing import List

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
    async def list(
            self, form_ids: List[str], request_for_deletion: bool
    ) -> List[StandardFormResponse]:
        try:
            find_query = {
                "form_id": {"$in": form_ids},
                "answers": {"$exists": not request_for_deletion}
            }
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

    async def get_user_submissions(self, form_ids, user: User):
        try:
            form_responses = (
                await FormResponseDocument.find(
                    {"dataOwnerIdentifier": user.sub, "form_id": {"$in": form_ids}}
                )
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
                        {"$set": {"form_title": "$form.title"}},
                        {"$unwind": "$form_title"},
                        {
                            "$lookup": {
                                "from": "responses_deletion_requests",
                                "localField": "response_id",
                                "foreignField": "response_id",
                                "as": "deletion_request",
                            }
                        },
                        {"$set": {"deletion_status": "$deletion_request.status"}},
                        {
                            "$unwind": {
                                "path": "$deletion_status",
                                "preserveNullAndEmptyArrays": True,
                            }
                        },
                        {"$sort": {"created_at": -1}},
                    ]
                )
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

    async def get(self, form_id: str, response_id: str) -> StandardFormResponse:
        try:
            document = (
                await FormResponseDocument.find(
                    {"form_id": form_id, "response_id": response_id}
                )
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
                        {
                            "$set": {
                                "title": "$form.title",
                                "provider": "$form.provider",
                            }
                        },
                        {"$unwind": "$title"},
                        {"$unwind": "$provider"},
                        {
                            "$lookup": {
                                "from": "workspace_forms",
                                "localField": "form_id",
                                "foreignField": "form_id",
                                "as": "workspace_form",
                            }
                        },
                        {
                            "$set": {
                                "formCustomUrl": "$workspace_form.settings.custom_url"
                            }
                        },
                        {"$unwind": "$formCustomUrl"},
                    ]
                )
                    .to_list()
            )
            if not document:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    content=MESSAGE_NOT_FOUND,
                )
            if document and len(document) > 1:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    content="Found multiple form response document with the provided response id.",
                )
            return StandardFormResponse(**document[0].dict())
        except (InvalidURI, NetworkTimeout, OperationFailure, InvalidOperation):
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content=MESSAGE_DATABASE_EXCEPTION,
            )

    async def add(self, item: FormResponseDocument) -> StandardFormResponse:
        pass

    async def update(
            self, item_id: str, item: FormResponseDocument
    ) -> StandardFormResponse:
        pass

    async def delete(self, item_id: str, provider: FormProvider):
        pass
