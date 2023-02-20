"""Application configuration - root APIRouter.

Defines all FastAPI application endpoints.

Resources:
    1. https://fastapi.tiangolo.com/tutorial/bigger-applications

"""
from typing import Type

from backend.app.controllers import ready
from backend.app.controllers.plugin_proxy import PluginProxy
from classy_fastapi import Routable
from common.base.plugin import register_plugin_class
from common.utils.router import CustomAPIRouter

root_api_router = CustomAPIRouter(prefix="")

root_api_router.include_router(ready.router, tags=["Ready"])

plugin_proxy_router_tags = ["Form Provider Plugin Proxy"]
register_plugin_class(
    router=root_api_router, route=PluginProxy(), tags=plugin_proxy_router_tags
)


# Decorator for automatically inserting routes defined in routable class
def router(*args, prefix=None, **kwargs):
    def decorator(cls: Type[Routable]):
        result = cls(*args, prefix=prefix, **kwargs)
        root_api_router.include_router(result.router)
        return result

    return decorator
