import json
from datetime import datetime, time

from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers


class ReportDataField(serializers.Field):
    """Convert report context values (dates, decimals, defaultdicts) to JSON primitives."""

    def to_representation(self, value):
        return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


class ReportPayloadSerializer(serializers.Serializer):
    report = serializers.CharField(required=False)
    data = ReportDataField()


class ReportIndexItemSerializer(serializers.Serializer):
    business = serializers.CharField()
    name = serializers.CharField()
    url = serializers.CharField()


class ReportIndexSerializer(serializers.Serializer):
    reports = ReportIndexItemSerializer(many=True)


class EmployeeTimeSheetInputSerializer(serializers.Serializer):
    date = serializers.DateField(input_formats=["%Y-%m-%d"])
    employee = serializers.CharField(max_length=100)
    leaveType = serializers.ChoiceField(choices=["None", "Half Day", "Full Day"])
    work = serializers.CharField(required=False, allow_blank=True)
    fromTime = serializers.RegexField(r"^$|^\d{2}:\d{2}$", required=False, allow_blank=True)
    toTime = serializers.RegexField(r"^$|^\d{2}:\d{2}$", required=False, allow_blank=True)
    totalHours = serializers.RegexField(r"^\d{2}:\d{2}$")


class AdminTimeSheetUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    date = serializers.DateField(input_formats=["%Y-%m-%d"])
    employee = serializers.CharField(max_length=100)
    leaveType = serializers.ChoiceField(choices=["None", "Half Day", "Full Day"])
    work = serializers.CharField(required=False, allow_blank=True)
    fromTime = serializers.RegexField(r"^$|^\d{2}:\d{2}$", required=False, allow_blank=True)
    toTime = serializers.RegexField(r"^$|^\d{2}:\d{2}$", required=False, allow_blank=True)


class AdminTimeSheetDeleteSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)


class GoldEstimateInputSerializer(serializers.Serializer):
    date = serializers.DateField(input_formats=["%Y-%m-%d"])
    time = serializers.TimeField(input_formats=["%H:%M:%S", "%H:%M"])
    kPadNo = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    item = serializers.ChoiceField(choices=[
        "Bangle", "Bracelet", "Chain", "Coin", "Dollar", "Ring", "Thalimani",
        "Neclace", "Nanal", "Haram", "Stud", "Pesary", "Extra", "Others",
    ])
    invoiceAmount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    gst = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    rAmount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    oldGoldPayment = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    cashReceived = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    digitalPayment = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    chitAmount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    oldOrnament = serializers.DecimalField(max_digits=18, decimal_places=3, required=False, default=0)
    oldKDye = serializers.DecimalField(max_digits=18, decimal_places=3, required=False, default=0)
    oldOtherDye = serializers.DecimalField(max_digits=18, decimal_places=3, required=False, default=0)
    oldValue = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    remarks = serializers.CharField(max_length=500, allow_blank=True, required=False, default="No Remarks")


class SilverEstimateInputSerializer(serializers.Serializer):
    date = serializers.DateField(input_formats=["%Y-%m-%d"])
    time = serializers.TimeField(input_formats=["%H:%M:%S", "%H:%M"])
    kPadNo = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    netValue = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    cashReceived = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    oldSilverPayment = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    digitalPayment = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    chitAmount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    kSheetWeight = serializers.DecimalField(max_digits=18, decimal_places=3, required=False, default=0)
    physicalWeight = serializers.DecimalField(max_digits=18, decimal_places=3, required=False, default=0)
    oldGoldValue = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    remarks = serializers.CharField(max_length=500, allow_blank=True, required=False, default="No Remarks")


class EstimateDateRangeSerializer(serializers.Serializer):
    fromDate = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])
    fromTime = serializers.TimeField(required=False, input_formats=["%H:%M:%S", "%H:%M"])
    toDate = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])
    toTime = serializers.TimeField(required=False, input_formats=["%H:%M:%S", "%H:%M"])

    def validate(self, attrs):
        if attrs.get("fromTime") and not attrs.get("fromDate"):
            raise serializers.ValidationError({"fromDate": "From Date is required when From Time is set."})
        if attrs.get("toTime") and not attrs.get("toDate"):
            raise serializers.ValidationError({"toDate": "To Date is required when To Time is set."})
        if attrs.get("fromDate") and attrs.get("toDate"):
            from_datetime = datetime.combine(attrs["fromDate"], attrs.get("fromTime") or time.min)
            to_datetime = datetime.combine(attrs["toDate"], attrs.get("toTime") or time.max)
            if from_datetime > to_datetime:
                raise serializers.ValidationError("From Date/Time must be on or before To Date/Time.")
        return attrs


class GoldEstimateRecordSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    time = serializers.TimeField()
    kPadNo = serializers.CharField()
    item = serializers.CharField()
    invoiceAmount = serializers.DecimalField(max_digits=18, decimal_places=2)
    gst = serializers.DecimalField(max_digits=18, decimal_places=2)
    rAmount = serializers.DecimalField(max_digits=18, decimal_places=2)
    oldGoldPayment = serializers.DecimalField(max_digits=18, decimal_places=2)
    cashReceived = serializers.DecimalField(max_digits=18, decimal_places=2)
    digitalPayment = serializers.DecimalField(max_digits=18, decimal_places=2)
    chitAmount = serializers.DecimalField(max_digits=18, decimal_places=2)
    oldOrnament = serializers.DecimalField(max_digits=18, decimal_places=3)
    oldKDye = serializers.DecimalField(max_digits=18, decimal_places=3)
    oldOtherDye = serializers.DecimalField(max_digits=18, decimal_places=3)
    oldValue = serializers.DecimalField(max_digits=18, decimal_places=2)
    hude = serializers.DecimalField(max_digits=18, decimal_places=2)
    balancePaid = serializers.DecimalField(max_digits=18, decimal_places=2)
    lessAmount = serializers.DecimalField(max_digits=18, decimal_places=2)
    remarks = serializers.CharField(allow_blank=True)


class SilverEstimateRecordSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    time = serializers.TimeField()
    kPadNo = serializers.CharField()
    netValue = serializers.DecimalField(max_digits=18, decimal_places=2)
    cashReceived = serializers.DecimalField(max_digits=18, decimal_places=2)
    oldSilverPayment = serializers.DecimalField(max_digits=18, decimal_places=2)
    digitalPayment = serializers.DecimalField(max_digits=18, decimal_places=2)
    chitAmount = serializers.DecimalField(max_digits=18, decimal_places=2)
    kSheetWeight = serializers.DecimalField(max_digits=18, decimal_places=3)
    physicalWeight = serializers.DecimalField(max_digits=18, decimal_places=3)
    oldGoldValue = serializers.DecimalField(max_digits=18, decimal_places=2)
    balancePaid = serializers.DecimalField(max_digits=18, decimal_places=2)
    remarks = serializers.CharField(allow_blank=True)
