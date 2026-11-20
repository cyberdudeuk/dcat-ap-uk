// Generated from DCAT-AP-UK. Names match the metadata weaver, so records written by the weaver load into these definitions. Not tested against a live tenant.
// Create with CreateFormType (model.smithy), then attach to assets as the form DcatApUkForm.
// The Smithy syntax here is background knowledge; check it against the SageMaker Catalog guide before loading.
@amazon.datazone#displayName("DCAT-AP-UK")
structure DcatApUkFormType {
    @documentation("The name of the resource, in plain English.")
    @required title: String
    @documentation("A plain English account of what the resource contains and what it can be used for.")
    @required description: String
    @documentation("The main identifier of the resource in the publisher's own catalogue.")
    @required identifier: String
    @documentation("The organisation responsible for making the resource available.")
    @required publisher: String
    @documentation("Where to ask questions about the resource or give feedback on it.")
    @required contactPoint: String
    @documentation("Who can get the data, and on what terms.")
    @required accessRights: String
    @documentation("The classification under the Government Security Classifications Policy that the data itself carries.")
    @required securityClassification: String
    @documentation("The licence under which the resource can be used.")
    @required licence: String
    @documentation("How often the resource is updated.")
    @required accrualPeriodicity: String
    @documentation("Whether the resource is a critical data asset under the Data Asset Management Policy.")
    criticalDataAsset: String
    @documentation("The organisation that created or compiled the content of the resource.")
    creator: String
    @documentation("The date the content of the resource was created or compiled.")
    created: String
    @documentation("A standard, specification or schema the resource follows.")
    conformsTo: String
    @documentation("The period of time the data is about.")
    temporal: String
    @documentation("Whether the data contains information about identifiable living people, and in what form.")
    personalData: String
    @documentation("A statement of any restriction on access or use, such as the data sharing agreement or legal gateway needed.")
    rights: String
    @documentation("The date the content of the resource last changed.")
    modified: String
    @documentation("The date the resource was first made available.")
    issued: String
    @documentation("A one-sentence summary of the resource, of no more than 250 characters.")
    abstract: String
    @documentation("The broad subject of the resource, from a controlled list.")
    theme: String
    @documentation("Words or short phrases that people might search for, not already in the title or description.")
    keyword: String
    @documentation("The geographic area the data is about.")
    spatial: String
    @documentation("A form in which the data can be got, such as a file or an API.")
    distribution: String
    @documentation("A web page where people can find out about the resource and how to get it.")
    landingPage: String
    @documentation("The version of the resource.")
    version: String
    @documentation("Whether the data contains information that needs extra care beyond being personal, such as special category data.")
    sensitiveData: String
    @documentation("An organisation and the role it plays for the resource, such as data owner or data steward.")
    qualifiedAttribution: String
    @documentation("The language or languages of the resource.")
    language: String
    @documentation("Another name the resource is known by, such as an abbreviation or a former name.")
    alternative: String
    @documentation("Any other identifier the resource is known by, such as one in a national or sector register.")
    otherIdentifier: String
    @documentation("The dataset series this dataset belongs to.")
    inSeries: String
    @documentation("A newer resource that replaces this one.")
    isReplacedBy: String
    @documentation("The date after which the resource should no longer be used.")
    expires: String
    @documentation("The version this one replaces in a sequence.")
    previousVersion: String
    @documentation("What changed in this version.")
    versionNotes: String
    @documentation("The smallest distance the data can tell apart, in metres.")
    spatialResolutionInMeters: String
    @documentation("The smallest period the data can tell apart, as an ISO 8601 duration.")
    temporalResolution: String
    @documentation("A code list, classification or set of groupings the data uses, such as age bands or a geography.")
    referenceData: String
    @documentation("A link to a published statement or measurement of the quality of the data.")
    qualityAnnotation: String
    @documentation("Another resource closely related to this one, such as the report the data supports.")
    relation: String
    @documentation("A related resource together with the kind of relationship.")
    qualifiedRelation: String
    @documentation("A web page that documents the resource, such as a user guide or a methodology.")
    documentation: String
    @documentation("Who is allowed to see the metadata record itself.")
    metadataAudience: String
    @documentation("Legislation that requires, governs or permits the publication or sharing of the resource.")
    applicableLegislation: String
    @documentation("A machine-readable policy, in the W3C Open Digital Rights Language (ODRL), saying what may and may not be done with the resource.")
    hasPolicy: String
    @documentation("Every country or territory where the data is stored or processed, or to which it is sent.")
    jurisdiction: String
    @documentation("The basis under UK GDPR on which personal data in the resource may be sent outside the UK.")
    transferMechanism: String
    @documentation("A property this record leaves empty on purpose, and why.")
    missingValue: String
}
