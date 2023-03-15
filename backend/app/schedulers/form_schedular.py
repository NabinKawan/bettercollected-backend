import logging
from typing import Dict, Any

from backend.app.schemas.standard_form import FormDocument
from backend.app.services.form_import_service import FormImportService
from backend.app.services.form_plugin_provider_service import FormPluginProviderService
from backend.app.utils import AiohttpClient
from loguru import logger

from common.services.jwt_service import JwtService


class FormSchedular:
    def __init__(
        self,
        form_provider_service: FormPluginProviderService,
        form_import_service: FormImportService,
        jwt_service: JwtService,
    ):
        self.form_provider_service = form_provider_service
        self.form_import_service = form_import_service
        self.jwt_service = jwt_service

    async def update_form(self, *, user, provider, form_id, response_data_owner):
        logger.info(f"Job started for form {form_id} by schedular.")
        cookies = {"Authorization": self.jwt_service.encode(user)}
        # TODO Make it do with proxy service after service and proxy router is refactored
        raw_form = await self.perform_request(
            provider=provider,
            append_url=f"/{form_id}",
            method="GET",
            cookies=cookies,
        )
        raw_converted_form = await self.perform_conversion_request(
            provider=provider,
            raw_form=raw_form,
            convert_responses=False,
            cookies=cookies,
        )
        form = FormDocument.parse_obj(raw_converted_form)

        # if the latest status of form is not closed then perform saving
        if not form.settings.is_closed:
            response_data = await self.perform_conversion_request(
                provider=provider, raw_form=raw_form, cookies=cookies
            )
            await self.form_import_service.save_converted_form_and_responses(
                response_data, response_data_owner
            )
            logger.info(f"Form {form_id} is updated successfully by schedular.")
        else:
            logger.info(f"Form {form_id} is not updated as it is now closed.")

    async def perform_conversion_request(
        self,
        *,
        provider: str,
        raw_form: Dict[str, Any],
        convert_responses: bool = True,
        cookies: Dict = None,
    ):
        return await self.perform_request(
            provider=provider,
            append_url="/convert/standard_form",
            method="POST",
            cookies=cookies,
            json=raw_form,
            params={"convert_responses": str(convert_responses)},
        )

    async def perform_request(
        self,
        *,
        provider: str,
        append_url: str,
        method: str,
        cookies: Dict,
        params: Dict = None,
        json: Dict = None,
    ):
        provider_url = await self.form_provider_service.get_provider_url(provider)
        # TODO Perform request from containers http client
        response = await AiohttpClient.get_aiohttp_client().request(
            method=method,
            url=f"{provider_url}/{provider}/forms{append_url}",
            params=params,
            cookies=cookies,
            json=json,
            timeout=60,
        )
        data = await response.json()
        return data
