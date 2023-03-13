from beanie import PydanticObjectId

from backend.app.schemas.workspace_user import WorkspaceUserDocument
from common.models.user import User


class WorkspaceUserRepository:
    @staticmethod
    async def is_user_admin_in_workspace(
        workspace_id: PydanticObjectId, user: User
    ) -> bool:
        if not user or not workspace_id:
            return False
        workspace_user = await WorkspaceUserDocument.find_one(
            {
                "workspace_id": PydanticObjectId(workspace_id),
                "user_id": PydanticObjectId(user.id),
            }
        )
        return True if workspace_user else False
