/*
    Migrate the existing CustomReport.dbo.OrnamentWastageMaster table from
    one GrossWt value per row to FromGrossWt / ToGrossWt ranges.

    Existing rows are preserved as singleton ranges (FromGrossWt = ToGrossWt).
    Run this once against the CustomReport database after taking a backup.
*/
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'CustomReport.dbo.OrnamentWastageMaster', N'U') IS NULL
        THROW 50001, 'CustomReport.dbo.OrnamentWastageMaster does not exist.', 1;

    IF COL_LENGTH(N'CustomReport.dbo.OrnamentWastageMaster', N'GrossWt') IS NULL
       OR COL_LENGTH(N'CustomReport.dbo.OrnamentWastageMaster', N'FromGrossWt') IS NOT NULL
       OR COL_LENGTH(N'CustomReport.dbo.OrnamentWastageMaster', N'ToGrossWt') IS NOT NULL
        THROW 50002, 'Table is not in the expected old schema, or migration was already applied.', 1;

    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ADD FromGrossWt DECIMAL(10,3) NULL,
            ToGrossWt DECIMAL(10,3) NULL;

    UPDATE CustomReport.dbo.OrnamentWastageMaster
       SET FromGrossWt = GrossWt,
           ToGrossWt = GrossWt;

    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ALTER COLUMN FromGrossWt DECIMAL(10,3) NOT NULL;
    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ALTER COLUMN ToGrossWt DECIMAL(10,3) NOT NULL;

    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ALTER COLUMN MakingCharge DECIMAL(10,3) NULL;

    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        DROP COLUMN GrossWt;

    ALTER TABLE CustomReport.dbo.OrnamentWastageMaster
        ADD CONSTRAINT CK_OrnamentWastageMaster_WeightRange
        CHECK (FromGrossWt <= ToGrossWt);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
