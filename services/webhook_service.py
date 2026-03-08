from services.db_service import (
    get_or_create_user,
    insert_response,
    response_exists,
    update_user_completion,
)


def get_or_create_webhook_user(user_id):
    return get_or_create_user(user_id, default_username="Unknown_User")


def record_response_if_new(model, user_id, response_id, status, response_timestamp):
    if response_exists(model.table_name, response_id):
        return False

    insert_response(
        model.table_name,
        user_id=user_id,
        response_id=response_id,
        status=status,
        response_timestamp=response_timestamp,
    )
    return True
