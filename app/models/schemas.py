"""
Data Models — Request and Response Schemas
"""
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class LegacySystem(str, Enum):
    COBOL_MAINFRAME = "cobol_mainframe"
    CSV_FLAT_FILE   = "csv_flat_file"
    XML_LEGACY      = "xml_legacy"
    FIXED_WIDTH     = "fixed_width"
    PIPE_DELIMITED  = "pipe_delimited"


class RawLegacyPayload(BaseModel):
    system_id:     str          = Field(..., description="Identifier of the originating legacy system")
    source_format: LegacySystem = Field(..., description="Format of the raw data")
    raw_data:      str          = Field(..., description="Raw string data from the legacy system")
    received_at:   Optional[datetime] = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "system_id": "ERP-001",
                "source_format": "csv_flat_file",
                "raw_data": "John Doe,1985-03-12,johndoe@mail.com,USD,1500.00",
                "received_at": "2025-02-17T10:30:00Z",
            }]
        }
    }


class NormalisedRecord(BaseModel):
    record_id:            str
    source_system:        str
    source_format:        str
    full_name:            Optional[str]   = None
    date_of_birth:        Optional[str]   = None
    email:                Optional[str]   = None
    currency:             Optional[str]   = None
    amount:               Optional[float] = None
    raw_fields:           dict[str, Any]  = Field(default_factory=dict)
    transformed_at:       datetime        = Field(default_factory=datetime.utcnow)
    transformation_notes: list[str]       = Field(default_factory=list)


class TransformationResponse(BaseModel):
    success:       bool
    system_id:     str
    source_format: str
    record:        Optional[NormalisedRecord] = None
    errors:        list[str] = Field(default_factory=list)
    warnings:      list[str] = Field(default_factory=list)


class BatchPayload(BaseModel):
    payloads: list[RawLegacyPayload] = Field(..., min_length=1, max_length=100)


class BatchTransformationResponse(BaseModel):
    total:      int
    successful: int
    failed:     int
    results:    list[TransformationResponse]
