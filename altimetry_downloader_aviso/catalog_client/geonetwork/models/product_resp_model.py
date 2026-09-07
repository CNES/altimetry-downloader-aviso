from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class GcoCharacterString(BaseModel):
    text: str = Field(..., alias="#text")

    @model_validator(mode="before")
    @classmethod
    def normalize_plain_string(cls, data: Any) -> Any:
        # Geonetwork sometimes returns a bare string instead of the usual
        # {'#text': '...'} wrapper for gco:CharacterString
        if isinstance(data, str):
            return {"#text": data}
        return data


class CitEmail(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class CitCIAddress(BaseModel):
    cit_electronicMailAddress: CitEmail = Field(..., alias="cit:electronicMailAddress")


class CitAddress(BaseModel):
    cit_CI_Address: CitCIAddress = Field(..., alias="cit:CI_Address")


class CitCIContact(BaseModel):
    cit_address: CitAddress = Field(..., alias="cit:address")


class CitContactInfo(BaseModel):
    cit_CI_Contact: CitCIContact = Field(..., alias="cit:CI_Contact")


class CitName(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class CitCIOrganisation(BaseModel):
    cit_name: CitName = Field(..., alias="cit:name")
    cit_contactInfo: CitContactInfo = Field(..., alias="cit:contactInfo")


class CitParty(BaseModel):
    cit_CI_Organisation: CitCIOrganisation = Field(..., alias="cit:CI_Organisation")


class CitCIResponsibility(BaseModel):
    cit_party: CitParty = Field(..., alias="cit:party")


class MdbContact(BaseModel):
    cit_CI_Responsibility: CitCIResponsibility = Field(
        ..., alias="cit:CI_Responsibility"
    )


class MccVersion(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class MccMDIdentifier(BaseModel):
    mcc_version: MccVersion = Field(..., alias="mcc:version")


class CitIdentifier(BaseModel):
    mcc_MD_Identifier: MccMDIdentifier = Field(..., alias="mcc:MD_Identifier")


class CitCICitation(BaseModel):
    cit_identifier: list[CitIdentifier] = Field(..., alias="cit:identifier")

    @model_validator(mode="before")
    @classmethod
    def normalize_identifier(cls, data):
        ids = data.get("cit:identifier")
        if not ids:
            return {"cit:identifier": []}
        if isinstance(ids, dict):
            return {"cit:identifier": [ids]}
        if isinstance(ids, list):
            cleaned = [item for item in ids if isinstance(item, dict)]
            return {"cit:identifier": cleaned}
        return data


class GcoDecimal(BaseModel):
    text: str = Field(..., alias="#text")


class GexWestBoundLongitude(BaseModel):
    gco_Decimal: GcoDecimal = Field(..., alias="gco:Decimal")


class GexEastBoundLongitude(BaseModel):
    gco_Decimal: GcoDecimal = Field(..., alias="gco:Decimal")


class GexSouthBoundLatitude(BaseModel):
    gco_Decimal: GcoDecimal = Field(..., alias="gco:Decimal")


class GexNorthBoundLatitude(BaseModel):
    gco_Decimal: GcoDecimal = Field(..., alias="gco:Decimal")


class GexExGeographicBoundingBox(BaseModel):
    gex_westBoundLongitude: GexWestBoundLongitude = Field(
        ..., alias="gex:westBoundLongitude"
    )
    gex_eastBoundLongitude: GexEastBoundLongitude = Field(
        ..., alias="gex:eastBoundLongitude"
    )
    gex_southBoundLatitude: GexSouthBoundLatitude = Field(
        ..., alias="gex:southBoundLatitude"
    )
    gex_northBoundLatitude: GexNorthBoundLatitude = Field(
        ..., alias="gex:northBoundLatitude"
    )


class GexGeographicElement(BaseModel):
    gex_Ex_GeographicBoundingBox: GexExGeographicBoundingBox = Field(
        ..., alias="gex:EX_GeographicBoundingBox"
    )


class GmlTimePeriod(BaseModel):
    gml_beginPosition: datetime = Field(..., alias="gml:beginPosition")
    gml_endPosition: datetime | None = Field(None, alias="gml:endPosition")

    @field_validator("gml_endPosition", mode="before")
    @classmethod
    def normalize_indeterminate_position(cls, data: Any) -> Any:
        # gml:endPosition can be {'@indeterminatePosition': 'now'} instead
        # of a real date, meaning the period is still ongoing
        if isinstance(data, dict) and "@indeterminatePosition" in data:
            return None
        return data


class GexExtent(BaseModel):
    gml_TimePeriod: GmlTimePeriod = Field(..., alias="gml:TimePeriod")


class GexExTemporalExtent(BaseModel):
    gex_extent: GexExtent = Field(..., alias="gex:extent")


class GexTemporalElement(BaseModel):
    gex_Ex_TemporalExtent: GexExTemporalExtent = Field(
        ..., alias="gex:EX_TemporalExtent"
    )


class GexExExtent(BaseModel):
    gex_geographicElement: GexGeographicElement = Field(
        ..., alias="gex:geographicElement"
    )
    gex_temporalElement: GexTemporalElement = Field(..., alias="gex:temporalElement")


class MriExtent(BaseModel):
    gex_EX_Extent: GexExExtent = Field(..., alias="gex:EX_Extent")


class MriCitation(BaseModel):
    cit_CI_Citation: CitCICitation = Field(..., alias="cit:CI_Citation")


class MriAbstract(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class MriCredit(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class GcoDistance(BaseModel):
    uom: str = Field(..., alias="@uom")
    text: str = Field(..., alias="#text")


class MriDistance(BaseModel):
    gco_Distance: GcoDistance = Field(..., alias="gco:Distance")


class MriMDResolution(BaseModel):
    mri_distance: MriDistance = Field(..., alias="mri:distance")


class MriSpatialResolution(BaseModel):
    mri_MD_resolution: MriMDResolution = Field(..., alias="mri:MD_Resolution")


class MriMDDataIdentification(BaseModel):
    mri_extent: MriExtent = Field(..., alias="mri:extent")
    mri_citation: MriCitation = Field(..., alias="mri:citation")
    mri_abstract: MriAbstract = Field(..., alias="mri:abstract")
    mri_credit: MriCredit = Field(..., alias="mri:credit")
    mri_spatialresolution: MriSpatialResolution = Field(
        ..., alias="mri:spatialResolution"
    )

    @field_validator("mri_spatialresolution", mode="before")
    @classmethod
    def filter_only_distance(cls, data: Any) -> Any:
        if isinstance(data, list):
            for item in data:
                md_res = item.get("mri:MD_Resolution")
                if md_res and "mri:distance" in md_res:
                    return item
        return data


class MdbIdentificationInfo(BaseModel):
    mri_MD_DataIdentification: MriMDDataIdentification = Field(
        ..., alias="mri:MD_DataIdentification"
    )


class CitDescription(BaseModel):
    gco_CharacterString: GcoCharacterString | None = Field(
        None, alias="gco:CharacterString"
    )


class CitLinkage(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class CitCIOnlineResource(BaseModel):
    cit_description: CitDescription | None = Field(None, alias="cit:description")
    cit_linkage: CitLinkage = Field(..., alias="cit:linkage")


class MrdOnLineItem(BaseModel):
    cit_CI_OnlineResource: CitCIOnlineResource = Field(
        ..., alias="cit:CI_OnlineResource"
    )


class MrdMDDigitalTransferOptions(BaseModel):
    mrd_onLine: list[MrdOnLineItem] = Field(..., alias="mrd:onLine")

    @model_validator(mode="before")
    @classmethod
    def normalize_online(cls, data):
        online = data.get("mrd:onLine")
        if not online:
            return {"mrd:onLine": []}
        if isinstance(online, dict):
            return {"mrd:onLine": [online]}
        if isinstance(online, list):
            cleaned = [item for item in online if isinstance(item, dict)]
            return {"mrd:onLine": cleaned}
        return data


class MrdTransferOptions(BaseModel):
    mrd_MD_DigitalTransferOptions: MrdMDDigitalTransferOptions = Field(
        ..., alias="mrd:MD_DigitalTransferOptions"
    )


class MrdMDDistribution(BaseModel):
    mrd_transferOptions: list[MrdTransferOptions] = Field(
        ..., alias="mrd:transferOptions"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_transfer_options(cls, data):
        opts = data.get("mrd:transferOptions")
        if not opts:
            return {"mrd:transferOptions": []}
        if isinstance(opts, dict):
            return {"mrd:transferOptions": [opts]}
        if isinstance(opts, list):
            cleaned = [item for item in opts if isinstance(item, dict)]
            return {"mrd:transferOptions": cleaned}
        return data


class MdbDistributionInfo(BaseModel):
    mrd_MD_Distribution: MrdMDDistribution = Field(..., alias="mrd:MD_Distribution")


class MccCode(BaseModel):
    gco_CharacterString: GcoCharacterString = Field(..., alias="gco:CharacterString")


class MccMDIdentifier1(BaseModel):
    mcc_code: MccCode = Field(..., alias="mcc:code")


class MrcProcessingLevelCode(BaseModel):
    mcc_MD_Identifier: MccMDIdentifier1 = Field(..., alias="mcc:MD_Identifier")


class MrcMDCoverageDescription(BaseModel):
    mrc_processingLevelCode: MrcProcessingLevelCode = Field(
        ..., alias="mrc:processingLevelCode"
    )


class MdbContentInfo(BaseModel):
    mrc_MD_CoverageDescription: MrcMDCoverageDescription = Field(
        ..., alias="mrc:MD_CoverageDescription"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_multiple_aliases(cls, data: dict[str, Any]) -> dict[str, Any]:
        aliases = ["mrc:MD_CoverageDescription", "mrc:MI_CoverageDescription"]
        for alias in aliases:
            if alias in data:
                data["mrc:MD_CoverageDescription"] = data[alias]
                break
        return data


class AvisoProductModel(BaseModel):
    mdb_contact: MdbContact | None = Field(None, alias="mdb:contact")
    mdb_identificationInfo: MdbIdentificationInfo = Field(
        ..., alias="mdb:identificationInfo"
    )
    mdb_distributionInfo: MdbDistributionInfo = Field(..., alias="mdb:distributionInfo")
    mdb_contentInfo: MdbContentInfo = Field(..., alias="mdb:contentInfo")

    def get_last_version(self) -> str:
        citation = self.mdb_identificationInfo.mri_MD_DataIdentification.mri_citation
        cit_id = citation.cit_CI_Citation.cit_identifier[0]

        return cit_id.mcc_MD_Identifier.mcc_version.gco_CharacterString.text

    def get_processing_level(self) -> str:
        description = self.mdb_contentInfo.mrc_MD_CoverageDescription
        mcc_code = description.mrc_processingLevelCode.mcc_MD_Identifier.mcc_code
        return mcc_code.gco_CharacterString.text

    def get_abstract(self) -> str:
        abstract = self.mdb_identificationInfo.mri_MD_DataIdentification.mri_abstract
        return abstract.gco_CharacterString.text

    def get_credit(self) -> str:
        credit = self.mdb_identificationInfo.mri_MD_DataIdentification.mri_credit
        return credit.gco_CharacterString.text

    def get_organisation(self) -> str:
        if self.mdb_contact is None:
            return ""
        organisation = (
            self.mdb_contact.cit_CI_Responsibility.cit_party.cit_CI_Organisation
        )
        return organisation.cit_name.gco_CharacterString.text

    def get_contact_info(self) -> str:
        if self.mdb_contact is None:
            return ""
        org = self.mdb_contact.cit_CI_Responsibility.cit_party.cit_CI_Organisation
        address = org.cit_contactInfo.cit_CI_Contact.cit_address.cit_CI_Address
        return address.cit_electronicMailAddress.gco_CharacterString.text

    def get_resolution(self) -> str:
        spatial_resolution = (
            self.mdb_identificationInfo.mri_MD_DataIdentification.mri_spatialresolution
        )
        distance = spatial_resolution.mri_MD_resolution.mri_distance.gco_Distance
        return f"{distance.text} {distance.uom}"

    def get_geographic_extent(self) -> tuple[float, float, float, float]:
        extent = self.mdb_identificationInfo.mri_MD_DataIdentification.mri_extent
        bbox = extent.gex_EX_Extent.gex_geographicElement.gex_Ex_GeographicBoundingBox
        return (
            float(bbox.gex_westBoundLongitude.gco_Decimal.text),
            float(bbox.gex_eastBoundLongitude.gco_Decimal.text),
            float(bbox.gex_southBoundLatitude.gco_Decimal.text),
            float(bbox.gex_northBoundLatitude.gco_Decimal.text),
        )

    def get_temporal_extent(self) -> str:
        extent = self.mdb_identificationInfo.mri_MD_DataIdentification.mri_extent
        temporal_extent = extent.gex_EX_Extent.gex_temporalElement.gex_Ex_TemporalExtent
        period = temporal_extent.gex_extent.gml_TimePeriod
        return (period.gml_beginPosition, period.gml_endPosition)
