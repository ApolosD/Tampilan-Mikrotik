HIDDEN_USERNAMES = {
    "default-trial",
    "default_trial",
    "defaulttrial",
}


def is_hidden_username(value: str) -> bool:
    return value.strip().lower() in HIDDEN_USERNAMES


def keep_visible_rows(rows: list, username_key: str = "username") -> list:
    visible = []
    for row in rows:
        username = str(row.get(username_key, "")) if hasattr(row, "get") else str(row[username_key])
        if is_hidden_username(username):
            continue
        visible.append(row)
    return visible