from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.exceptions import HTTPException
from backend.app.models.workspace import WorkspaceFormSettings, Workspace
from backend.app.repositories.workspace_form_repository import WorkspaceFormRepository
from backend.app.schedulers.form_schedular import FormSchedular
from backend.app.schemas.workspace import WorkspaceDocument
from backend.app.services.form_import_service import FormImportService
from backend.app.services.form_plugin_provider_service import FormPluginProviderService
from backend.app.services.form_response_service import FormResponseService
from backend.app.services.form_service import FormService
from backend.app.services.plugin_proxy_service import PluginProxyService
from backend.app.services.workspace_user_service import WorkspaceUserService
from backend.app.utils import AiohttpClient
from backend.config import settings

from beanie import PydanticObjectId

from common.enums.plan import Plans
from common.models.form_import import FormImportRequestBody
from common.models.user import User

from starlette.requests import Request


class WorkspaceFormService:
    def __init__(
        self,
        form_provider_service: FormPluginProviderService,
        plugin_proxy_service: PluginProxyService,
        workspace_user_service: WorkspaceUserService,
        form_service: FormService,
        workspace_form_repository: WorkspaceFormRepository,
        form_schedular: FormSchedular,
        form_import_service: FormImportService,
        schedular: AsyncIOScheduler,
        form_response_service: FormResponseService,
    ):
        self.form_provider_service = form_provider_service
        self.plugin_proxy_service = plugin_proxy_service
        self.workspace_user_service = workspace_user_service
        self.form_service = form_service
        self.workspace_form_repository = workspace_form_repository
        self.form_schedular = form_schedular
        self.form_import_service = form_import_service
        self.schedular = schedular
        self.form_response_service = form_response_service

    # TODO : Use plugin interface for importing for now endpoint is used here
    async def import_form_to_workspace(
        self,
        workspace_id: PydanticObjectId,
        provider: str,
        form_import: FormImportRequestBody,
        user: User,
        request: Request,
    ):
        await self.workspace_user_service.check_user_is_admin_in_workspace(
            workspace_id, user
        )

        can_import_form = await self.check_if_user_can_import_more_forms(
            user=user, workspace_id=workspace_id
        )
        if not can_import_form:
            raise HTTPException(
                status_code=403, content="Upgrade plan to import more forms"
            )
        response_data = await self.convert_form(
            provider=provider, request=request, form_import=form_import
        )
        standard_form = (
            await self.form_import_service.save_converted_form_and_responses(
                response_data, form_import.response_data_owner
            )
        )
        embed_url = (
            standard_form.settings.embed_url
            if standard_form.settings and standard_form.settings.embed_url
            else ""
        )
        await self.workspace_form_repository.save_workspace_form(
            workspace_id=workspace_id,
            form_id=standard_form.form_id,
            user_id=user.id,
            workspace_form_settings=WorkspaceFormSettings(
                custom_url=standard_form.form_id,
                embed_url=embed_url,
                response_data_owner_field=form_import.response_data_owner,
                # TODO : Refactor repeated information provider is only saved on form
                #  as it doesn't change with workspaces
                provider=standard_form.settings.provider,
                private=not standard_form.settings.is_public,
            ),
        )
        self.schedular.add_job(
            self.form_schedular.update_form,
            "interval",
            id=f"{provider}_{standard_form.form_id}",
            coalesce=True,
            replace_existing=True,
            kwargs={
                "user": user,
                "provider": provider,
                "form_id": standard_form.form_id,
                "response_data_owner": form_import.response_data_owner,
            },
            minutes=settings.schedular_settings.INTERVAL_MINUTES,
        )

    async def convert_form(self, *, provider, request, form_import):
        provider_url = await self.form_provider_service.get_provider_url(provider)
        response = await AiohttpClient.get_aiohttp_client().post(
            url=f"{provider_url}/{provider}/forms/convert/standard_form",
            json=form_import.form,
            cookies=request.cookies,
            timeout=60,
        )
        response_data = await response.json()
        return response_data

    async def check_if_user_can_import_more_forms(
        self, user: User, workspace_id: PydanticObjectId
    ):
        if user.plan == Plans.PRO:
            return True

        responses = await self.form_response_service.get_responses_count_in_workspace(
            workspace_id
        )
        if responses > 1000:
            return False

        return True
