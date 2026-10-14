USE [CustomReport];
GO

IF OBJECT_ID(N'dbo.GoldEstimate', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.GoldEstimate
    (
        GoldEstimateID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_GoldEstimate PRIMARY KEY,
        EstimateDate DATE NOT NULL,
        EstimateTime TIME(0) NOT NULL,
        Hude DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_Hude DEFAULT (0),
        KPadNo NVARCHAR(50) NOT NULL CONSTRAINT DF_GoldEstimate_KPadNo DEFAULT (N''),
        Item NVARCHAR(30) NOT NULL,
        InvoiceAmount DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_InvoiceAmount DEFAULT (0),
        GST DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_GST DEFAULT (0),
        RAmount DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_RAmount DEFAULT (0),
        OldGoldPayment DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_OldGoldPayment DEFAULT (0),
        CashReceived DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_CashReceived DEFAULT (0),
        DigitalPayment DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_DigitalPayment DEFAULT (0),
        ChitAmount DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_ChitAmount DEFAULT (0),
        OldOrnament DECIMAL(18,3) NOT NULL CONSTRAINT DF_GoldEstimate_OldOrnament DEFAULT (0),
        OldKDye DECIMAL(18,3) NOT NULL CONSTRAINT DF_GoldEstimate_OldKDye DEFAULT (0),
        OldOtherDye DECIMAL(18,3) NOT NULL CONSTRAINT DF_GoldEstimate_OldOtherDye DEFAULT (0),
        OldValue DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_OldValue DEFAULT (0),
        Remarks NVARCHAR(500) NOT NULL CONSTRAINT DF_GoldEstimate_Remarks DEFAULT (N'No Remarks'),
        BalancePaid DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_BalancePaid DEFAULT (0),
        LessAmount DECIMAL(18,2) NOT NULL CONSTRAINT DF_GoldEstimate_LessAmount DEFAULT (0),
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_GoldEstimate_CreatedAt DEFAULT (SYSDATETIME())
    );
END;
GO

IF OBJECT_ID(N'dbo.SilverEstimate', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.SilverEstimate
    (
        SilverEstimateID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SilverEstimate PRIMARY KEY,
        EstimateDate DATE NOT NULL,
        EstimateTime TIME(0) NOT NULL,
        KPadNo NVARCHAR(50) NOT NULL CONSTRAINT DF_SilverEstimate_KPadNo DEFAULT (N''),
        NetValue DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_NetValue DEFAULT (0),
        CashReceived DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_CashReceived DEFAULT (0),
        OldSilverPayment DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_OldSilverPayment DEFAULT (0),
        DigitalPayment DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_DigitalPayment DEFAULT (0),
        ChitAmount DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_ChitAmount DEFAULT (0),
        KSheetWeight DECIMAL(18,3) NOT NULL CONSTRAINT DF_SilverEstimate_KSheetWeight DEFAULT (0),
        PhysicalWeight DECIMAL(18,3) NOT NULL CONSTRAINT DF_SilverEstimate_PhysicalWeight DEFAULT (0),
        OldGoldValue DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_OldGoldValue DEFAULT (0),
        Remarks NVARCHAR(500) NOT NULL CONSTRAINT DF_SilverEstimate_Remarks DEFAULT (N'No Remarks'),
        BalancePaid DECIMAL(18,2) NOT NULL CONSTRAINT DF_SilverEstimate_BalancePaid DEFAULT (0),
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_SilverEstimate_CreatedAt DEFAULT (SYSDATETIME())
    );
END;
GO
