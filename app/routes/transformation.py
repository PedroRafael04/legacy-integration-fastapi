"""
Transformation Routes — single and batch transformation endpoints.
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    RawLegacyPayload, TransformationResponse,
    BatchPayload, BatchTransformationResponse,
)
from app.services.transformation_service import transform_payload

router = APIRouter()

@router.post("/transform", response_model=TransformationResponse,
             summary="Transform a single legacy record")
def transform_single(payload: RawLegacyPayload) -> TransformationResponse:
    result = transform_payload(payload)
    if not result.success and not result.record:
        raise HTTPException(status_code=422, detail=result.errors)
    return result

@router.post("/transform/batch", response_model=BatchTransformationResponse,
             summary="Transform a batch of legacy records")
def transform_batch(batch: BatchPayload) -> BatchTransformationResponse:
    results   = [transform_payload(p) for p in batch.payloads]
    successful = sum(1 for r in results if r.success)
    return BatchTransformationResponse(
        total=len(results), successful=successful,
        failed=len(results) - successful, results=results,
    )

@router.get("/formats", summary="List supported legacy formats")
def list_formats():
    return {
        "supported_formats": [
            {"id": "csv_flat_file",   "name": "CSV Flat File",   "example": "John Doe,1985-03-12,john@mail.com,USD,1500.00"},
            {"id": "xml_legacy",      "name": "Legacy XML",      "example": "<record><n>John</n><dob>1985-03-12</dob></record>"},
            {"id": "cobol_mainframe", "name": "COBOL Mainframe", "example": "Name(30)+DOB(8)+Email(30)+CCY(3)+Amount(13)"},
            {"id": "fixed_width",     "name": "Fixed Width",     "example": "John Doe       1985-03-12  john@mail.com  USD  1500.00"},
            {"id": "pipe_delimited",  "name": "Pipe Delimited",  "example": "name|dob|email|currency|amount\nJohn|1985-03-12|..."},
        ]
    }
