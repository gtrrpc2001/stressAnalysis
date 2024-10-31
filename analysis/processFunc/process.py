async def ECGserialize(user: dict, eq: str) -> list:
    result = []
    for body in user[eq]["body"]:
        result.extend(body["ecg"])

    return result


async def process_data(user: dict, data: dict) -> dict:

    if data["eq"] in user.keys():
        user[data["eq"]]["body"].append({"eq": data["eq"],
                                         "ecg": data["ecgPacket"],
                                         "writetime": data["writetime"],
                                         "timezone": data["timezone"]}
                                        )

    else:
        user[data["eq"]] = {}
        user[data["eq"]]["analysis_in_progress"] = False
        user[data["eq"]]["body"] = []
        user[data["eq"]]["body"].append({"eq": data["eq"],
                                         "ecg": data["ecgPacket"],
                                         "writetime": data["writetime"],
                                         "timezone": data["timezone"]}
                                        )

    return user
