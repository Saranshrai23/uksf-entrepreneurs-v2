from app.services.storage import upload_file


def save_profile_photo(profile_id, photo):
    extension = (
        photo.filename
        .rsplit(".", 1)[-1]
        .lower()
    )

    key = f"photos/{profile_id}.{extension}"

    upload_file(
        photo.file,
        key,
        photo.content_type
    )

    return key
