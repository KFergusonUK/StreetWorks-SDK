"""Coded-value tables from the SRWR Data Extract specification v2.02.

The extract stores enumerated fields as codes; these tables map them to the
official descriptions. Real extract data does not always zero-pad codes
(``"5"`` appears where the spec table says ``"05"``), so :func:`describe`
normalises before lookup.
"""

from __future__ import annotations

__all__ = ["describe", "WORKS_TYPES", "ACTIVITY_STATUSES", "NOTICE_TYPES"]

WORKS_TYPES = {
    "01": "Minor With Excavation",
    "02": "Minor Without Excavation",
    "03": "Minor Mobile and Short Duration",
    "04": "Major",
    "05": "Standard",
    "06": "Urgent",
    "07": "Emergency",
    "09": "Remedial Other",
    "10": "Remedial Dangerous",
    "12": "Bar Hole",
    "13": "Dial Before You Dig",
    "14": "Unattributable Works",
    "15": "Defective Apparatus",
    "16": "Road Restriction",
    "17": "Diversionary Works",
    "18": "Works Licence",
    "19": "Traffic Regulation Order",
    "20": "Permission",
    "21": "Removal",
    "22": "Event/Disruption",
    "23": "Damage Report",
    "24": "Accepted Works",
    "26": "Unexpected Buried Object",
}

ACTIVITY_STATUSES = {
    "01": "Potential",
    "03": "Advance Planning",
    "04": "Proposed",
    "05": "In Progress",
    "06": "Cleared",
    "07": "Closed",
    "08": "Closed No Excavation",
    "09": "Abandoned",
    "10": "Active",
    "11": "Lapsed",
    "12": "Awaiting Response",
    "13": "Accepted",
    "14": "Denied",
    "15": "In Force",
    "16": "Commenced",
    "17": "Overrun",
    "18": "Completed",
    "19": "Report Open",
    "20": "Report Closed",
    "21": "Recorded",
    "26": "Accepted - in Vault Submission",
}

NOTICE_TYPES = {
    "01": "Twenty Four Hour Notice",
    "02": "Actual Start",
    "04": "Bar Hole Registration",
    "05": "Cancellation",
    "07": "Defective Apparatus",
    "09": "Direction On Placing Apparatus",
    "10": "Direction On Timing",
    "11": "Diversionary Works (Five Year Notice)",
    "12": "Duration Challenge",
    "13": "Duration Challenge Non Acceptance",
    "15": "Error Correction",
    "20": "Intention To Issue Licence",
    "22": "Non Notifiable Phase Completion",
    "23": "One Month Notice New Activity",
    "27": "Potential Works",
    "31": "Registration Full",
    "32": "Registration Partial",
    "36": "Revert Actual Start",
    "37": "Revert Works Stop",
    "38": "Revised Duration",
    "41": "Seven Day Notice (Follow-up)",
    "42": "Seven Day New Activity",
    "51": "Three Day Notice New Activity",
    "52": "Three Month Notice",
    "55": "Traffic Signal Approval",
    "56": "Traffic Signal Approval Not Required",
    "57": "Traffic Signal Approval With Design",
    "58": "Traffic Signal Design Info Required",
    "60": "Traffic Signal Refused",
    "62": "Two Hours After Notice",
    "63": "Two Hours Before Notice",
    "64": "Unattributable Works",
    "65": "Undue Delay",
    "67": "Works Acceptance Defective Apparatus",
    "68": "Works Acceptance Unattributable Works",
    "69": "Works Cleared",
    "70": "Works Closed",
    "72": "Works Non Acceptance Defective Apparatus",
    "73": "Works Non Acceptance Unattributable Works",
    "75": "Notice Not Required",
    "76": "Twenty Four Hour Modified",
    "77": "Three Day Notice Modified",
    "78": "Damage Notice",
    "79": "Plant Information Request",
    "80": "Non Works Disruption/Event",
    "81": "Permission One Month",
    "82": "Permission Seven Days",
    "83": "Permission One Day After",
    "84": "Permission Three Days After",
    "85": "Permission Three Days After No Due",
    "86": "Revert Clear",
    "87": "Revert Close",
    "88": "Permission",
    "89": "Damage Report Closed",
    "90": "Approve Licence",
    "91": "Refuse Licence",
    "92": "Temporary Traffic Restriction",
    "93": "Enforcement",
    "135": "Unidentified Buried Object",
    "136": "Accepted UBO",
    "137": "Deny UBO",
}

INSPECTION_RESULTS = {
    "0001": "Passed",
    "0002": "Failed - High Risk",
    "0003": "Failed - Low Risk",
    "0004": "Abortive",
    "0005": "Works In Progress",
    "0006": "Works Stopped",
    "0007": "Start Pending",
    "0008": "Failed - Monitor",
    "0009": "Failed - Replace",
    "0010": "Cancelled",
    "0013": "Failed - Medium",
}

