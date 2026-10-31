"""Visual Evidence Asset API Route."""

from fastapi import APIRouter, HTTPException, Response, status
from app.services.data_layer_adapter import adapter

router = APIRouter(prefix="/api/evidence", tags=["Evidence & Visual Assets"])


@router.get("/assets/{file_id}")
def get_screenshot_asset(file_id: str):
    """Retrieve raw visual evidence screenshot (e.g. Grafana dashboard) by file/asset ID."""
    try:
        asset_res = adapter.get_visual_asset(file_id=file_id)
        if not asset_res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visual asset '{file_id}' not found.",
            )

        if isinstance(asset_res, tuple) and len(asset_res) == 2:
            content_bytes, media_type = asset_res
        else:
            content_bytes = asset_res
            media_type = "image/png"

        return Response(content=content_bytes, media_type=media_type)
    except HTTPException:
        raise
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Member 1's data layer has not yet been placed in the project.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading asset: {str(e)}",
        )

