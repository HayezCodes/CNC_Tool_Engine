def get_tool_family_message(tool_family: str) -> dict:
    messages = {
        "TURNING_INSERT": {"status":"LIVE","title":"Turning insert engine is active","message":"This family is fully wired into the behavior engine and supplier mapping."},
        "GROOVING_INSERT": {"status":"NEXT","title":"Grooving module is next","message":"Routing is ready. Logic and supplier mapping still need to be built."},
        "THREADING_INSERT": {"status":"NEXT","title":"Threading module is next","message":"Routing is ready. Logic and supplier mapping still need to be built."},
        "DRILL": {"status":"PLANNED","title":"Drill module planned","message":"Use this router entry as the future home for drill logic and supplier search."},
        "ENDMILL": {"status":"PLANNED","title":"Endmill module planned","message":"Use this router entry as the future home for endmill logic and supplier search."},
        "FACE_MILL": {"status":"PLANNED","title":"Face mill module planned","message":"Use this router entry as the future home for face mill logic and supplier search."},
        "TAP": {"status":"PLANNED","title":"Tap module planned","message":"Use this router entry as the future home for tap logic and supplier search."},
        "REAMER": {"status":"PLANNED","title":"Reamer module planned","message":"Use this router entry as the future home for reamer logic and supplier search."},
    }
    return messages[tool_family]