TRAFFIC_MANAGEMENT_TYPES = {
    "00": "No Obstruction On C/W Or F/W",
    "01": "Traffic Management Not Yet Known",
    "02": "1 Way Shuttle During Peak",
    "03": "1 Way Shuttle Outwith Peak",
    "04": "Lane Closure - 2 Way Working - Continuous",
    "05": "Lane Closure - 2 Way Working - Outwith Peak",
    "06": "Road Closure",
    "07": "Traffic Signals",
    "08": "Shuttle - Stop/Go Boards - Continuous",
    "14": "Motorway Slip Closure - Continuous",
    "15": "Motorway Slip Closure - Outwith Peak",
    "16": "Shuttle - Give and Take - Continuous",
    "17": "Shuttle - Give and Take - Outwith Peak",
    "18": "Shuttle - Priority Working - Continuous",
    "19": "Shuttle - Priority Working - Outwith Peak",
    "20": "Shuttle - Stop/Go Boards - Outwith Peak",
    "21": "Shuttle - Convoy Working - Continuous",
    "22": "Shuttle - Convoy Working - Outwith Peak",
    "23": "Contraflow on Dual Carriageway - Continuous",
    "24": "Contraflow on Dual Carriageway - Outwith Peak",
    "25": "2 Way Portable Signals - No Junction - Continuous",
    "26": "2 Way Portable Signals - No Junction - Outwith Peak",
    "27": "2 Way Portable Signals - With Junction - Continuous",
    "28": "2 Way Portable Signals - With Junction - Outwith Peak",
    "29": "Multi-Way Portable Signals - With Junction - Continuous",
    "30": "Multi-Way Portable Signals - With Junction - Outwith Peak",
    "31": "Road Narrowing (Two Way Working)",
    "32": "Portable Traffic Lights (TTLS)",
    "33": "Convoy Working",
    "34": "Stop/Go Boards Traffic Control",
    "35": "Priority System Traffic Control",
    "36": "Give and Take Traffic Control",
    "37": "Lane Closure",
    "38": "Hard Shoulder Closure",
    "39": "Slip Closure",
    "40": "Contraflow",
    "41": "Works Entirely On The Footway",
}

REINSTATEMENT_TYPES = {
    "00": "None (not yet entered)",
    "01": "Interim",
    "02": "Permanent",
    "03": "Remedial",
    "04": "Bar Hole",
}

SITE_LOCATIONS = {
    "00": "None (not yet entered)",
    "01": "Carriageway",
    "02": "Footway",
    "03": "Verge",
    "04": "Cycleway",
}

INSPECTION_TYPES = {
    "0006": "Defect Joint Site Visit - Non Categorised",
    "0007": "Defect Joint Site Visit - All Categories",
    "0008": "Defect Follow Up - Non Categorised",
    "0009": "Defect Follow Up - All Categories",
    "0010": "Defect Completion - Non Categorised",
    "0011": "Defect Completion - All Categories",
    "0030": "Statutory - Category A",
    "0031": "Statutory - Category B",
    "0032": "Statutory - Category C",
    "0033": "Investigatory - Non-Categorised",
    "0037": "Investigatory - All Categories",
    "0038": "Target - Category A",
    "0039": "Target - Category B",
    "0040": "Target - Category C",
    "0041": "Routine - Non-Categorised",
    "0045": "Routine - All Categories",
    "0046": "Third Party - Non-Categorised",
    "0050": "Third Party - All Categories",
    "0051": "Occupancy Monitor",
    "0052": "Local Coring",
    "0053": "National Coring",
    "0054": "Apparatus - Routine",
    "0055": "Apparatus - Third Party",
    "0057": "Apparatus - Follow-up",
    "0061": "Defect Joint Site Visit - Categorised",
    "0067": "Defect Completion - Categorised",
    "0069": "Utility - Category A",
    "0070": "Utility - Category B",
    "0071": "Utility - Category C",
    "0072": "Utility Coring",
    "0073": "Apparatus - Post-resolution",
    "0074": "Local Coring - Follow Up",
    "0075": "Local Coring - Completion",
    "0076": "National Coring - Follow Up",
    "0077": "National Coring - Follow Up Completion",
    "0079": "Compliance",
    "1001": "Statutory Training Qualification",
}

FPN_STATUSES = {
    "1": "Potential",
    "2": "Not Pursued",
    "3": "Awaiting Decision",
    "4": "Accepted",
    "5": "Declined",
    "6": "Hearing",
    "7": "Pending Withdrawal",
    "8": "Withdrawn",
}

PHASE_TYPES = {
    "01": "Asset Activity and Reinstatement if Required",
    "02": "Interim to Permanent Reinstatement",
    "03": "Remedial Reinstatement",
}

WORKS_TECHNIQUES = {
    "01": "Machine",
    "02": "Road Breaker",
    "03": "Hand",
    "04": "Thrust Boring",
    "05": "Other",
    "06": "No Excavation",
    "07": "Unknown",
    "08": "Mobile/Short Duration",
}

TABLES: dict[str, dict[str, str]] = {
    "works_type": WORKS_TYPES,
    "activity_status": ACTIVITY_STATUSES,
    "notice_type": NOTICE_TYPES,
    "inspection_result": INSPECTION_RESULTS,
    "inspection_type": INSPECTION_TYPES,
    "traffic_management_type": TRAFFIC_MANAGEMENT_TYPES,
    "reinstatement_type": REINSTATEMENT_TYPES,
    "site_location": SITE_LOCATIONS,
    "fpn_status": FPN_STATUSES,
    "phase_type": PHASE_TYPES,
    "works_technique": WORKS_TECHNIQUES,
}


def describe(table: str, code: str | int | None) -> str | None:
    """Look up the description for a coded value.

    Tolerates the extract's inconsistent zero-padding: ``describe("notice_type",
    "5")`` and ``describe("notice_type", "05")`` both return ``"Cancellation"``.
    Returns ``None`` for empty codes; returns the code itself (stringified) if
    it isn't in the table, so unknown/new codes are never silently lost.
    """
    if code is None or code == "":
        return None
    values = TABLES[table]
    text = str(code).strip()
    if text in values:
        return values[text]
    for width in (2, 3, 4):
        padded = text.zfill(width)
        if padded in values:
            return values[padded]
    return text
