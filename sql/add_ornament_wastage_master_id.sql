/* Add a stable row key required to edit individual wastage records. */
SET XACT_ABORT ON;

IF OBJECT_ID(N'CustomReport.dbo.OrnamentWastageMaster', N'U') IS NULL
    THROW 50001, 'CustomReport.dbo.OrnamentWastageMaster does not exist.', 1;

IF COL_LENGTH(N'CustomReport.dbo.OrnamentWastageMaster', N'WastageID') IS NULL
BEGIN
    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ADD WastageID INT IDENTITY(1,1) NOT NULL;

    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ADD CONSTRAINT PK_OrnamentWastageMaster_WastageID PRIMARY KEY (WastageID);
END;
